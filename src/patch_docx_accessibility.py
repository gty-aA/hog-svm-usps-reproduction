"""Add figure alternative text to an already-assembled DOCX."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def normalize_table_widths(table) -> None:
    grid_widths = [
        int(column.get(qn("w:w"))) for column in table._tbl.tblGrid.gridCol_lst
    ]
    for row in table.rows:
        for cell, width in zip(row.cells, grid_widths):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")


def main() -> None:
    path = ROOT / "paper" / "HOG_SVM_USPS_Reproduction_Paper.docx"
    document = Document(path)
    captions = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.style.name == "FigureCaption"
    ]
    if len(captions) != len(document.inline_shapes):
        raise RuntimeError(
            f"Expected one caption per image, got {len(captions)} captions "
            f"and {len(document.inline_shapes)} images"
        )
    for shape, caption in zip(document.inline_shapes, captions):
        shape._inline.docPr.set("descr", caption)
    for table in document.tables:
        normalize_table_widths(table)
    document.save(path)
    print(f"Added alternative text to {len(captions)} figures in {path}")


if __name__ == "__main__":
    main()
