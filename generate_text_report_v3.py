from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

STATUS_LABELS = {
    "tjänligt": "Tjänligt",
    "tjänligt med anmärkning": "Tjänligt med anmärkning",
    "otjänligt": "Otjänligt",
    "ej bedömd": "Ej bedömd",
}


def nice_status(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def format_bullets(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return "\n".join(f"- {item}" for item in cleaned)


def clean_block(text: str | None) -> str:
    return (text or "").strip()


def format_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "- Inga avvikande fynd att prioritera."

    blocks: list[str] = []
    for item in findings:
        header = f"{item.get('display_name', 'Okänd parameter')}: {item.get('value', '')}".strip()
        lines = [header]
        lines.append(f"  Status: {nice_status(item.get('status', ''))}")
        if item.get("priority_label"):
            lines.append(f"  Prioritet: {item['priority_label']}")
        if item.get("explanation"):
            lines.append("  Vad det betyder för dig:")
            lines.append(f"  {item['explanation'].strip()}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_reference_text(p: dict[str, Any]) -> str:
    ref = p.get("reference_values") or {}
    if ref:
        return (
            f"Riktvärden: enhet {ref.get('unit', '-')}; "
            f"tjänligt med anmärkning {ref.get('remark', '-')}; "
            f"otjänligt {ref.get('unfit', '-')}"
        )
    return p.get("reference_text") or "Riktvärde saknas eller är inte angivet i aktuell tabell."


def format_all_parameters(parameters: list[dict[str, Any]]) -> str:
    if not parameters:
        return "- Inga parametrar att visa."

    grouped: dict[str, list[str]] = {
        "otjänligt": [],
        "tjänligt med anmärkning": [],
        "tjänligt": [],
        "ej bedömd": [],
    }
    other: list[str] = []

    for p in parameters:
        value = f"{(p.get('value_text') or '').strip()} {(p.get('unit') or '').strip()}".strip()
        line = (
            f"{p.get('parameter_display', p.get('parameter', ''))}: "
            f"{value} — {p.get('category', '')} — {format_reference_text(p)} — "
            f"{nice_status(p.get('status', ''))}"
        )
        status = (p.get("status") or "").strip().lower()
        if status in grouped:
            grouped[status].append(line)
        else:
            other.append(line)

    blocks: list[str] = []
    headings = [
        ("OTJÄNLIGT", grouped["otjänligt"]),
        ("TJÄNLIGT MED ANMÄRKNING", grouped["tjänligt med anmärkning"]),
        ("TJÄNLIGT", grouped["tjänligt"]),
        ("EJ BEDÖMD", grouped["ej bedömd"]),
        ("ÖVRIGT", other),
    ]
    for heading, items in headings:
        if items:
            blocks.append(f"{heading}\n{'~' * len(heading)}\n{format_bullets(items)}")
    return "\n\n".join(blocks)


def generate_text_report(input_path: str = "report_model_v3.json", output_path: str = "report_text_v3.txt") -> None:
    with Path(input_path).open("r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("generated_sections", {})
    findings = data.get("priority_findings", [])
    positives = data.get("positive_observations", [])
    not_assessed = data.get("not_assessed_observations", [])
    parameters = data.get("parameters", [])
    meta = data.get("metadata", {})

    text = f"""VATTENRAPPORT V3
================

Kund: {meta.get('kundnamn', '')}
Fastighet: {meta.get('fastighetsbeteckning', '')}
Provnummer: {meta.get('provnummer', '')}
Provtagningsdatum: {meta.get('provtagningsdatum', '')}

Samlad bedömning: {nice_status(data.get('overall_status', 'okänd'))}
Mikrobiologisk status: {nice_status(data.get('mikrobiologisk_status', 'ej bedömd'))}
Kemisk status: {nice_status(data.get('kemisk_status', 'ej bedömd'))}

SAMMANFATTNING
--------------
{clean_block(sections.get('summary'))}

VAD DET INNEBÄR
---------------
{clean_block(sections.get('what_it_means'))}

DET HÄR BÖR DU HA KOLL PÅ
----------------------------
{format_findings(findings)}

VÅR REKOMMENDATION TILL DIG
-------------------------
{clean_block(sections.get('actions'))}

PRAKTISKA RÅD I VARDAGEN
-------------
{clean_block(sections.get('practical_advice'))}

HÄLSA
-----
{clean_block(sections.get('health_assessment'))}

MÖJLIGA ORSAKER
---------------
{clean_block(sections.get('causes'))}

TEKNISKA KONSEKVENSER / VAD SOM KAN BEHÖVA GÖRAS
--------------------------------
{clean_block(sections.get('installations'))}

DET SOM SER BRA UT
------------------
{format_bullets(positives) or '- Inga särskilda positiva observationer att visa.'}

ÖVRIGA ANALYSER UTAN SEPARAT BEDÖMNING
--------------------------------------
{format_bullets(not_assessed) or '- Inga sådana parametrar att visa.'}

ALLA PARAMETRAR
---------------
{format_all_parameters(parameters)}

Förklaring till riktvärden: (h) hälsomässig, (e) estetisk och (t) teknisk bedömningsgrund. Riktvärden enligt Analysparametrar och riktvärden, version 2026-02-04.

SLUTSATS
--------
{clean_block(sections.get('conclusion'))}

--------------------------------------------------
Rapporten är automatiskt genererad och utgör endast vägledande information.
Svenska Vatteninstitutet ansvarar inte för beslut, åtgärder eller konsekvenser
som baseras på rapportens innehåll.
"""

    Path(output_path).write_text(text, encoding="utf-8")
    print(f"KLAR ✅ -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", nargs="?", default="report_model_v3.json")
    parser.add_argument("output_path", nargs="?", default="report_text_v3.txt")
    args = parser.parse_args()
    generate_text_report(args.input_path, args.output_path)
