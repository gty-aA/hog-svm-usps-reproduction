"""Build the final bilingual academic paper from the Markdown source."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


SOURCE = ROOT / "paper" / "manuscript.md"
OUTPUT = ROOT / "paper" / "HOG_SVM_USPS_Reproduction_Paper.docx"

INK = "17394A"
MID_BLUE = "1F5A6F"
GRAY = "53626A"
LIGHT_RULE = "B8C8D0"
TABLE_HEADER = "DCEAF0"


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in [
        ("top", top),
        ("start", start),
        ("bottom", bottom),
        ("end", end),
    ]:
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_cm: float) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_cm: list[float]) -> None:
    total_dxa = int(sum(widths_cm) * 567)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total_dxa))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_grid = tbl.tblGrid
    for index, grid_col in enumerate(tbl_grid.gridCol_lst):
        grid_col.set(qn("w:w"), str(int(widths_cm[index] * 567)))
    for row in table.rows:
        for cell, width in zip(row.cells, widths_cm):
            set_cell_width(cell, width)
            set_cell_margins(cell)


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color=LIGHT_RULE, size=4) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:color"), color)


def repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def set_run_font(run, chinese: str, latin: str, size: float, bold=False, italic=False) -> None:
    run.font.name = latin
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string("1B1B1B")
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:eastAsia"), chinese)
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)


def add_inline_runs(paragraph, text: str, style: dict) -> None:
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        content = part[2:-2] if bold else part
        run = paragraph.add_run(content)
        set_run_font(
            run,
            chinese=style.get("chinese", "宋体"),
            latin=style.get("latin", "Times New Roman"),
            size=style.get("size", 10.5),
            bold=bold or style.get("bold", False),
            italic=style.get("italic", False),
        )


def add_page_number(paragraph) -> None:
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)


def add_toc(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "打开文档后右键更新目录域"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, placeholder, end])


def add_horizontal_rule(paragraph, color=LIGHT_RULE) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def add_cover(document: Document) -> None:
    for _ in range(2):
        document.add_paragraph()
    kicker = document.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = kicker.add_run("COMPUTER VISION  ·  REPRODUCTION STUDY")
    set_run_font(run, "微软雅黑", "Arial", 9, bold=True)
    run.font.color.rgb = RGBColor.from_string(MID_BLUE)
    kicker.paragraph_format.space_after = Pt(18)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(12)
    title.paragraph_format.space_after = Pt(10)
    run = title.add_run("基于方向梯度直方图与RBF支持向量机的\n手写数字识别复现及鲁棒性分析")
    set_run_font(run, "黑体", "Arial", 20, bold=True)
    run.font.color.rgb = RGBColor.from_string(INK)

    rule = document.add_paragraph()
    rule.paragraph_format.space_before = Pt(10)
    rule.paragraph_format.space_after = Pt(14)
    add_horizontal_rule(rule)

    english_title = document.add_paragraph()
    english_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    english_title.paragraph_format.left_indent = Cm(1.1)
    english_title.paragraph_format.right_indent = Cm(1.1)
    english_title.paragraph_format.space_after = Pt(28)
    run = english_title.add_run(
        "Reproducing HOG-SVM for Handwritten Digit Recognition:\n"
        "An Empirical Study of Representation and Robustness"
    )
    set_run_font(run, "Times New Roman", "Times New Roman", 14, bold=False, italic=True)
    run.font.color.rgb = RGBColor.from_string(MID_BLUE)

    for label, value in [
        ("作    者", "XXX"),
        ("单    位", "XX大学  计算机科学与技术学院"),
        ("研究方向", "计算机视觉 · 模式识别 · 可复现实验"),
        ("日    期", "2026年11月13日"),
    ]:
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(9)
        run = p.add_run(f"{label}    {value}")
        set_run_font(run, "宋体", "Times New Roman", 11)

    document.add_paragraph()
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.left_indent = Cm(2.0)
    note.paragraph_format.right_indent = Cm(2.0)
    run = note.add_run("本文全部实验数值由本地代码实际运行产生\n代码、权重与逐样本结果随论文一并交付")
    set_run_font(run, "宋体", "Times New Roman", 8.5)
    run.font.color.rgb = RGBColor.from_string(GRAY)


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.35)
    section.bottom_margin = Cm(2.25)
    section.left_margin = Cm(2.45)
    section.right_margin = Cm(2.45)
    section.header_distance = Cm(1.15)
    section.footer_distance = Cm(1.05)
    section.different_first_page_header_footer = True

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True

    for style_name, size, color, before, after in [
        ("Heading 1", 14, INK, 12, 6),
        ("Heading 2", 12, MID_BLUE, 9, 4),
        ("Heading 3", 11, MID_BLUE, 7, 3),
    ]:
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.line_spacing = 1.2

    for name, size, color, before, after, align in [
        ("FigureCaption", 9, GRAY, 3, 8, WD_ALIGN_PARAGRAPH.CENTER),
        ("TableCaption", 9.5, INK, 7, 4, WD_ALIGN_PARAGRAPH.LEFT),
        ("Equation", 10.5, "1B1B1B", 3, 3, WD_ALIGN_PARAGRAPH.CENTER),
        ("ReferenceEntry", 9.5, "1B1B1B", 0, 3, WD_ALIGN_PARAGRAPH.JUSTIFY),
        ("CodeBlock", 9, "26343B", 3, 5, WD_ALIGN_PARAGRAPH.LEFT),
    ]:
        style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        style.paragraph_format.alignment = align
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1.15

    ref_style = styles["ReferenceEntry"]
    ref_style.paragraph_format.left_indent = Cm(0.65)
    ref_style.paragraph_format.first_line_indent = Cm(-0.65)

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run("HOG-SVM 手写数字识别复现研究")
    set_run_font(run, "宋体", "Times New Roman", 8)
    run.font.color.rgb = RGBColor.from_string(GRAY)
    add_horizontal_rule(hp, "D6E0E5")

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number(fp)


def parse_table(lines: list[str], start: int):
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        line = lines[index].strip()
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            rows.append(cells)
        index += 1
    return rows, index


def table_widths(column_count: int) -> list[float]:
    presets = {
        2: [4.2, 11.4],
        4: [2.2, 3.2, 3.3, 6.9],
        5: [4.1, 3.9, 2.8, 2.4, 2.4],
        7: [1.0, 1.45, 1.55, 1.65, 1.7, 1.55, 1.45],
        9: [3.2, 0.9, 2.1, 1.45, 1.5, 1.35, 1.4, 1.2, 1.35],
    }
    if column_count in presets:
        widths = presets[column_count]
    else:
        widths = [15.8 / column_count] * column_count
    scale = 15.8 / sum(widths)
    return [width * scale for width in widths]


def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    column_count = max(len(row) for row in rows)
    normal_rows = [row + [""] * (column_count - len(row)) for row in rows]
    table = document.add_table(rows=len(normal_rows), cols=column_count)
    table.style = "Table Grid"
    widths = table_widths(column_count)
    set_table_geometry(table, widths)
    repeat_table_header(table.rows[0])
    for row_index, values in enumerate(normal_rows):
        row = table.rows[row_index]
        if row_index == 0:
            shade_cell(row.cells[0], TABLE_HEADER)
        for col_index, value in enumerate(values):
            cell = row.cells[col_index]
            set_cell_border(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if row_index == 0:
                shade_cell(cell, TABLE_HEADER)
            p = cell.paragraphs[0]
            p.alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if col_index == 0 else WD_ALIGN_PARAGRAPH.CENTER
            )
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            add_inline_runs(
                p,
                value,
                {
                    "chinese": "宋体",
                    "latin": "Times New Roman",
                    "size": 8.2,
                    "bold": row_index == 0,
                },
            )
    document.add_paragraph().paragraph_format.space_after = Pt(0)


def add_figure(document: Document, source: str, caption: str) -> None:
    image_path = ROOT / source
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    inline_shape = run.add_picture(str(image_path), width=Cm(15.5))
    inline_shape._inline.docPr.set("descr", caption)

    cap = document.add_paragraph(style="FigureCaption")
    add_inline_runs(
        cap,
        caption,
        {"chinese": "宋体", "latin": "Times New Roman", "size": 8.8},
    )


def build() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    document = Document()
    configure_document(document)
    document.core_properties.title = "基于方向梯度直方图与RBF支持向量机的手写数字识别复现及鲁棒性分析"
    document.core_properties.subject = "计算机视觉复现研究"
    document.core_properties.author = "XXX"
    document.core_properties.keywords = "HOG; SVM; USPS; 手写数字识别; 复现实验; 鲁棒性"
    document.core_properties.comments = "All numerical results were generated by the accompanying code."

    add_cover(document)
    document.add_page_break()

    index = 0
    while index < len(lines) and lines[index].strip() != "## 中文摘要":
        index += 1

    in_references = False
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            add_table(document, rows)
            continue
        if stripped.startswith("[[FIGURE:") and stripped.endswith("]]"):
            body = stripped[9:-2]
            source, caption = body.split("|", 1)
            add_figure(document, source, caption)
            index += 1
            continue
        if stripped == "[PAGEBREAK]":
            document.add_page_break()
            index += 1
            continue
        if stripped == "[TOC]":
            toc_paragraph = document.add_paragraph()
            add_toc(toc_paragraph)
            index += 1
            continue
        if stripped.startswith("[EQ]"):
            p = document.add_paragraph(style="Equation")
            add_inline_runs(
                p,
                stripped[4:],
                {"chinese": "宋体", "latin": "Times New Roman", "size": 10.5},
            )
            index += 1
            continue
        if stripped.startswith("[CODE]"):
            p = document.add_paragraph(style="CodeBlock")
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.keep_together = True
            run = p.add_run(stripped[6:])
            set_run_font(run, "等线", "Consolas", 9)
            run.font.color.rgb = RGBColor.from_string("17394A")
            index += 1
            continue
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            p = document.add_paragraph(style="Heading 1")
            add_inline_runs(
                p,
                text,
                {"chinese": "黑体", "latin": "Times New Roman", "size": 14, "bold": True},
            )
            in_references = text == "参考文献"
            index += 1
            continue
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            if text == "Abstract":
                p = document.add_paragraph(style="Heading 1")
            else:
                p = document.add_paragraph(style="Heading 2")
            add_inline_runs(
                p,
                text,
                {"chinese": "黑体", "latin": "Times New Roman", "size": 12, "bold": True},
            )
            index += 1
            continue
        if stripped.startswith("- "):
            p = document.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            p.paragraph_format.space_after = Pt(4)
            add_inline_runs(
                p,
                stripped[2:],
                {"chinese": "宋体", "latin": "Times New Roman", "size": 10.5},
            )
            index += 1
            continue
        if stripped.startswith("**表") and stripped.endswith("**"):
            p = document.add_paragraph(style="TableCaption")
            add_inline_runs(
                p,
                stripped,
                {"chinese": "黑体", "latin": "Times New Roman", "size": 9.5, "bold": True},
            )
            index += 1
            continue
        if stripped.startswith("**关键词：**") or stripped.startswith("**Keywords:**"):
            p = document.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(10)
            add_inline_runs(
                p,
                stripped,
                {"chinese": "宋体", "latin": "Times New Roman", "size": 10},
            )
            index += 1
            continue
        if stripped.startswith("[") and re.match(r"^\[\d+\]", stripped):
            p = document.add_paragraph(style="ReferenceEntry")
            add_inline_runs(
                p,
                stripped,
                {"chinese": "宋体", "latin": "Times New Roman", "size": 9.5},
            )
            index += 1
            continue
        if in_references:
            p = document.add_paragraph(style="ReferenceEntry")
        else:
            p = document.add_paragraph()
        p.paragraph_format.widow_control = True
        add_inline_runs(
            p,
            stripped,
            {"chinese": "宋体", "latin": "Times New Roman", "size": 10.5},
        )
        index += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    build()
