#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全隐患整改通知书生成器
用法:
  python generate_notice.py <notice.yaml> [output.docx]

字段见同目录的 notice.yaml 示例。改 YAML 字段即可改通知内容。
"""

import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_cn_font(run, name="宋体"):
    """给 run 设置中文字体。"""
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)


def add_title(doc, text, size=22, font="黑体"):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = True
    set_cn_font(run, font)


def add_centered(doc, text, size=12, font="宋体"):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(size)
    set_cn_font(run, font)


def add_body(doc, text, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    run = p.add_run(text)
    run.font.size = Pt(12)
    set_cn_font(run)
    return p


def add_right(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.font.size = Pt(12)
    set_cn_font(run)


def init_doc():
    doc = Document()
    # 页面: A4, 上下左右 2.5cm
    section = doc.sections[0]
    for attr, val in [
        ("left_margin", Cm(2.5)),
        ("right_margin", Cm(2.5)),
        ("top_margin", Cm(2.5)),
        ("bottom_margin", Cm(2.5)),
    ]:
        setattr(section, attr, val)
    # 默认字体
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    style.font.size = Pt(12)
    return doc


def generate(data: dict, out_path: Path):
    doc = init_doc()

    # 标题
    add_title(doc, "安全隐患整改通知书")

    # 文号(可选)
    if data.get("doc_number"):
        add_centered(doc, data["doc_number"], size=12)

    add_body(doc, "")  # 空行

    # 抬头
    add_body(doc, f"致:{data['to_unit']}:", indent=False)

    # 正文中段
    main_text = (
        f"{data['issue_date']},"
        f"{data['from_unit']}于"
        f"{data.get('context', '日常巡检')}中,"
        f"发现你单位{data['location']}"
        f"严重违反《{data['regulation_name']}》"
        f"({data['regulation_code']})(见图{data.get('regulation_figures','')})"
        f"相关要求,"
        f"现场存在{data['hazard']}现象"
        f"(见图{data.get('hazard_figures','')})"
        f",未及时整改。"
    )
    add_body(doc, main_text, indent=True)

    add_body(doc, "")
    add_body(doc, "现对你单位要求如下:", indent=False)

    # 整改要求(列表)
    for i, req in enumerate(data["requirements"], 1):
        add_body(doc, f"{i}.{req}", indent=False)

    add_body(doc, "")

    # 闭环段
    deadline = data.get("deadline_days", 3)
    review = data.get("review_clause") or f"{data['from_unit']}将于整改完成后组织复查"
    feed_back = data.get("feedback_clause") or f"并将整改结果书面报{data['from_unit']}"
    tail = (
        f"本通知下发之日起 {deadline} 日内完成全部整改,"
        f"{feed_back}。"
        f"{review}。"
        f"逾期将按照《{data['penalty_doc']}》"
        f"对你单位进行{data.get('penalty', '违约扣款')}处理。"
    )
    add_body(doc, tail, indent=True)

    add_body(doc, "")
    add_body(doc, "")

    # 落款
    add_right(doc, f"发文单位:{data['from_unit']}(盖章)")
    add_right(doc, data["issue_date"])

    add_body(doc, "")
    add_body(doc, "签收人:_____________  签收日期:_____________")

    doc.save(out_path)


def dump_for_preview(out_path: Path):
    """把生成的 docx 段落提取出来,用于终端预览。"""
    d = Document(out_path)
    lines = []
    for p in d.paragraphs:
        t = p.text
        if t.strip() == "":
            continue
        if len(t) > 60 and not t.lstrip().startswith(("致:", "1.", "2.", "3.", "4.")):
            # 缩进的长段
            lines.append(f"　　{t}")
        elif t.lstrip().startswith(("1.", "2.", "3.", "4.")):
            lines.append(t)
        elif "签收" in t or "盖章" in t:
            lines.append("　　　　　　　　　　　　　　　　　　" + t)
        else:
            lines.append(t)
    return "\n".join(lines)


if __name__ == "__main__":
    yaml_path = Path(sys.argv[1] if len(sys.argv) > 1 else "notice.yaml")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "安全隐患整改通知书.docx")

    import yaml  # noqa: 这里才 import 避免顶层依赖
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    generate(data, out_path)
    print(f"✓ 已生成: {out_path.resolve()}")
    print("---文件预览(终端版)---")
    print(dump_for_preview(out_path))
