#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_suggest.py — 隐患 → 整改通知(N 条隐患 → 1 段描述 + N 条针对性整改)

v0.4 新增: --photos 参数,Qwen-VL-Max 视觉识别后,自动喂给 DeepSeek 出通知。

两种输入方式:
  ① 文本隐患:命令行参数 / stdin / -i 交互式
  ② 照片识别:--photos <路径...> (Qwen-VL-Max 自动看图)

用法:
  # 文本(老用法,完全兼容)
  ./venv/bin/python ai_suggest.py "电线泡水" "高处未系安全带"
  echo -e "电线泡水\\n高处未系安全带" | ./venv/bin/python ai_suggest.py
  ./venv/bin/python ai_suggest.py -i

  # 照片(新,融合模式)
  ./venv/bin/python ai_suggest.py --photos photo1.jpg photo2.jpg
  ./venv/bin/python ai_suggest.py --photos ./工地照片/

  # 走代理时(用户的 key 是 sk-ws-... 格式时通常需要)
  ./venv/bin/python ai_suggest.py --photos photo.jpg \\
      --base-url https://your-proxy.com/v1 \\
      --model qwen-vl-max

输出:
  - 完整通知书文本(终端预览)
  - YAML 到 ./notice.yaml(供 generate_notice.py 出 docx)
"""

import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path


# ════════════════════════════════════════════════════════════════
# API key 加载(两类:DeepSeek 文字生成 + Qwen-VL 图片识别)
# ════════════════════════════════════════════════════════════════

def load_api_key(env_var: str, fallback_file: str) -> str:
    """统一从环境变量或 ~/.config/...txt 读 key。"""
    k = os.environ.get(env_var)
    if k:
        return k.strip()
    f = Path(fallback_file).expanduser()
    if f.exists():
        return f.read_text().strip()
    return ""


def load_keys():
    """懒加载所有 key(在 main() 里调用,这样 --help 不会被拦)。"""
    deepseek = load_api_key("DEEPSEEK_API_KEY", "~/.config/deepseek_key.txt")
    dashscope = load_api_key("DASHSCOPE_API_KEY", "~/.config/dashscope_key.txt")
    base_url = os.environ.get(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = os.environ.get("DASHSCOPE_VL_MODEL", "qwen-vl-max")
    return deepseek, dashscope, base_url, model


# ════════════════════════════════════════════════════════════════
# 文字生成 prompt + 调用(原有 v0.3 逻辑)
# ════════════════════════════════════════════════════════════════

PROMPT = """你是建筑施工安全员,负责把 N 条隐患整合成一份整改通知的核心内容。
请只输出合法 JSON,不要任何解释,不要 markdown 代码块。

输入:
- 隐患列表(每行一条,共 N 条,N ∈ [1,6]):
{hazards_block}
- 今天日期: {today}
- 整改期限: {deadline} 天

输出字段(全部必须;无法确定的填占位字符串):
- to_unit: "XX项目部"
- from_unit: "安监部"
- issue_date: "{today}"
- context: "日常巡检"
- hazards_input: 原样回传输入数组(去掉空行/重复,保持顺序)
- location: 综合位置描述(N 条在同区域写 1 处,不同则用"、"分隔)
- regulation_name: 适用的规范,带书名号(可多个,用"、"分隔)
- regulation_code: 编号(可多个,用"、"分隔)
- violation_clause: 具体违反的条款(可多个,用"、"分隔)
- hazard_paragraph: 一段话,**把所有 N 条隐患依次描述出来**。
  严格约束:
  - **一段话,不换行**(YAML 用 | 块保存为单一段落)
  - **不编号**(不要"1./2./3."或"(1)/(2)/..."这种编号)
  - **不列表**(不要"•"或"-"项目符号)
  - 用"同时 / 此外 / 另外 / 还存在"等连接词串联各条隐患
  - 必须让**所有 N 条隐患都出现**,且**顺序与输入一致**
  - 引用 1-3 个标准号
  - 段长 ≤ 400 字
  - 住建部正式公文口吻,不口语化
- requirements: 数组,**正好 N 条**,与输入隐患**一一对应**(顺序一致)。
  严格约束:
  - **每条只针对对应的那一条隐患**,**不写通用整改**:
    ✗ 不要"立即停止施工""全面排查""举一反三""严肃处理"这种万能句
    ✓ 必须能直接看出是针对哪一条隐患的整改
  - 每条动词开头、具体可执行、有量化指标(如时间/数量/距离)
  - 必须引用对应隐患适用的规范条款
- deadline_days: {deadline}
- penalty_doc: "施工现场奖惩实施细则"
- penalty: "违约扣款"
- doc_number: ""
- photos: ["图1","图2","图3","图4"] (4 个占位字符串,实际贴图时替换)

常见规范编号参考(选适用的现行版本):
- 临时用电 JGJ 46-2005
- 高处作业 JGJ 80-2016
- 深基坑 JGJ 120-2012
- 脚手架 JGJ 130-2011
- 模板 JGJ 162-2008
- 塔式起重机 JGJ 196-2010
- 安全帽 GB 2811-2019
- 安全带 GB 6095-2021
- 安全网 GB 5725-2009
- 施工检查标准 JGJ 59-2011
- 建设工程施工现场消防安全技术标准 GB 50720-2011
"""


def call_deepseek(hazards: list, today: str, deadline: int, api_key: str) -> dict:
    """调 DeepSeek API,N 条隐患 → 1 份通知 JSON。"""
    hazards_block = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(hazards))
    prompt = PROMPT.format(
        hazards_block=hazards_block,
        today=today,
        deadline=deadline,
    )
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    text = result["choices"][0]["message"]["content"].strip()
    # 容错:去掉首尾 ``` 或 ```json 包裹
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


# ════════════════════════════════════════════════════════════════
# 图片识别 prompt + 调用(Qwen-VL-Max) — v0.4 新增
# ════════════════════════════════════════════════════════════════

QWEN_VL_PROMPT = """你是一名工地安全员。看到一张现场照片后，按 JSON 输出（不要 markdown 代码块）：

{
  "位置": "<楼栋/楼层/区域，例如 '10号楼b栋14层'，看不到就留空>",
  "隐患描述": "<10-30 字，极简现场术语，不带前缀>",
  "建议措施": "<一句话整改方法>"
}

风格参考：
- {"位置":"10号楼b栋14层","隐患描述":"加气块临边堆放","建议措施":"按要求将材料堆放在指定位置"}
- {"位置":"九号楼B栋18层","隐患描述":"外架安全网损坏","建议措施":"及时恢复外架安全网"}
- {"位置":"10号楼a栋8层","隐患描述":"放线洞未浇筑无盖板","建议措施":"及时恢复洞口盖板"}

硬性要求：
1. 隐患描述不要前缀（不要写「隐患：」「问题：」）
2. 看不到的地方不许编，没法判断就留空
3. 语气工地班前会腔，不写「经检查发现」之类
4. 动火作业场景必须看：作业点 5m 内是否有灭火器/接火盆？看不到要明说「未观察到」"""

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def call_qwen_vl(image_path: str, api_key: str, base_url: str, model: str) -> dict:
    """调 Qwen-VL-Max 看单张图,返回 {位置, 隐患描述, 建议措施}。"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime = MIME_MAP.get(ext, "image/jpeg")

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": QWEN_VL_PROMPT},
            ],
        }],
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"].strip()
        # 容错:去掉首尾 ``` 或 ```json 包裹
        if content.startswith("```"):
            lines = content.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return json.loads(content)


def collect_photo_paths(args: list) -> list:
    """从参数(可能是文件或文件夹)收集所有支持的图片路径,按文件名排序。"""
    paths = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.suffix.lower() in IMAGE_EXT:
                    paths.append(str(f))
        elif p.is_file() and p.suffix.lower() in IMAGE_EXT:
            paths.append(str(p))
        else:
            sys.stderr.write(f"⚠ 跳过: {a} (不是图片或不存在)\n")
    return paths


def photos_to_hazards(photo_paths: list, api_key: str, base_url: str, model: str) -> list:
    """N 张图 → N 条隐患描述(完全丢弃 Qwen 的位置和建议措施,只保留隐患描述)。"""
    hazards = []
    for i, p in enumerate(photo_paths, 1):
        sys.stderr.write(f"🖼  [{i}/{len(photo_paths)}] {Path(p).name} ... ")
        try:
            data = call_qwen_vl(p, api_key, base_url, model)
            desc = (data.get("隐患描述") or "").strip()
            if not desc:
                desc = f"(AI 识别为空: {Path(p).name})"
            sys.stderr.write(f"✓ {desc[:30]}\n")
            hazards.append(desc)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode()
            except Exception:
                pass
            sys.stderr.write(f"✗ HTTP {e.code}: {err_body[:100]}\n")
            hazards.append(f"(AI 识别失败 {Path(p).name}: HTTP {e.code})")
        except Exception as e:
            sys.stderr.write(f"✗ {e}\n")
            hazards.append(f"(AI 识别失败 {Path(p).name}: {e})")
    return hazards


# ════════════════════════════════════════════════════════════════
# 文本渲染(原有,不变)
# ════════════════════════════════════════════════════════════════

def render_text(d: dict) -> str:
    """渲染通知书文本(终端预览用,实际 docx 由 generate_notice.py 生成)。"""
    iso = d.get("regulation_name", "").strip("《》")
    out = []
    out.append("安全隐患整改通知书")
    if d.get("doc_number"):
        out.append(d["doc_number"])
        out.append("")
    out.append(f"致:{d.get('to_unit', 'XX项目部')}:")
    out.append("")

    paragraph = d.get("hazard_paragraph") or (
        f"　　{d.get('issue_date', '')},"
        f"{d.get('from_unit', '安监部')}于"
        f"{d.get('context', '日常巡检')}中,"
        f"发现你单位{d.get('location', '施工现场')}"
        f"存在{d.get('hazard', '')}等问题,"
        f"违反《{iso}》"
        f"({d.get('regulation_code', '')}){d.get('violation_clause', '')},"
        f"未及时整改。"
    )
    out.append(paragraph)
    out.append("")
    out.append("现对你单位要求如下:")
    for i, r in enumerate(d.get("requirements", []), 1):
        out.append(f"{i}.{r}")
    out.append("")
    deadline = d.get("deadline_days", 3)
    out.append(
        f"　　本通知下发之日起 {deadline} 日内完成全部整改,"
        f"并将整改结果书面报{d.get('from_unit', '安监部')}。"
        f"{d.get('from_unit', '安监部')}将于整改完成后组织复查。"
        f"逾期将按照《{d.get('penalty_doc', '施工现场奖惩实施细则')}》"
        f"对你单位进行{d.get('penalty', '违约扣款')}处理。"
    )
    out.append("")
    out.append(f"发文单位:{d.get('from_unit', '安监部')}(盖章)")
    out.append(d.get("issue_date", ""))
    out.append("")
    out.append("签收人:_____________  签收日期:_____________")
    return "\n".join(out)


def parse_hazards_from_stdin() -> list:
    """从 stdin 读多行,拆成隐患列表。空行/纯空白行忽略。"""
    raw = sys.stdin.read()
    lines = [ln.strip() for ln in raw.splitlines()]
    return [ln for ln in lines if ln]


# ════════════════════════════════════════════════════════════════
# 主入口(argparse 重构)
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="智安通 v0.4 — 隐患 → 整改通知。文本输入或 Qwen-VL-Max 看图识别。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  %(prog)s "电线泡水" "高处未系安全带"
  echo -e "电线泡水\\n高处未系安全带" | %(prog)s
  %(prog)s -i
  %(prog)s --photos photo1.jpg photo2.jpg
  %(prog)s --photos ./工地照片/
  %(prog)s --photos photo.jpg --base-url https://your-proxy.com/v1
""",
    )
    parser.add_argument("hazard", nargs="*",
                        help="隐患文本(可多条,空格分隔)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="交互式输入,空行结束")
    parser.add_argument("--photos", nargs="+", metavar="PATH",
                        help="照片路径或文件夹(Qwen-VL-Max 自动识别隐患)")
    parser.add_argument("--deadline", type=int, default=3,
                        help="整改期限(天),默认 3")
    parser.add_argument("--base-url", metavar="URL",
                        help="Qwen-VL API 端点(走代理时用,默认阿里云 dashscope 直连)")
    parser.add_argument("--model", default="qwen-vl-max",
                        help="Qwen-VL 模型名,默认 qwen-vl-max")
    args = parser.parse_args()

    hazards: list = []
    source = ""

    deepseek_key, dashscope_key, default_base_url, default_model = load_keys()
    base_url = args.base_url or default_base_url
    model = args.model or default_model

    # ── Step 1: 收集隐患 ──
    if args.photos:
        # 照片模式
        photo_paths = collect_photo_paths(args.photos)
        if not photo_paths:
            sys.stderr.write("⚠ --photos 没找到任何图片(.jpg/.png/.webp/.bmp)\n")
            sys.exit(1)
        if not dashscope_key:
            sys.stderr.write("⚠ --photos 需要 DASHSCOPE_API_KEY(env 或 ~/.config/dashscope_key.txt)\n")
            sys.stderr.write("   跑 scripts/set-dashscope-key.ps1 配置。\n")
            sys.exit(1)
        sys.stderr.write(f"🔍 Qwen-VL-Max 识别 {len(photo_paths)} 张图...\n")
        sys.stderr.write(f"   端点: {base_url}  模型: {model}\n")
        hazards = photos_to_hazards(photo_paths, dashscope_key, base_url, model)
        source = f"photos({len(photo_paths)})"
    elif args.interactive:
        sys.stderr.write("请逐条输入隐患(每行一条),输入空行结束:\n")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            hazards.append(line)
        source = "interactive"
    elif args.hazard:
        hazards = [s.strip() for s in args.hazard if s.strip()]
        source = f"argv({len(hazards)})"
    elif not sys.stdin.isatty():
        hazards = parse_hazards_from_stdin()
        source = "stdin"

    if not hazards:
        parser.print_help()
        sys.stderr.write("\n⚠ 没收到任何隐患。\n")
        sys.exit(1)

    # ── Step 2: 检查 DeepSeek key ──
    if not deepseek_key:
        sys.stderr.write("⚠ 需要 DEEPSEEK_API_KEY(env 或 ~/.config/deepseek_key.txt)\n")
        sys.stderr.write("   跑 scripts/set-deepseek-key.ps1 配置。\n")
        sys.exit(1)

    # ── Step 3: 调 DeepSeek 出通知 ──
    t = date.today()
    today = f"{t.year}年{t.month}月{t.day}日"

    sys.stderr.write(f"🔄 调 DeepSeek ... ({source} → {len(hazards)} 条隐患)\n")
    for i, h in enumerate(hazards, 1):
        sys.stderr.write(f"   {i}. {h}\n")

    try:
        data = call_deepseek(hazards, today, args.deadline, deepseek_key)
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"❌ DeepSeek API 错误 {e.code} {e.reason}\n")
        try:
            sys.stderr.write(e.read().decode() + "\n")
        except Exception:
            pass
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"❌ DeepSeek 输出不是合法 JSON: {e}\n")
        sys.exit(3)

    # ── Step 4: 写 YAML ──
    import yaml  # noqa: 延迟 import
    yaml_path = Path("notice.yaml")
    yaml_path.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # ── Step 5: 终端预览 ──
    print(render_text(data))
    print()
    sys.stderr.write(f"✓ 已写入 {yaml_path}\n")
    sys.stderr.write("→ PowerShell 敲 notice-open 直接出新 docx\n")


if __name__ == "__main__":
    main()