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
    @page {{ size: A4; margin: 12mm; }}

    :root {{
      --bg: #f6f8fb;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --brand: #0f766e;
      --brand-soft: #ccfbf1;
      --shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
      --radius-lg: 22px;
      --radius-md: 16px;
      --radius-sm: 999px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 34%),
        linear-gradient(180deg, #ffffff 0%, var(--bg) 55%, #ffffff 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    .page {{ max-width: 1080px; margin: 0 auto; padding: 30px 18px 38px; }}

    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      margin-bottom: 18px;
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 11px;
      border: 1px solid rgba(15, 118, 110, 0.18);
      border-radius: var(--radius-sm);
      background: rgba(204, 251, 241, 0.55);
      color: #115e59;
      font-size: 11px;
      font-weight: 750;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1, h2, h3 {{ margin: 0; letter-spacing: -0.025em; }}
    h1 {{ margin-top: 12px; font-size: 38px; line-height: 1.04; }}
    h2 {{ font-size: 20px; }}
    h3 {{ font-size: 15px; }}

    p {{ margin: 0.55em 0 0; color: #334155; }}
    strong {{ color: var(--ink); font-weight: 760; }}
    section {{ margin-top: 16px; }}

    .report-meta {{
      min-width: 230px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.82);
      padding: 13px 14px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
      font-size: 12px;
      color: var(--muted);
    }}

    .meta-line {{ display: flex; justify-content: space-between; gap: 18px; padding: 4px 0; }}
    .meta-line span:first-child {{ color: var(--muted); }}
    .meta-line span:last-child {{ color: var(--ink); font-weight: 700; text-align: right; }}

    .hero {{
      display: grid;
      grid-template-columns: 1.12fr 0.88fr;
      gap: 18px;
      align-items: stretch;
      padding: 22px;
      border: 1px solid rgba(226, 232, 240, 0.9);
      border-radius: 28px;
      background: rgba(255, 255, 255, 0.9);
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
    }}

    .hero:before {{
      content: \"\";
      position: absolute;
      width: 220px;
      height: 220px;
      right: -80px;
      top: -90px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.10);
    }}

    .hero-title {{ position: relative; z-index: 1; }}
    .hero-title p {{ max-width: 650px; font-size: 15px; color: #475569; }}

    .status-panel {{
      position: relative;
      z-index: 1;
      display: grid;
      gap: 10px;
      align-content: start;
    }}

    .status-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 13px 14px;
      background: var(--surface);
    }}

    .status-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 750; }}
    .status-value {{ display: flex; align-items: center; gap: 8px; margin-top: 4px; font-weight: 820; font-size: 15px; }}
    .dot {{ width: 9px; height: 9px; border-radius: 99px; display: inline-block; background: #94a3b8; }}

    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .wide {{ grid-column: 1 / -1; }}

    .card {{
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      padding: 18px 18px 17px;
      background: rgba(255, 255, 255, 0.94);
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }}

    .kicker {{ color: var(--muted); font-size: 11px; font-weight: 760; letter-spacing: 0.07em; text-transform: uppercase; }}

    .finding {{
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 14px 15px;
      margin-top: 10px;
      background: var(--surface-soft);
    }}

    .finding-head {{ display: flex; justify-content: space-between; gap: 12px; font-weight: 820; margin-bottom: 8px; }}
    .finding-head span:last-child {{ color: var(--muted); font-weight: 700; white-space: nowrap; }}
    .meta-row {{ margin-top: 3px; color: #475569; font-size: 13px; }}

    .status-unfit {{ background: #fff1f2; border-color: #fecdd3; }}
    .status-remark {{ background: #fff7ed; border-color: #fed7aa; }}
    .status-good {{ background: #f0fdf4; border-color: #bbf7d0; }}
    .status-unknown {{ background: #f8fafc; border-color: #cbd5e1; }}
    .status-unfit .dot {{ background: #e11d48; }}
    .status-remark .dot {{ background: #f97316; }}
    .status-good .dot {{ background: #16a34a; }}
    .status-unknown .dot {{ background: #94a3b8; }}

    ul {{ padding-left: 0; margin: 10px 0 0; list-style: none; }}
    li {{
      position: relative;
      margin: 8px 0;
      padding-left: 20px;
      color: #334155;
    }}
    li:before {{
      content: \"\";
      position: absolute;
      left: 0;
      top: 0.72em;
      width: 7px;
      height: 7px;
      border-radius: 99px;
      background: var(--brand);
    }}

    .table-wrap {{ overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius-md); margin-top: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 11px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; color: #475569; font-size: 11px; text-transform: uppercase; letter-spacing: 0.055em; }}
    tr:last-child td {{ border-bottom: 0; }}
    td:first-child {{ font-weight: 740; color: var(--ink); }}

    .empty {{ color: var(--muted); }}
    .disclaimer {{ font-size: 10.5px; color: #64748b; margin-top: 22px; padding: 0 4px; }}

    @media print {{
      body {{ background: #fff; font-size: 12px; }}
      .page {{ padding: 0; max-width: none; }}
      .hero, .card, .report-meta {{ box-shadow: none; }}
      .hero {{ border-radius: 22px; }}
      section, .card, .finding, table, tr, td, th {{ break-inside: avoid; page-break-inside: avoid; }}
      h2, h3 {{ break-after: avoid; page-break-after: avoid; }}
      .grid {{ grid-template-columns: 1fr 1fr; gap: 12px; }}
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
