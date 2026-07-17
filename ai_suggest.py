#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_suggest.py — 隐患 → 整改建议自动生成器 (DeepSeek API)

用法:
  echo "电线泡水没处理" | ./venv/bin/python ai_suggest.py
  ./venv/bin/python ai_suggest.py 电线泡水
  ./venv/bin/python ai_suggest.py -i     # 交互式

输出:
  - 完整通知书文本(可直接复制到 Word 模板)
  - 同时写一份 YAML 到 ./notice.yaml(供 notice-open 生成 docx)
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


PROMPT = """你是建筑施工安全员,负责给一个具体隐患写整改通知的核心内容。
请只输出合法 JSON,不要任何解释,不要 markdown 代码块。

输入:
- 隐患描述: {hazard}
- 今天日期: {today}
- 整改期限: {deadline} 天

输出字段(全部必须;无法确定的填占位字符串):
- to_unit: "XX项目部"
- from_unit: "安监部"
- issue_date: "{today}"
- context: "日常巡检"
- location: 推断的位置(如"施工现场临时用电区域")
- regulation_name: 适用的规范,带书名号
- regulation_code: 编号(如 JGJ 46-2005)
- violation_clause: 具体违反的条款(尽量引到章/节/条)
- hazard: 一句正式书面语的隐患描述
- hazard_figures: "" (留空,贴图后填)
- regulation_figures: "" (留空)
- requirements: 数组,3-5 条整改要求,每条"动词开头,具体可执行"
- deadline_days: {deadline}
- penalty_doc: "施工现场奖惩实施细则"
- penalty: "违约扣款"
- doc_number: ""

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

整改要求原则(自动生成时遵循):
1. 第 1 条用 "立即 ..." 开头 (应急措施)
2. 第 2 条用 "全面 ..." 开头 (横向排查)
3. 第 3 条用 "严格执行 ..." 开头 (规章升级)
- 全用住建部/建设部正式公文口吻,不要口语化。
- 引用条款时尽量精确(如"违反《…》第7.1.6条")。
"""


def call_deepseek(hazard: str, today: str, deadline: int = 3) -> dict:
    prompt = PROMPT.format(hazard=hazard, today=today, deadline=deadline)
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500,
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
    iso = d.get("regulation_name", "").strip("《》")
    out = []
    out.append("安全隐患整改通知书")
    if d.get("doc_number"):
        out.append(d["doc_number"])
        out.append("")
    out.append(f"致:{d.get('to_unit', 'XX项目部')}:")
    out.append("")
    clause = d.get("violation_clause") or "相关要求"
    out.append(
        f"　　{d.get('issue_date', '')},"
        f"{d.get('from_unit', '安监部')}于"
        f"{d.get('context', '日常巡检')}中,"
        f"发现你单位{d.get('location', '施工现场')}"
        f"违反《{iso}》"
        f"({d.get('regulation_code', '')}){clause},"
        f"{d.get('hazard', '')},未及时整改。"
    )
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


def main():
    hazard = ""
    if len(sys.argv) > 1 and sys.argv[1] != "-i":
        hazard = " ".join(sys.argv[1:])
    elif len(sys.argv) > 1 and sys.argv[1] == "-i":
        hazard = input("请描述隐患: ").strip()
    else:
        hazard = sys.stdin.read().strip()

    if not hazard:
        sys.stderr.write("⚠ 没收到隐患描述。\n")
        sys.stderr.write('用法: ai_suggest.py "电线泡水"\n')
        sys.exit(1)

    t = date.today()
    today = f"{t.year}年{t.month}月{t.day}日"

    sys.stderr.write(f"🔄 调 DeepSeek ... ({hazard})\n")
    try:
        data = call_deepseek(hazard, today)
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
