#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_suggest.py — 隐患 → 整改通知(N 条隐患 → 1 段描述 + N 条针对性整改)

用法:
  echo -e "电线泡水\\n高处未系安全带" | ./venv/bin/python ai_suggest.py
  ./venv/bin/python ai_suggest.py "电线泡水" "高处未系安全带" "基坑堆土超载"
  ./venv/bin/python ai_suggest.py -i   # 交互式,空行分隔多隐患,Ctrl-D/Ctrl-Z 结束
  cat hazards.txt | ./venv/bin/python ai_suggest.py

输出:
  - 完整通知书文本(可直接复制到 Word 模板)
  - 同时写一份 YAML 到 ./notice.yaml(供 notice-open / generate_notice.py 出 docx)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

# ── 读取 API key ──
api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    f = Path("~/.config/deepseek_key.txt").expanduser()
    if f.exists():
        api_key = f.read_text().strip()
if not api_key:
    sys.stderr.write("⚠ 未找到 DEEPSEEK_API_KEY。请跑 set-deepseek-key.ps1 配置。\n")
    sys.exit(1)


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


def call_deepseek(hazards: list, today: str, deadline: int = 3) -> dict:
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

    # 主体:一段话
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


def main():
    hazards: list = []

    # 1. 命令行参数(可以多个)
    if len(sys.argv) > 1 and sys.argv[1] != "-i":
        hazards = [s.strip() for s in sys.argv[1:] if s.strip()]
    # 2. 交互式
    elif len(sys.argv) > 1 and sys.argv[1] == "-i":
        sys.stderr.write("请逐条输入隐患(每行一条),输入空行结束:\n")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            hazards.append(line)
    # 3. stdin
    else:
        hazards = parse_hazards_from_stdin()

    if not hazards:
        sys.stderr.write("⚠ 没收到隐患描述。\n")
        sys.stderr.write('用法:\n')
        sys.stderr.write('  ai_suggest.py "隐患1" "隐患2" "隐患3"\n')
        sys.stderr.write('  echo "隐患1\\n隐患2" | ai_suggest.py\n')
        sys.stderr.write('  ai_suggest.py -i   # 交互式\n')
        sys.exit(1)

    t = date.today()
    today = f"{t.year}年{t.month}月{t.day}日"

    sys.stderr.write(f"🔄 调 DeepSeek ... ({len(hazards)} 条隐患)\n")
    for i, h in enumerate(hazards, 1):
        sys.stderr.write(f"   {i}. {h}\n")

    try:
        data = call_deepseek(hazards, today)
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

    import yaml  # noqa: 延迟 import
    yaml_path = Path("notice.yaml")
    yaml_path.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print(render_text(data))
    print()
    sys.stderr.write(f"✓ 已写入 {yaml_path}\n")
    sys.stderr.write("→ PowerShell 敲 notice-open 直接出新 docx\n")


if __name__ == "__main__":
    main()