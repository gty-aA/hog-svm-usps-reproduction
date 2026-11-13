"""Insert the final public GitHub URL and a clickable hyperlink into the DOCX."""

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
from docx.shared import Pt, RGBColor


URL = "https://github.com/gty-aA/hog-svm-usps-reproduction"
OLD = "GitHub公网仓库链接在获得作者账号授权后发布，仓库名为hog-svm-usps-reproduction。"


def add_hyperlink(paragraph, text: str, url: str) -> None:
    relationship_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F5A6F")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "21")
    run_properties.extend([color, underline, size])
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.extend([run_properties, text_node])
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def main() -> None:
    path = ROOT / "paper" / "HOG_SVM_USPS_Reproduction_Paper.docx"
    document = Document(path)
    updated = False
    for paragraph in document.paragraphs:
        if OLD not in paragraph.text:
            continue
        text = paragraph.text.replace(OLD, "").rstrip()
        for run in list(paragraph.runs):
            paragraph._p.remove(run._r)
        prefix = paragraph.add_run(text)
        prefix.font.name = "Times New Roman"
        prefix.font.size = Pt(10.5)
        prefix._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
        separator = paragraph.add_run(" ")
        separator.font.size = Pt(10.5)
        add_hyperlink(paragraph, URL, URL)
        updated = True
        break
    if not updated:
        raise RuntimeError("Public URL paragraph was not found.")
    document.save(path)
    print(f"Inserted clickable public URL into {path}")


if __name__ == "__main__":
    main()
