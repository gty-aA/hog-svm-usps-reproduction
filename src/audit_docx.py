"""Structural audit for the final DOCX artifact."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

from docx import Document
from docx.oxml.ns import qn


def main() -> None:
    path = ROOT / "paper" / "HOG_SVM_USPS_Reproduction_Paper.docx"
    document = Document(path)
    section = document.sections[0]
    figures = [
        p.text for p in document.paragraphs if p.style.name == "FigureCaption"
    ]
    headings = {
        "Heading 1": sum(p.style.name == "Heading 1" for p in document.paragraphs),
        "Heading 2": sum(p.style.name == "Heading 2" for p in document.paragraphs),
    }
    alt_text = [shape._inline.docPr.get("descr") for shape in document.inline_shapes]
    table_checks = []
    for table_index, table in enumerate(document.tables, start=1):
        width_text = table._tbl.tblPr.find(qn("w:tblW")).get(qn("w:w"))
        grid_widths = [
            int(col.get(qn("w:w")))
            for col in table._tbl.tblGrid.gridCol_lst
        ]
        row_width_checks = []
        for row in table.rows:
            row_widths = []
            for cell in row.cells:
                tc_w = cell._tc.tcPr.find(qn("w:tcW"))
                row_widths.append(int(tc_w.get(qn("w:w"))))
            row_width_checks.append(sum(row_widths) == sum(grid_widths))
        table_checks.append(
            {
                "table": table_index,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "declared_width_dxa": int(width_text),
                "grid_width_dxa": sum(grid_widths),
                "widths_consistent": int(width_text) == sum(grid_widths),
                "all_rows_match_grid": all(row_width_checks),
            }
        )
    with zipfile.ZipFile(path) as archive:
        zip_integrity = archive.testzip() is None
        media = [name for name in archive.namelist() if name.startswith("word/media/")]

    findings = []
    if round(section.page_width.cm, 1) != 21.0 or round(section.page_height.cm, 1) != 29.7:
        findings.append("Page size is not A4 portrait.")
    if len(figures) != len(document.inline_shapes):
        findings.append("Figure caption count does not match image count.")
    if any(not value for value in alt_text):
        findings.append("One or more figures are missing alternative text.")
    if headings["Heading 1"] < 10 or headings["Heading 2"] < 20:
        findings.append("Heading hierarchy is unexpectedly sparse.")
    if not zip_integrity:
        findings.append("DOCX ZIP container is corrupt.")
    if any(
        not check["widths_consistent"] or not check["all_rows_match_grid"]
        for check in table_checks
    ):
        findings.append("At least one table has inconsistent DXA geometry.")

    report = {
        "file": str(path.relative_to(ROOT)),
        "page_size_cm": [round(section.page_width.cm, 2), round(section.page_height.cm, 2)],
        "margins_cm": {
            "top": round(section.top_margin.cm, 2),
            "bottom": round(section.bottom_margin.cm, 2),
            "left": round(section.left_margin.cm, 2),
            "right": round(section.right_margin.cm, 2),
        },
        "paragraphs": len(document.paragraphs),
        "headings": headings,
        "tables": len(document.tables),
        "figures": len(document.inline_shapes),
        "media_files": len(media),
        "zip_integrity": zip_integrity,
        "alt_text_complete": all(bool(value) for value in alt_text),
        "table_geometry": table_checks,
        "findings": findings,
        "pass": not findings,
    }
    output = ROOT / "results" / "docx_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
