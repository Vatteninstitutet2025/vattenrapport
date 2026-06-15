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
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def generate_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = find_browser()
    if not browser:
        raise RuntimeError("Hittar inte Chrome/Edge. Installera Chrome eller Edge, eller lägg webbläsaren i PATH.")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
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
    )


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
      margin: 10mm 11mm 11mm 11mm;
    }}

    :root {{
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #d7dee8;
      --line-soft: #e8edf3;
      --brand: #0f766e;
      --brand-dark: #115e59;
      --brand-soft: #ecfdf5;
      --warn-soft: #fff7ed;
      --warn-line: #fed7aa;
      --danger-soft: #fff1f2;
      --danger-line: #fecdd3;
      --good-soft: #f0fdf4;
      --good-line: #bbf7d0;
      --unknown-soft: #f8fafc;
      --unknown-line: #cbd5e1;
      --radius-lg: 10px;
      --radius-md: 8px;
      --radius-sm: 999px;
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12.5px;
      line-height: 1.48;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    body {{ width: 100%; }}

    .page {{
      width: 100%;
      max-width: none;
      margin: 0;
      padding: 0;
    }}

    .topbar {{
      display: grid;
      grid-template-columns: 1fr 74mm;
      gap: 10mm;
      align-items: start;
      padding-bottom: 7mm;
      margin-bottom: 6mm;
      border-bottom: 2px solid var(--brand);
    }}

    .eyebrow {{
      display: inline-block;
      padding: 3px 8px;
      border: 1px solid rgba(15, 118, 110, 0.25);
      border-radius: var(--radius-sm);
      background: #f0fdfa;
      color: var(--brand-dark);
      font-size: 9.5px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1, h2, h3 {{
      margin: 0;
      color: var(--ink);
      line-height: 1.16;
    }}

    h1 {{
      margin-top: 8px;
      font-size: 29px;
      letter-spacing: -0.02em;
    }}

    h2 {{ font-size: 18px; }}
    h3 {{ font-size: 14px; }}

    p {{
      margin: 0.45em 0 0;
      color: #334155;
    }}

    strong {{ color: var(--ink); font-weight: 700; }}
    section {{ margin-top: 6mm; }}

    .report-meta {{
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: #ffffff;
      padding: 9px 11px;
      font-size: 11px;
      color: var(--muted);
    }}

    .meta-line {{
      display: grid;
      grid-template-columns: 1fr 1.35fr;
      gap: 8px;
      padding: 3px 0;
      border-bottom: 1px solid var(--line-soft);
    }}

    .meta-line:last-child {{ border-bottom: 0; }}
    .meta-line span:first-child {{ color: var(--muted); }}
    .meta-line span:last-child {{ color: var(--ink); font-weight: 700; text-align: right; overflow-wrap: anywhere; }}

    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 64mm;
      gap: 6mm;
      align-items: start;
      padding: 0;
      border: 0;
      border-radius: 0;
      background: #ffffff;
      box-shadow: none;
      overflow: visible;
      position: relative;
    }}

    .hero-title {{
      padding: 6mm;
      border: 1px solid var(--line);
      border-left: 4px solid var(--brand);
      border-radius: var(--radius-lg);
      background: #ffffff;
    }}

    .hero-title p {{
      max-width: none;
      font-size: 12.5px;
      color: #334155;
    }}

    .status-panel {{
      display: grid;
      gap: 3mm;
      align-content: start;
      position: relative;
      z-index: 1;
    }}

    .status-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 10px 11px;
      background: #ffffff;
    }}

    .status-label {{
      font-size: 9.5px;
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
      font-weight: 700;
      font-size: 12.5px;
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
      gap: 5mm;
    }}

    .wide {{ grid-column: 1 / -1; }}

    .card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      padding: 5mm;
      background: #ffffff;
      box-shadow: none;
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
      font-size: 9.5px;
      font-weight: 700;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      margin-bottom: 3px;
    }}

    .finding {{
      border: 1px solid var(--line);
      border-left-width: 4px;
      border-radius: var(--radius-md);
      padding: 11px 12px;
      margin-top: 8px;
      background: #ffffff;
    }}

    .finding-head {{
      font-weight: 700;
      margin-bottom: 6px;
      color: var(--ink);
    }}

    .meta-row {{
      margin-top: 2px;
      color: #475569;
      font-size: 11.5px;
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
      margin: 8px 0 0;
      list-style: none;
    }}

    li {{
      position: relative;
      margin: 6px 0;
      padding-left: 16px;
      color: #334155;
    }}

    li:before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0.68em;
      width: 5px;
      height: 5px;
      border-radius: 99px;
      background: var(--brand);
    }}

    .table-wrap {{
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      margin-top: 9px;
      background: #ffffff;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10.8px;
      background: #ffffff;
    }}

    th, td {{
      border-bottom: 1px solid var(--line-soft);
      padding: 7px 8px;
      text-align: left;
      vertical-align: top;
    }}

    th {{
      background: #f8fafc;
      color: #475569;
      font-size: 9.5px;
      text-transform: uppercase;
      letter-spacing: 0.045em;
      font-weight: 700;
    }}

    tr:last-child td {{ border-bottom: 0; }}
    td:first-child {{ font-weight: 700; color: var(--ink); }}
    td {{ overflow-wrap: anywhere; }}

    .empty {{ color: var(--muted); }}

    .disclaimer {{
      font-size: 9.5px;
      color: #64748b;
      margin-top: 7mm;
      padding-top: 4mm;
      border-top: 1px solid var(--line-soft);
    }}

    @media print {{
      html, body {{ background: #ffffff; font-size: 12px; }}
      .page {{ width: 100%; max-width: none; margin: 0; padding: 0; }}
      .hero, .card, .report-meta, .status-card {{ box-shadow: none; }}
      section, .card, .finding, table, tr, td, th {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      h2, h3 {{ break-after: avoid; page-break-after: avoid; }}
      .grid {{ grid-template-columns: 1fr 1fr; gap: 5mm; }}
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

    <section class=\"card\">
      <h3>Alla parametrar</h3>
      <div class=\"table-wrap\">
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
