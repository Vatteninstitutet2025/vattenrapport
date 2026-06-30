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
        "ej bedömd": "Informationsparameter",
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



def _norm_name(value: object) -> str:
    import unicodedata
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


PARAMETER_GROUPS = [
    ("Mikrobiologisk kvalitet", "Bakterier och mikroorganismer som visar om vattnet kan vara påverkat av ytvatten, avlopp eller annan mikrobiologisk förorening."),
    ("Utseende, lukt och allmän vattenkvalitet", "Parametrar som påverkar lukt, färg, grumlighet och allmän upplevelse av vattnet."),
    ("pH, salter och korrosion", "Vattnets surhet, buffringsförmåga och salthalt. Viktigt för smak, korrosion och teknisk påverkan."),
    ("Näringsämnen och påverkan från omgivningen", "Kan indikera påverkan från avlopp, gödsel, jordbruk, ytvatten eller biologisk aktivitet i brunnen."),
    ("Hårdhet och mineraler", "Mineraler som påverkar kalkavlagringar, smak, dosering av tvättmedel och teknisk funktion."),
    ("Tekniska metaller", "Metaller som ofta påverkar smak, missfärgning, beläggningar, tvätt, porslin och installationer."),
    ("Hälsorelaterade metaller och spårämnen", "Metaller och spårämnen som främst bedöms utifrån långsiktig hälsopåverkan."),
    ("Radon och radioaktivitet", "Radioaktiva ämnen som kan förekomma naturligt i berggrund och grundvatten."),
    ("Prov- och mätinformation", "Uppgifter som beskriver provtagning eller mätförhållanden, men som normalt inte är en egen kvalitetsanmärkning."),
    ("Övriga parametrar", "Parametrar som inte automatiskt kunde placeras i någon av huvudgrupperna."),
]


def parameter_group_name(parameter: dict) -> str:
    name = _norm_name(" ".join(str(parameter.get(key) or "") for key in ("parameter_display", "parameter", "name")))
    if "vattentemperatur" in name or "temperatur vid ph" in name or "provtagning" in name:
        return "Prov- och mätinformation"
    if any(term in name for term in ["odlingsbara", "escherichia", "e. coli", "coli", "koliform"]):
        return "Mikrobiologisk kvalitet"
    if any(term in name for term in ["lukt", "turbiditet", "farg", "cod-mn", "cod mn", "permanganat"]):
        return "Utseende, lukt och allmän vattenkvalitet"
    if any(term in name for term in ["ph", "alkalinitet", "konduktivitet", "klorid", "sulfat", "fluorid"]):
        return "pH, salter och korrosion"
    if any(term in name for term in ["ammonium", "ammoniumkvave", "fosfat", "fosfatfosfor", "nitrat", "nitratkvave", "nitrit", "nitrit-nitrogen", "no3", "no2"]):
        return "Näringsämnen och påverkan från omgivningen"
    if any(term in name for term in ["hardhet", "kalcium", "magnesium", "natrium", "kalium"]):
        return "Hårdhet och mineraler"
    if any(term in name for term in ["jarn", "mangan", "aluminium", "koppar"]):
        return "Tekniska metaller"
    if any(term in name for term in ["antimon", "arsenik", "bly", "kadmium", "krom", "nickel", "selen", "uran"]):
        return "Hälsorelaterade metaller och spårämnen"
    if "radon" in name or "radio" in name:
        return "Radon och radioaktivitet"
    return "Övriga parametrar"


def build_parameter_row(parameter: dict) -> str:
    value = f"{(parameter.get('value_text') or '').strip()} {(parameter.get('unit') or '').strip()}".strip()
    return (
        f"<tr class=\"{status_class(parameter.get('status'))}\">"
        f"<td>{esc(parameter.get('parameter_display'))}</td>"
        f"<td>{esc(value)}</td>"
        f"<td>{format_reference(parameter.get('reference_values'), parameter.get('reference_text'))}</td>"
        f"<td>{esc(status_label(parameter.get('status', '')))}</td>"
        f"</tr>"
    )


def build_grouped_parameters_html(parameters: list[dict]) -> str:
    if not parameters:
        return '<p class="empty">Inga parametrar att visa.</p>'
    order = {"otjänligt": 0, "tjänligt med anmärkning": 1, "tjänligt": 2, "ej bedömd": 3}
    groups: dict[str, list[dict]] = {name: [] for name, _ in PARAMETER_GROUPS}
    for parameter in parameters:
        groups.setdefault(parameter_group_name(parameter), []).append(parameter)
    group_descriptions = dict(PARAMETER_GROUPS)
    blocks = []
    for group_name, description in PARAMETER_GROUPS:
        items = groups.get(group_name, [])
        if not items:
            continue
        sorted_items = sorted(
            items,
            key=lambda p: (
                order.get((p.get("status") or "").strip().lower(), 9),
                p.get("parameter_display", p.get("parameter", "")),
            ),
        )
        rows = "".join(build_parameter_row(item) for item in sorted_items)
        blocks.append(f"""
            <article class="parameter-group">
              <div class="parameter-group-head">
                <div>
                  <h4>{esc(group_name)}</h4>
                  <p>{esc(group_descriptions.get(group_name, description))}</p>
                </div>
                <span>{len(sorted_items)} st</span>
              </div>
              <div class="table-wrap group-table-wrap">
                <table>
                  <thead>
                    <tr><th>Parameter</th><th>Värde</th><th>Riktvärden</th><th>Status</th></tr>
                  </thead>
                  <tbody>{rows}</tbody>
                </table>
              </div>
            </article>
            """)
    return "".join(blocks)



def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    import re

    text = str(value).strip().replace("\xa0", " ").replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _find_hardness_parameter(parameters: list[dict]) -> dict | None:
    for p in parameters:
        name = " ".join(
            str(p.get(key) or "")
            for key in ("parameter_display", "parameter", "name")
        ).lower()
        if "hårdhet" in name or "hardness" in name:
            return p
    return None


def _hardness_to_dh(value: float, unit: str) -> float:
    unit_l = (unit or "").lower()
    if "mmol" in unit_l:
        return value * 5.6
    return value


def _hardness_label(value_dh: float) -> str:
    if value_dh < 2:
        return "Mycket mjukt"
    if value_dh < 5:
        return "Mjukt"
    if value_dh < 10:
        return "Medelhårt"
    if value_dh < 20:
        return "Hårt"
    return "Mycket hårt"

def _hardness_marker_position(value_dh: float) -> float:
    if value_dh <= 0:
        return 0.0
    if value_dh < 2:
        return (value_dh / 2) * 20
    if value_dh < 5:
        return 20 + ((value_dh - 2) / 3) * 20
    if value_dh < 10:
        return 40 + ((value_dh - 5) / 5) * 20
    if value_dh < 20:
        return 60 + ((value_dh - 10) / 10) * 20
    if value_dh < 25:
        return 80 + ((value_dh - 20) / 5) * 20

    return 100.0

def build_hardness_scale_html(parameters: list[dict]) -> str:
    p = _find_hardness_parameter(parameters)
    if not p:
        return ""

    raw_value = p.get("value_text") or p.get("value") or p.get("result")
    unit = (p.get("unit") or "°dH").strip() or "°dH"
    value = _parse_number(raw_value)
    if value is None:
        return ""

    value_dh = _hardness_to_dh(value, unit)
    label = _hardness_label(value_dh)
    marker_left = _hardness_marker_position(value_dh)
    display_value = f"{value:g}".replace(".", ",")

    return f'''
    <section class="hardness-card">
      <div class="hardness-head">
        <div>
          <div class="kicker">Vattnets hårdhet</div>
          <h3>{esc(label)}</h3>
        </div>
        <div class="hardness-value">
          <span>{esc(display_value)}</span>
          <small>{esc(unit)}</small>
        </div>
      </div>

      <div class="hardness-scale" aria-label="Skala för vattnets hårdhet">
        <div class="hardness-marker" style="left: {marker_left:.1f}%"></div>
      </div>

      <div class="hardness-labels">
        <span>Mycket mjukt<br><strong>0–2</strong></span>
        <span>Mjukt<br><strong>2–5</strong></span>
        <span>Medelhårt<br><strong>5–10</strong></span>
        <span>Hårt<br><strong>10–20</strong></span>
        <span>Mycket hårt<br><strong>&gt;20</strong></span>
      </div>

      <p class="hardness-note">
        Hårdheten påverkar främst kalkavlagringar, dosering av tvätt- och diskmedel samt teknisk funktion i installationer.
      </p>
    </section>
    '''



def _find_ph_parameter(parameters: list[dict]) -> dict | None:
    for p in parameters:
        name = " ".join(
            str(p.get(key) or "")
            for key in ("parameter_display", "parameter", "name")
        ).lower()
        # Undvik temperaturen vid pH-mätning. Vi vill ha själva parametern pH.
        if "temperatur" in name or "temperature" in name:
            continue
        padded = f" {name} "
        if name.strip() == "ph" or " ph " in padded or name.startswith("ph ") or "ph-värde" in name:
            return p
    return None


def _ph_label(value: float) -> str:
    if value < 6.5:
        return "Surt"
    if value <= 9.0:
        return "Nära neutralt"
    return "Basiskt"


def build_ph_scale_html(parameters: list[dict]) -> str:
    p = _find_ph_parameter(parameters)
    if not p:
        return ""

    raw_value = p.get("value_text") or p.get("value") or p.get("result")
    value = _parse_number(raw_value)
    if value is None:
        return ""

    label = _ph_label(value)
    marker_left = max(0, min(100, (value / 14) * 100))
    display_value = f"{value:g}".replace(".", ",")

    return f'''
    <section class="ph-card">
      <div class="hardness-head">
        <div>
          <div class="kicker">pH-värde</div>
          <h3>{esc(label)}</h3>
        </div>
        <div class="hardness-value">
          <span>{esc(display_value)}</span>
          <small>pH</small>
        </div>
      </div>

      <div class="ph-scale" aria-label="Skala för pH-värde">
        <div class="hardness-marker" style="left: {marker_left:.1f}%"></div>
      </div>

      <div class="ph-labels">
        <span>Surt<br><strong>0</strong></span>
        <span>Svagt surt<br><strong>6,5</strong></span>
        <span>Neutralt<br><strong>7</strong></span>
        <span>Basiskt<br><strong>9</strong></span>
        <span>Starkt basiskt<br><strong>14</strong></span>
      </div>

      <p class="hardness-note">
        pH visar om vattnet är surt, nära neutralt eller basiskt. Lågt pH kan öka risken för korrosion i ledningar och installationer.
      </p>
    </section>
    '''



def build_summary_stats_html(parameters: list[dict]) -> str:
    assessed = [
        p for p in parameters
        if (p.get("status") or "").strip().lower() != "ej bedömd"
    ]

    total = len(assessed)
    good = len([p for p in assessed if (p.get("status") or "").strip().lower() == "tjänligt"])
    remark = len([p for p in assessed if (p.get("status") or "").strip().lower() == "tjänligt med anmärkning"])
    unfit = len([p for p in assessed if (p.get("status") or "").strip().lower() == "otjänligt"])
    deviating = remark + unfit

    return f"""
    <section class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{total}</div>
        <div class="stat-label">Bedömda parametrar</div>
      </div>

      <div class="stat-card good">
        <div class="stat-number">{good}</div>
        <div class="stat-label">Tjänliga</div>
      </div>

      <div class="stat-card remark">
        <div class="stat-number">{remark}</div>
        <div class="stat-label">Med anmärkning</div>
      </div>

      <div class="stat-card unfit">
        <div class="stat-number">{unfit}</div>
        <div class="stat-label">Otjänliga</div>
      </div>

    </section>
    """


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
      --line: #d6dee8;
      --line-soft: #edf2f7;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --brand: #23395d;
      --brand-dark: #23395d;
      --brand-soft: #eef7f6;
      --blue-soft: #f3f7fb;
      --warn-soft: #ffffff;
      --warn-line: #d6dee8;
      --danger-soft: #ffffff;
      --danger-line: #d6dee8;
      --good-soft: #ffffff;
      --good-line: #d6dee8;
      --unknown-soft: #ffffff;
      --unknown-line: #d6dee8;
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
      background: #1e3a5f;
      color: #ffffff;
      font-size: 9.2px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 12px;
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
      width: 3px;
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
      color: #4f6487;
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


    .hardness-card {{
      margin-top: 5.3mm;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      padding: 4.8mm;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .hardness-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 12px;
    }}

    .hardness-value {{
      min-width: 26mm;
      padding: 8px 10px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid var(--line);
      text-align: right;
    }}

    .hardness-value span {{
      display: block;
      font-size: 20px;
      line-height: 1;
      font-weight: 800;
      color: var(--ink);
      letter-spacing: -0.03em;
    }}

    .hardness-value small {{
      display: block;
      margin-top: 3px;
      font-size: 9px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .hardness-scale {{
      position: relative;
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(90deg, #dbeafe 0%, #ccfbf1 20%, #fef3c7 40%, #fed7aa 70%, #fecaca 100%);
      border: 1px solid rgba(15, 23, 42, 0.10);
      overflow: visible;
    }}

    .hardness-marker {{
      position: absolute;
      top: 50%;
      width: 14px;
      height: 14px;
      margin-left: -7px;
      margin-top: -7px;
      border-radius: 999px;
      background: var(--ink);
      border: 3px solid #ffffff;
      box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.18);
    }}

    .hardness-labels {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 4px;
      margin-top: 7px;
      color: var(--muted);
      font-size: 8.7px;
      line-height: 1.25;
    }}

    .hardness-labels span {{ text-align: center; }}
    .hardness-labels strong {{ font-size: 8.4px; color: var(--ink); }}

    .hardness-note {{
      margin-top: 9px;
      color: var(--muted);
      font-size: 10.3px;
    }}



    .ph-card {{
      margin-top: 3mm;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      padding: 4.8mm;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .ph-scale {{
      position: relative;
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(90deg, #fecaca 0%, #fef3c7 46%, #dcfce7 50%, #dbeafe 64%, #ddd6fe 100%);
      border: 1px solid rgba(15, 23, 42, 0.10);
      overflow: visible;
    }}

    .ph-labels {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 4px;
      margin-top: 7px;
      color: var(--muted);
      font-size: 8.7px;
      line-height: 1.25;
    }}

    .ph-labels span {{ text-align: center; }}
    .ph-labels strong {{ font-size: 8.4px; color: var(--ink); }}

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
    .finding.status-unfit {{ border-left-color: #e11d48; background: #fbeaea; }}
    .finding.status-remark {{ border-left-color: #d4be95; background: #fcf5e8; }}
    .finding.status-good {{ border-left-color: #16a34a; background: #edf8f0; }}
    .finding.status-unknown {{ border-left-color: #94a3b8; background: #eef2f6; }}
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

    .parameter-groups {{
      display: grid;
      gap: 4.5mm;
    }}

    .parameter-group {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #ffffff;
      overflow: hidden;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .parameter-group-head {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
      padding: 11px 12px 9px;
      background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
      border-bottom: 1px solid var(--line-soft);
    }}

    .parameter-group-head h4 {{
      margin: 0;
      font-size: 12.6px;
      line-height: 1.15;
      color: var(--ink);
    }}

    .parameter-group-head p {{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 9.6px;
      line-height: 1.35;
    }}

    .parameter-group-head span {{
      display: inline-block;
      padding: 3px 7px;
      border-radius: 999px;
      background: #eef2ff;
      color: #475569;
      font-size: 8.8px;
      font-weight: 800;
      white-space: nowrap;
    }}

    .group-table-wrap {{
      border: 0;
      border-radius: 0;
    }}

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
      font-size: 12.5px;
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
      font-size: 12.5px;
      text-transform: uppercase;
      letter-spacing: 0.045em;
      font-weight: 800;
    }}

    tr {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    tr:last-child td {{ border-bottom: 0; }}
    td:first-child {{ font-weight: 600; color: var(--ink); }}

    .empty {{ color: var(--muted); }}

    .disclaimer {{
      font-size: 9.2px;
      color: #64748b;
      margin-top: 7mm;
      padding-top: 4mm;
      border-top: 1px solid var(--line-soft);
    }}
        .legend-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}

    .legend-table th,
    .legend-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line-soft);
      text-align: left;
      vertical-align: top;
    }}

    .legend-table th {{
      background: #f1f5f9;
      color: #475569;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-weight: 800;
      white-space: nowrap;
    }}

    .legend-table th:first-child,
    .legend-table td:first-child {{
      width: 170px;
      white-space: nowrap;
    }}

    .legend-explainer {{
      margin-top: 12px;
      padding: 10px 12px;
      background: #f8fafc;
      border: 1px solid var(--line-soft);
      border-radius: 10px;
    }}

    .legend-explainer p {{
      margin: 4px 0;
    }}




    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 4mm;
      width: 100%;
      margin-top: 5.3mm;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .stat-card {{
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 10px 8px;
      text-align: center;
      min-height: 21mm;
      box-sizing: border-box;
    }}

    .stat-number {{
      font-size: 25px;
      font-weight: 800;
      line-height: 1;
      color: var(--ink);
      letter-spacing: -0.03em;
    }}

    .stat-label {{
      margin-top: 5px;
      font-size: 9.3px;
      line-height: 1.25;
      color: var(--muted);
      font-weight: 700;
    }}

    .stat-card.good {{
      background: var(--good-soft);
      border-color: var(--good-line);
    }}

    .stat-card.remark {{
      background: var(--warn-soft);
      border-color: var(--warn-line);
    }}

    .stat-card.unfit {{
      background: var(--danger-soft);
      border-color: var(--danger-line);
    }}

    .stat-card.deviating {{
      background: var(--blue-soft);
      border-color: #bfdbfe;
    }}

    .parameter-group tr.status-unfit {{
    background: #fbeaea;
    }}

    .parameter-group tr.status-remark {{
    background: #fcf5e8;
    }}

    .parameter-group tr.status-good {{
    background: #edf8f0;
    }}

    .parameter-group tr.status-unknown {{
    background: #eef2f6;
    }}


    @media print {{
      html, body {{ background: #ffffff; font-size: 11.8px; }}
      .page {{ width: 100%; max-width: none; margin: 0; padding: 0; }}
      .card, .finding, .hero-title, .report-meta, .status-card {{ box-shadow: none; }}
      section, .card, .finding {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      .parameter-section, .parameter-groups {{
        break-inside: auto;
        page-break-inside: auto;
      }}
      .parameter-group {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      .table-wrap, table {{
        break-inside: auto;
        page-break-inside: auto;
      }}
      tr {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      h2, h3, h4, .parameter-title, .parameter-group-head {{ break-after: avoid; page-break-after: avoid; }}
      .grid {{ grid-template-columns: 1fr 1fr; gap: 4.5mm; }}
    }}
  </style>
</head>
<body>
  <main class=\"page\">
    <header class=\"topbar\">
      <div>
        <div class=\"eyebrow\">Svenska Vatteninstitutet · Analysrapport</div>
        <h1>Vattenrapport för din fastighet</h1>
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

    {build_summary_stats_html(parameters)}

    {build_hardness_scale_html(parameters)}
    {build_ph_scale_html(parameters)}

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
        <span class="parameter-note">Grupperad parameteröversikt</span>
      </div>
      <div class="parameter-groups">
        {build_grouped_parameters_html(parameters)}
      </div>
</section>

    <section class=\"card\">
  <div class=\"kicker\">Slutsats</div>
  <h3>Slutsats</h3>
  {nl2html(sections.get('conclusion'))}
</section>

<section class="card">
  <div class="kicker">Förklaring</div>
  <h3>Så tolkar du bedömningarna</h3>

  <table class="legend-table">
    <thead>
      <tr>
        <th>Bedömning</th>
        <th>Förklaring</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Tjänligt</strong></td>
        <td>
          Vattnet uppfyller aktuella riktvärden och bedöms normalt inte kräva
          någon särskild åtgärd.
        </td>
      </tr>

      <tr>
        <td><strong>Tjänligt med anmärkning</strong></td>
        <td>
          En eller flera parametrar avviker från rekommenderade nivåer.
          Vattnet kan ofta användas, men uppföljning eller åtgärder kan vara
          motiverade beroende på avvikelsens omfattning.
        </td>
      </tr>

      <tr>
        <td><strong>Otjänligt</strong></td>
        <td>
          Minst en parameter avviker på en nivå som kan innebära risk för hälsa,
          installationer eller användning. Vidare bedömning och åtgärder
          rekommenderas.
        </td>
      </tr>
    </tbody>
  </table>

  <div class="legend-explainer">
    <p><strong>H</strong> = Hälsomässig bedömning</p>
    <p><strong>T</strong> = Teknisk bedömning</p>
    <p><strong>E</strong> = Estetisk bedömning</p>
  </div>

  <p>
    Hälsomässiga anmärkningar avser risker för människors hälsa.
    Tekniska anmärkningar avser påverkan på installationer, ledningar,
    varmvattenberedare och annan utrustning.
    Estetiska anmärkningar avser smak, lukt, färg och den allmänna
    upplevelsen av vattnet.
  </p>
</section>

    <p class=\"disclaimer\">
      Rapporten har tagits fram med hjälp av automatiserad bearbetning och tolkning av analysresultat från ackrediterat laboratorium. Trots omfattande kvalitetskontroller kan fel, avvikelser eller feltolkningar förekomma vid inläsning, bearbetning eller presentation av data.

Rapporten är avsedd som vägledande information och ska inte betraktas som medicinsk rådgivning, hälsobedömning, teknisk projektering, myndighetsbeslut eller annan professionell rådgivning. Bedömningar, slutsatser, rekommendationer och åtgärdsförslag baseras på tillgängliga analysresultat och generell fackkunskap men tar inte hänsyn till samtliga förhållanden som kan påverka vattenkvaliteten, såsom installationer, lokala förutsättningar, provtagningstillfälle eller förändringar över tid.

Fastighetsägaren ansvarar själv för hur informationen tolkas och används samt för eventuella beslut, åtgärder eller investeringar som grundas på rapportens innehåll. Vid osäkerhet eller inför beslut av betydelse rekommenderas att analysresultatet bedöms tillsammans med relevant sakkunnig.

Svenska Vatteninstitutet ansvarar inte för direkta eller indirekta skador, kostnader, uteblivna besparingar eller andra konsekvenser som kan uppstå till följd av användning av rapporten eller de rekommendationer som lämnas i den.
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
