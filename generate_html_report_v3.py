from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from html import escape
from pathlib import Path


def esc(v):
    return "" if v is None else escape(str(v))


def nl2html(text: str | None) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    paragraphs = []
    for block in value.split("\n\n"):
        lines = [esc(line) for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        paragraphs.append(f"<p>{'<br>'.join(lines)}</p>")
    return "".join(paragraphs)


def list_items(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return "<li>Inga uppgifter att visa.</li>"
    return "".join(f"<li>{esc(item)}</li>" for item in cleaned)


def find_browser() -> str | None:
    candidates = [
        shutil.which("msedge"),
        shutil.which("microsoft-edge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def _generate_pdf_with_browser(html_path: Path, pdf_path: Path, browser: str) -> None:
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        timeout=30,
    )


def _generate_pdf_with_weasyprint(html_path: Path, pdf_path: Path) -> None:
    from weasyprint import HTML

    HTML(filename=str(html_path)).write_pdf(str(pdf_path))


def _write_minimal_pdf(pdf_path: Path, text: str) -> None:
    # Sista fallbacken om varken Chrome/Chromium eller WeasyPrint finns i servermiljön.
    # Den skapar en enkel, giltig PDF så att hela rapportflödet inte kraschar.
    import re
    import textwrap

    cleaned = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    cleaned = re.sub(r"<script.*?</script>", "", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    lines = [
        "PDF-renderare saknas i servermiljön.",
        "HTML-rapporten skapades korrekt, men layout-PDF kunde inte renderas.",
        "",
        *textwrap.wrap(cleaned[:3500], 92),
    ]

    stream_parts = ["BT /F1 9 Tf 40 800 Td"]
    for line in lines[:70]:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_parts.append(f"({safe}) Tj 0 -12 Td")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", "replace")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF".encode())
    pdf_path.write_bytes(out)


def generate_pdf(html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # WeasyPrint är bäst i servermiljöer som Render eftersom det inte kräver Chrome/Edge.
    try:
        _generate_pdf_with_weasyprint(html_path, pdf_path)
        return
    except Exception as exc:
        print(f"VARNING: WeasyPrint kunde inte skapa PDF ({exc}). Försöker med Chrome/Chromium.")

    browser = find_browser()
    if browser:
        try:
            _generate_pdf_with_browser(html_path, pdf_path, browser)
            return
        except Exception as exc:
            print(f"VARNING: Chrome/Chromium kunde inte skapa PDF ({exc}). Skapar enkel fallback-PDF så flödet inte kraschar.")
    else:
        print("VARNING: Hittar varken WeasyPrint eller Chrome/Chromium. Skapar enkel fallback-PDF så flödet inte kraschar.")

    _write_minimal_pdf(pdf_path, html_path.read_text(encoding="utf-8", errors="replace"))


def status_class(status: str) -> str:
    return {
        "otjänligt": "status-unfit",
        "tjänligt med anmärkning": "status-remark",
        "tjänligt": "status-good",
        "ej bedömd": "status-unknown",
    }.get((status or "").strip().lower(), "status-unknown")


def status_label(status: str) -> str:
    return {
        "otjänligt": "Otjänligt",
        "tjänligt med anmärkning": "Tjänligt med anmärkning",
        "tjänligt": "Tjänligt",
        "ej bedömd": "Ej bedömd",
    }.get((status or "").strip().lower(), status)


def format_reference(ref: dict | None, reference_text: str | None = None) -> str:
    if ref:
        return (
            f"<div><strong>Enhet:</strong> {esc(ref.get('unit', '-'))}</div>"
            f"<div><strong>Tjänligt med anmärkning:</strong> {esc(ref.get('remark', '-'))}</div>"
            f"<div><strong>Otjänligt:</strong> {esc(ref.get('unfit', '-'))}</div>"
        )
    return esc(reference_text or "Riktvärde saknas eller är inte angivet i aktuell tabell.")


def build_parameter_rows(parameters: list[dict]) -> str:
    order = {"otjänligt": 0, "tjänligt med anmärkning": 1, "tjänligt": 2, "ej bedömd": 3}
    sorted_params = sorted(
        parameters,
        key=lambda p: (
            order.get((p.get("status") or "").strip().lower(), 9),
            p.get("category", ""),
            p.get("parameter_display", p.get("parameter", "")),
        ),
    )
    rows = []
    for p in sorted_params:
        value = f"{(p.get('value_text') or '').strip()} {(p.get('unit') or '').strip()}".strip()
        rows.append(
            f"<tr class=\"{status_class(p.get('status'))}\">"
            f"<td>{esc(p.get('parameter_display'))}</td>"
            f"<td>{esc(value)}</td>"
            f"<td>{esc(p.get('category'))}</td>"
            f"<td>{format_reference(p.get('reference_values'), p.get('reference_text'))}</td>"
            f"<td>{esc(status_label(p.get('status', '')))}</td>"
            f"</tr>"
        )
    return "".join(rows)


def build_findings_html(findings: list[dict]) -> str:
    if not findings:
        return '<p class="empty">Inga avvikande fynd att prioritera.</p>'

    blocks = []
    for item in findings:
        blocks.append(
            f"""
            <article class=\"finding {status_class(item.get('status'))}\">
              <div class=\"finding-head\">{esc(item.get('display_name'))}: {esc(item.get('value'))}</div>
              <div class=\"meta-row\"><strong>Status:</strong> {esc(status_label(item.get('status', '')))}</div>
              <div class=\"meta-row\"><strong>Prioritet:</strong> {esc(item.get('priority_label'))}</div>
              {nl2html(item.get('explanation'))}
            </article>
            """
        )
    return "".join(blocks)


def generate_html(input_path: str = "report_model_v3.json", output_path: str = "report_v3.html") -> None:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with Path(input_path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    meta = data.get("metadata", {})
    sections = data.get("generated_sections", {})
    findings = data.get("priority_findings", [])
    positives = data.get("positive_observations", [])
    not_assessed = data.get("not_assessed_observations", [])
    parameters = data.get("parameters", [])

    html = f"""
<!doctype html>
<html lang=\"sv\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Vattenrapport</title>
  <style>
    @page {{
      size: A4;
      margin: 9mm 10mm 10mm 10mm;
    }}

    :root {{
      --ink: #111827;
      --text: #334155;
      --muted: #64748b;
      --line: #dbe3ee;
      --line-soft: #edf2f7;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --brand: #0f766e;
      --brand-dark: #0f4f4a;
      --brand-soft: #e6fffb;
      --blue-soft: #eff6ff;
      --warn-soft: #fff7ed;
      --warn-line: #fdba74;
      --danger-soft: #fff1f2;
      --danger-line: #fda4af;
      --good-soft: #f0fdf4;
      --good-line: #86efac;
      --unknown-soft: #f8fafc;
      --unknown-line: #cbd5e1;
      --radius-lg: 14px;
      --radius-md: 10px;
      --radius-sm: 999px;
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12.2px;
      line-height: 1.48;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    .page {{
      width: 100%;
      margin: 0;
      padding: 0;
    }}

    .topbar {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 72mm;
      gap: 8mm;
      align-items: stretch;
      margin-bottom: 7mm;
    }}

    .brand-block {{
      border-radius: 18px;
      padding: 7mm 7mm 6mm;
      background: linear-gradient(135deg, #0f766e 0%, #0f4f4a 100%);
      color: #ffffff;
    }}

    .eyebrow {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: var(--radius-sm);
      background: rgba(255,255,255,0.16);
      color: #d9fffb;
      font-size: 9.2px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1, h2, h3 {{
      margin: 0;
      line-height: 1.15;
      color: var(--ink);
    }}

    .brand-block h1 {{
      margin-top: 7px;
      color: #ffffff;
      font-size: 31px;
      letter-spacing: -0.035em;
    }}

    .brand-subtitle {{
      margin-top: 5px;
      color: #d9fffb;
      font-size: 12.3px;
    }}

    h2 {{ font-size: 18px; letter-spacing: -0.02em; }}
    h3 {{ font-size: 13.5px; letter-spacing: -0.01em; }}

    p {{
      margin: 0.45em 0 0;
      color: var(--text);
    }}

    strong {{ color: var(--ink); font-weight: 700; }}
    section {{ margin-top: 5.3mm; }}

    .report-meta {{
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--panel);
      padding: 5mm;
      font-size: 10.8px;
    }}

    .meta-line {{
      display: grid;
      grid-template-columns: 1fr 1.35fr;
      gap: 8px;
      padding: 4px 0;
      border-bottom: 1px solid var(--line-soft);
    }}

    .meta-line:last-child {{ border-bottom: 0; }}
    .meta-line span:first-child {{ color: var(--muted); }}
    .meta-line span:last-child {{ color: var(--ink); font-weight: 700; text-align: right; overflow-wrap: anywhere; }}

    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 63mm;
      gap: 5mm;
      align-items: stretch;
    }}

    .hero-title {{
      position: relative;
      padding: 6mm;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }}

    .hero-title:before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      border-radius: var(--radius-lg) 0 0 var(--radius-lg);
      background: var(--brand);
    }}

    .hero-title p {{
      max-width: none;
      font-size: 12.3px;
      color: var(--text);
    }}

    .status-panel {{
      display: grid;
      gap: 3mm;
      align-content: start;
    }}

    .status-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 10px 11px;
      background: #ffffff;
    }}

    .status-label {{
      font-size: 9.2px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 700;
    }}

    .status-value {{
      display: flex;
      align-items: center;
      gap: 7px;
      margin-top: 4px;
      font-weight: 800;
      font-size: 12.4px;
    }}

    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 99px;
      display: inline-block;
      background: #94a3b8;
      flex: 0 0 auto;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 4.5mm;
    }}

    .card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      padding: 4.8mm;
      background: #ffffff;
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 6px;
    }}

    .kicker {{
      color: var(--brand-dark);
      font-size: 9.2px;
      font-weight: 800;
      letter-spacing: 0.075em;
      text-transform: uppercase;
      margin-bottom: 3px;
    }}

    .finding {{
      border: 1px solid var(--line);
      border-left-width: 4px;
      border-radius: var(--radius-md);
      padding: 10px 11px;
      margin-top: 7px;
      background: #ffffff;
    }}

    .finding-head {{
      font-weight: 800;
      margin-bottom: 5px;
      color: var(--ink);
    }}

    .meta-row {{
      margin-top: 2px;
      color: #475569;
      font-size: 11.2px;
    }}

    .status-unfit {{ background: var(--danger-soft); border-color: var(--danger-line); }}
    .status-remark {{ background: var(--warn-soft); border-color: var(--warn-line); }}
    .status-good {{ background: var(--good-soft); border-color: var(--good-line); }}
    .status-unknown {{ background: var(--unknown-soft); border-color: var(--unknown-line); }}
    .finding.status-unfit {{ border-left-color: #e11d48; }}
    .finding.status-remark {{ border-left-color: #f97316; }}
    .finding.status-good {{ border-left-color: #16a34a; }}
    .finding.status-unknown {{ border-left-color: #94a3b8; }}
    .status-unfit .dot {{ background: #e11d48; }}
    .status-remark .dot {{ background: #f97316; }}
    .status-good .dot {{ background: #16a34a; }}
    .status-unknown .dot {{ background: #94a3b8; }}

    ul {{
      padding-left: 0;
      margin: 7px 0 0;
      list-style: none;
    }}

    li {{
      position: relative;
      margin: 5px 0;
      padding-left: 15px;
      color: var(--text);
    }}

    li:before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0.66em;
      width: 5px;
      height: 5px;
      border-radius: 99px;
      background: var(--brand);
    }}

    .parameter-section {{
      margin-top: 6mm;
      break-inside: auto;
      page-break-inside: auto;
    }}

    .parameter-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
      margin-bottom: 7px;
    }}

    .parameter-title h3 {{ margin: 0; }}
    .parameter-note {{ color: var(--muted); font-size: 9.8px; }}

    .table-wrap {{
      overflow: visible;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      margin-top: 0;
      background: #ffffff;
      break-inside: auto;
      page-break-inside: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10.35px;
      background: #ffffff;
      break-inside: auto;
      page-break-inside: auto;
    }}

    thead {{ display: table-header-group; }}
    tbody {{ display: table-row-group; }}

    th, td {{
      border-bottom: 1px solid var(--line-soft);
      padding: 6px 7px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}

    th {{
      background: #f1f5f9;
      color: #475569;
      font-size: 8.8px;
      text-transform: uppercase;
      letter-spacing: 0.045em;
      font-weight: 800;
    }}

    tr {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    tr:last-child td {{ border-bottom: 0; }}
    td:first-child {{ font-weight: 800; color: var(--ink); }}

    .empty {{ color: var(--muted); }}

    .disclaimer {{
      font-size: 9.2px;
      color: #64748b;
      margin-top: 7mm;
      padding-top: 4mm;
      border-top: 1px solid var(--line-soft);
    }}

    @media print {{
      html, body {{ background: #ffffff; font-size: 11.8px; }}
      .page {{ width: 100%; max-width: none; margin: 0; padding: 0; }}
      .card, .finding, .hero-title, .report-meta, .status-card {{ box-shadow: none; }}
      section, .card, .finding {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      .parameter-section, .table-wrap, table {{
        break-inside: auto;
        page-break-inside: auto;
      }}
      tr {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      h2, h3, .parameter-title {{ break-after: avoid; page-break-after: avoid; }}
      .grid {{ grid-template-columns: 1fr 1fr; gap: 4.5mm; }}
    }}
  </style>
</head>
<body>
  <main class=\"page\">
    <header class=\"topbar\">
      <div>
        <div class=\"eyebrow\">Svenska Vatteninstitutet · Analysrapport</div>
        <h1>Vattenrapport</h1>
      </div>
      <aside class=\"report-meta\">
        <div class=\"meta-line\"><span>Fastighet</span><span>{esc(meta.get('fastighetsbeteckning'))}</span></div>
        <div class=\"meta-line\"><span>Provnummer</span><span>{esc(meta.get('provnummer'))}</span></div>
        <div class=\"meta-line\"><span>Provdatum</span><span>{esc(meta.get('provtagningsdatum'))}</span></div>
      </aside>
    </header>

    <section class=\"hero\">
      <div class=\"hero-title\">
        <div class=\"kicker\">Samlad bedömning</div>
        <h2>{esc(status_label(data.get('overall_status')))}</h2>
        {nl2html(sections.get('summary'))}
      </div>
      <div class=\"status-panel\">
        <div class=\"status-card {status_class(data.get('overall_status'))}\">
          <div class=\"status-label\">Helhetsstatus</div>
          <div class=\"status-value\"><span class=\"dot\"></span>{esc(status_label(data.get('overall_status')))}</div>
        </div>
        <div class=\"status-card {status_class(data.get('mikrobiologisk_status'))}\">
          <div class=\"status-label\">Mikrobiologisk status</div>
          <div class=\"status-value\"><span class=\"dot\"></span>{esc(status_label(data.get('mikrobiologisk_status')))}</div>
        </div>
        <div class=\"status-card {status_class(data.get('kemisk_status'))}\">
          <div class=\"status-label\">Kemisk status</div>
          <div class=\"status-value\"><span class=\"dot\"></span>{esc(status_label(data.get('kemisk_status')))}</div>
        </div>
      </div>
    </section>

    <section class=\"card\">
      <div class=\"card-header\">
        <div>
          <div class=\"kicker\">Prioritering</div>
          <h3>Det viktigaste att börja med</h3>
        </div>
      </div>
      {build_findings_html(findings)}
    </section>

    <section class=\"grid\">
      <div class=\"card\">
        <div class=\"kicker\">Tolkning</div>
        <h3>Vad det innebär</h3>
        {nl2html(sections.get('what_it_means'))}
      </div>
      <div class=\"card\">
        <div class=\"kicker\">Åtgärder</div>
        <h3>Rekommenderade nästa steg</h3>
        {nl2html(sections.get('actions'))}
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"card\">
        <div class=\"kicker\">Råd</div>
        <h3>Praktiska råd</h3>
        {nl2html(sections.get('practical_advice'))}
      </div>
      <div class=\"card\">
        <div class=\"kicker\">Bedömning</div>
        <h3>Hälsa</h3>
        {nl2html(sections.get('health_assessment'))}
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"card\">
        <div class=\"kicker\">Bakgrund</div>
        <h3>Möjliga orsaker</h3>
        {nl2html(sections.get('causes'))}
      </div>
      <div class=\"card\">
        <div class=\"kicker\">Installation</div>
        <h3>Tekniska konsekvenser / åtgärder</h3>
        {nl2html(sections.get('installations'))}
      </div>
    </section>

    <section class=\"grid\">
      <div class=\"card\">
        <div class=\"kicker\">Godkända delar</div>
        <h3>Det som ser bra ut</h3>
        <ul>{list_items(positives)}</ul>
      </div>
      <div class=\"card\">
        <div class=\"kicker\">Övrigt</div>
        <h3>Analyser utan separat bedömning</h3>
        <ul>{list_items(not_assessed)}</ul>
      </div>
    </section>

    <section class="parameter-section">
      <div class="parameter-title">
        <h3>Alla parametrar</h3>
        <span class="parameter-note">Fullständig parameteröversikt</span>
      </div>
      <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Parameter</th><th>Värde</th><th>Kategori</th><th>Riktvärden</th><th>Status</th></tr>
      </thead>
      <tbody>
        {build_parameter_rows(parameters)}
      </tbody>
    </table>
  </div>
</section>

    <section class=\"card\">
      <div class=\"kicker\">Slutsats</div>
      <h3>Slutsats</h3>
      {nl2html(sections.get('conclusion'))}
    </section>

    <p class=\"disclaimer\">
      Rapporten är automatiskt genererad och utgör endast vägledande information.
      Svenska Vatteninstitutet ansvarar inte för beslut, åtgärder eller konsekvenser
      som baseras på rapportens innehåll.
    </p>
  </main>
</body>
</html>
"""

    output_file.write_text(html, encoding="utf-8")
    pdf_path = output_file.with_suffix(".pdf")
    generate_pdf(output_file, pdf_path)

    print(f"HTML skapad: {output_file}")
    print(f"PDF skapad: {pdf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    args = parser.parse_args()
    generate_html(args.input_path, args.output_path)
