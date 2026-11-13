"""Build a presentation PDF from the same Markdown manuscript.

The DOCX is the editable artifact. This HTML-to-PDF route provides a portable
read-only copy when desktop office automation is unavailable.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import pymupdf


SOURCE = ROOT / "paper" / "manuscript.md"
HTML_PATH = ROOT / "paper" / "paper_render.html"
TEMP_PDF = ROOT / "qa" / "paper_temp.pdf"
OUTPUT_PDF = ROOT / "paper" / "HOG_SVM_USPS_Reproduction_Paper.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1">\1</a>',
        escaped,
    )


def parse_table(lines: list[str], start: int):
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            rows.append(cells)
        index += 1
    return rows, index


def collect_toc(lines: list[str]) -> list[tuple[int, str, str]]:
    entries = []
    started = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[TOC]":
            started = True
            continue
        if not started:
            continue
        if stripped.startswith("# ") and stripped != "# 目录":
            entries.append((1, stripped[2:], f"sec-{len(entries)}"))
        elif stripped.startswith("## ") and stripped not in {"## 英文题目", "## 中文摘要", "## Abstract"}:
            entries.append((2, stripped[3:], f"sec-{len(entries)}"))
    return entries


def render_body(lines: list[str], toc_entries: list[tuple[int, str, str]]) -> tuple[str, list[dict]]:
    output = []
    index = 0
    heading_index = 0
    heading_records = []
    while index < len(lines) and lines[index].strip() != "## 中文摘要":
        index += 1
    in_references = False
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            if rows:
                output.append("<table><thead><tr>")
                output.append("".join(f"<th>{inline(cell)}</th>" for cell in rows[0]))
                output.append("</tr></thead><tbody>")
                for row in rows[1:]:
                    output.append("<tr>")
                    output.append("".join(f"<td>{inline(cell)}</td>" for cell in row))
                    output.append("</tr>")
                output.append("</tbody></table>")
            continue
        if stripped.startswith("[[FIGURE:") and stripped.endswith("]]"):
            source, caption = stripped[9:-2].split("|", 1)
            uri = (ROOT / source).resolve().as_uri()
            output.append(
                f'<figure><img src="{uri}" alt="{html.escape(caption)}">'
                f"<figcaption>{inline(caption)}</figcaption></figure>"
            )
            index += 1
            continue
        if stripped == "[PAGEBREAK]":
            output.append('<div class="page-break"></div>')
            index += 1
            continue
        if stripped == "[TOC]":
            output.append('<nav class="toc">')
            for level, title, anchor in toc_entries:
                if level == 1:
                    output.append(
                        f'<div class="toc-row level1"><a href="#{anchor}">{html.escape(title)}</a>'
                        f'<span class="dots"></span><span class="page" data-title="{html.escape(title)}"></span></div>'
                    )
                else:
                    output.append(
                        f'<div class="toc-row level2"><a href="#{anchor}">{html.escape(title)}</a>'
                        f'<span class="dots"></span><span class="page" data-title="{html.escape(title)}"></span></div>'
                    )
            output.append("</nav>")
            index += 1
            continue
        if stripped.startswith("[EQ]"):
            output.append(f'<div class="equation">{html.escape(stripped[4:])}</div>')
            index += 1
            continue
        if stripped.startswith("[CODE]"):
            output.append(f"<pre><code>{html.escape(stripped[6:])}</code></pre>")
            index += 1
            continue
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            anchor = toc_entries[heading_index][2] if heading_index < len(toc_entries) else f"h{heading_index}"
            heading_records.append({"id": anchor, "text": text})
            heading_index += 1
            output.append(f'<h1 id="{anchor}">{inline(text)}</h1>')
            in_references = text == "参考文献"
            index += 1
            continue
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            if text == "Abstract":
                anchor = "abstract-en"
                output.append(f'<h1 id="{anchor}">{inline(text)}</h1>')
            elif text == "中文摘要":
                anchor = "abstract-cn"
                output.append(f'<h1 id="{anchor}">{inline(text)}</h1>')
            else:
                anchor = toc_entries[heading_index][2] if heading_index < len(toc_entries) else f"h{heading_index}"
                heading_records.append({"id": anchor, "text": text})
                heading_index += 1
                output.append(f'<h2 id="{anchor}">{inline(text)}</h2>')
            index += 1
            continue
        if stripped.startswith("- "):
            output.append(f"<li>{inline(stripped[2:])}</li>")
            index += 1
            continue
        if stripped.startswith("**表") and stripped.endswith("**"):
            output.append(f'<div class="table-caption">{inline(stripped)}</div>')
            index += 1
            continue
        cls = "reference" if in_references or re.match(r"^\[\d+\]", stripped) else ""
        output.append(f'<p class="{cls}">{inline(stripped)}</p>')
        index += 1
    return "\n".join(output), heading_records


CSS = """
@page {
  size: A4;
  margin: 25mm 20mm 22mm 20mm;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0;
  color: #1b1b1b;
  font-family: "SimSun", "Times New Roman", serif;
  font-size: 10.5pt;
  line-height: 1.72;
}
p { margin: 0 0 6.5pt; text-align: justify; }
h1 {
  color: #17394A;
  font-family: "SimHei", sans-serif;
  font-size: 15pt;
  line-height: 1.25;
  margin: 15pt 0 7pt;
  padding-bottom: 4pt;
  border-bottom: 0.7pt solid #B8C8D0;
  page-break-after: avoid;
}
h2 {
  color: #1F5A6F;
  font-family: "SimHei", sans-serif;
  font-size: 12pt;
  margin: 11pt 0 4.5pt;
  page-break-after: avoid;
}
li { margin: 0 0 4pt 15pt; text-align: justify; }
.page-break { break-before: page; }
.cover {
  height: 240mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  page-break-after: always;
}
.cover .kicker {
  color: #1F5A6F;
  font-family: "Arial", sans-serif;
  font-size: 8.5pt;
  font-weight: 700;
  letter-spacing: 2pt;
  margin-bottom: 25pt;
}
.cover .title {
  color: #17394A;
  font-family: "SimHei", sans-serif;
  font-size: 22pt;
  font-weight: 700;
  line-height: 1.55;
}
.cover .rule { width: 75%; border-top: 1pt solid #B8C8D0; margin: 22pt auto; }
.cover .en-title {
  color: #1F5A6F;
  font-family: "Times New Roman", serif;
  font-size: 15pt;
  font-style: italic;
  line-height: 1.55;
  margin-bottom: 35pt;
}
.cover .meta { font-size: 11pt; line-height: 2.1; }
.cover .note { color: #53626A; font-size: 8.5pt; margin-top: 45pt; }
.toc { margin-top: 8pt; }
.toc-row { display: flex; align-items: baseline; font-size: 10.2pt; margin: 5pt 0; }
.toc-row a { color: inherit; text-decoration: none; }
.toc-row.level2 { margin-left: 18pt; font-size: 9.5pt; color: #3C4D55; }
.dots { flex: 1; border-bottom: 0.7pt dotted #AAB6BC; margin: 0 6pt 3pt; }
.page { min-width: 20pt; text-align: right; }
figure { margin: 9pt 0 10pt; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 112mm; }
figcaption { color: #53626A; font-size: 8.8pt; line-height: 1.35; margin-top: 3pt; }
table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 3pt 0 10pt;
  font-size: 7.6pt;
  line-height: 1.35;
  page-break-inside: auto;
}
th, td { border: 0.55pt solid #B8C8D0; padding: 4pt 3.5pt; vertical-align: middle; overflow-wrap: anywhere; }
th { background: #DCEAF0; color: #17394A; font-weight: 700; text-align: center; }
td:first-child { text-align: left; }
td { text-align: center; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
.table-caption { color: #17394A; font-family: "SimHei", sans-serif; font-size: 9.2pt; font-weight: 700; margin: 8pt 0 3pt; page-break-after: avoid; }
.equation {
  font-family: "Cambria Math", "Times New Roman", serif;
  text-align: center;
  font-size: 10pt;
  margin: 4pt 0;
}
pre {
  background: #F2F5F6;
  border-left: 2.5pt solid #1F5A6F;
  padding: 7pt 10pt;
  font-family: "Consolas", monospace;
  font-size: 8.5pt;
  white-space: pre-wrap;
  page-break-inside: avoid;
}
.reference { font-size: 9pt; line-height: 1.45; padding-left: 18pt; text-indent: -18pt; margin-bottom: 2.5pt; }
strong { color: inherit; }
"""


def build_html(page_map: dict[str, int] | None = None) -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    toc_entries = collect_toc(lines)
    body, _ = render_body(lines, toc_entries)
    if page_map:
        for title, page in page_map.items():
            escaped_title = html.escape(title, quote=True)
            body = body.replace(
                f'data-title="{escaped_title}"></span>',
                f'data-title="{escaped_title}">{page}</span>',
            )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>HOG-SVM USPS Reproduction</title>
<style>{CSS}</style></head><body>
<section class="cover">
  <div class="kicker">COMPUTER VISION · REPRODUCTION STUDY</div>
  <div class="title">基于方向梯度直方图与RBF支持向量机的<br>手写数字识别复现及鲁棒性分析</div>
  <div class="rule"></div>
  <div class="en-title">Reproducing HOG-SVM for Handwritten Digit Recognition:<br>An Empirical Study of Representation and Robustness</div>
  <div class="meta">作　者：XXX<br>单　位：XX大学　计算机科学与技术学院<br>研究方向：计算机视觉 · 模式识别 · 可复现实验<br>日　期：2026年11月13日</div>
  <div class="note">本文全部实验数值由本地代码实际运行产生<br>代码、权重与逐样本结果随论文一并交付</div>
</section>
{body}
</body></html>"""
    HTML_PATH.write_text(document, encoding="utf-8")


def edge_print(output: Path) -> None:
    profile = ROOT / "qa" / "edge-profile"
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        str(EDGE),
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--disable-extensions",
        f"--user-data-dir={profile}",
        "--allow-file-access-from-files",
        f"--print-to-pdf={output}",
        "--no-pdf-header-footer",
        HTML_PATH.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, timeout=120)
    stderr = result.stderr.decode("utf-8", errors="replace")
    stdout = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0 or not output.exists():
        raise RuntimeError(
            f"Edge PDF export failed ({result.returncode}): {stderr[-2000:]}\n{stdout[-1000:]}"
        )


def locate_pages(
    pdf_path: Path, entries: list[tuple[int, str, str]]
) -> dict[str, int]:
    document = pymupdf.open(pdf_path)
    result = {}
    start = 0
    for level, title, _ in entries:
        normalized = re.sub(r"\s+", "", title)
        minimum_size = 13.0 if level == 1 else 10.8
        found = None
        for index in range(start, len(document)):
            blocks = document[index].get_text("dict").get("blocks", [])
            for block in blocks:
                lines = block.get("lines", [])
                if not lines:
                    continue
                block_text = "".join(
                    span.get("text", "")
                    for line in lines
                    for span in line.get("spans", [])
                )
                max_size = max(
                    (span.get("size", 0) for line in lines for span in line.get("spans", [])),
                    default=0,
                )
                if normalized in re.sub(r"\s+", "", block_text) and max_size >= minimum_size:
                    found = index
                    break
            if found is not None:
                break
        if found is not None:
            result[title] = found + 1
            start = found
    document.close()
    return result


def add_furniture(pdf_path: Path) -> None:
    document = pymupdf.open(pdf_path)
    total = len(document)
    title = "HOG-SVM 手写数字识别复现研究"
    for index, page in enumerate(document):
        if index == 0:
            continue
        width = page.rect.width
        height = page.rect.height
        page.insert_text((width - 65, 30), title, fontname="helv", fontsize=7, color=(0.35, 0.42, 0.46))
        page.draw_line((55, 38), (width - 55, 38), color=(0.72, 0.78, 0.81), width=0.4)
        page.draw_line((55, height - 36), (width - 55, height - 36), color=(0.80, 0.84, 0.86), width=0.35)
        label = f"{index + 1} / {total}"
        text_width = pymupdf.get_text_length(label, fontname="helv", fontsize=7.5)
        page.insert_text((width / 2 - text_width / 2, height - 22), label, fontname="helv", fontsize=7.5, color=(0.35, 0.42, 0.46))
    document.saveIncr()
    document.close()


def write_qa_report(pdf_path: Path) -> None:
    document = pymupdf.open(pdf_path)
    report = {"page_count": len(document), "pages": []}
    for index, page in enumerate(document):
        blocks = page.get_text("blocks")
        images = page.get_images(full=True)
        text = page.get_text("text").strip()
        report["pages"].append(
            {
                "page": index + 1,
                "characters": len(text),
                "text_blocks": len(blocks),
                "images": len(images),
                "width_pt": round(page.rect.width, 2),
                "height_pt": round(page.rect.height, 2),
            }
        )
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(
            ROOT / "qa" / f"paper-page-{index + 1:02d}.png"
        )
    report["empty_content_pages"] = [
        row["page"] for row in report["pages"][1:] if row["characters"] < 20
    ]
    report["embedded_image_count"] = sum(row["images"] for row in report["pages"])
    document.close()
    (ROOT / "qa" / "pdf_qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    (ROOT / "qa").mkdir(exist_ok=True)
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    toc_entries = collect_toc(lines)
    build_html()
    edge_print(TEMP_PDF)
    page_map = locate_pages(TEMP_PDF, toc_entries)
    build_html(page_map)
    edge_print(OUTPUT_PDF)
    add_furniture(OUTPUT_PDF)
    write_qa_report(OUTPUT_PDF)
    print(f"Saved {OUTPUT_PDF}")
    print(f"TOC page map entries: {len(page_map)}")
    print(f"QA report: {ROOT / 'qa' / 'pdf_qa.json'}")


if __name__ == "__main__":
    main()
