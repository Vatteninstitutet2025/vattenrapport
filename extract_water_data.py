from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

KNOWN_PARAMETERS = [
    "Odlingsbara mikroorganismer 22°C",
    "Escherichia coli",
    "Koliforma bakterier 35°C",
    "Vattentemperatur vid provtagning",
    "Lukt, styrka, vid 20°C",
    "Lukt, art, vid 20 °C",
    "Turbiditet",
    "Färg (410 nm)",
    "pH",
    "Temperatur vid pH-mätning",
    "Alkalinitet",
    "Konduktivitet",
    "Klorid",
    "Sulfat",
    "Fluorid",
    "Radon",
    "COD-Mn",
    "Ammonium",
    "Ammoniumkväve (NH4-N)",
    "Fosfat (PO4)",
    "Fosfatfosfor (PO4-P)",
    "Nitrat (NO3)",
    "Nitratkväve (NO3-N)",
    "Nitrit (NO2)",
    "Nitrit-nitrogen (NO2-N)",
    "NO3/50+NO2/0,5",
    "Hårdhet",
    "Natrium Na (end surgjort)",
    "Kalium K (end surgjort)",
    "Kalcium Ca (end surgjort)",
    "Järn Fe (end surgjort)",
    "Magnesium Mg (end surgjort)",
    "Mangan Mn (end surgjort)",
    "Aluminium Al (end surgjort)",
    "Antimon Sb (end surgjort)",
    "Arsenik As (end surgjort)",
    "Bly Pb (end surgjort)",
    "Kadmium Cd (end surgjort)",
    "Koppar Cu (end surgjort)",
    "Krom Cr (end surgjort)",
    "Nickel Ni (end surgjort)",
    "Selen Se (end surgjort)",
    "Uran U (end surgjort)",
]

PARAMETER_MAP = {
    "Natrium Na (end surgjort)": "Natrium",
    "Kalium K (end surgjort)": "Kalium",
    "Kalcium Ca (end surgjort)": "Kalcium",
    "Järn Fe (end surgjort)": "Järn",
    "Magnesium Mg (end surgjort)": "Magnesium",
    "Mangan Mn (end surgjort)": "Mangan",
    "Aluminium Al (end surgjort)": "Aluminium",
    "Antimon Sb (end surgjort)": "Antimon",
    "Arsenik As (end surgjort)": "Arsenik",
    "Bly Pb (end surgjort)": "Bly",
    "Kadmium Cd (end surgjort)": "Kadmium",
    "Koppar Cu (end surgjort)": "Koppar",
    "Krom Cr (end surgjort)": "Krom",
    "Nickel Ni (end surgjort)": "Nickel",
    "Selen Se (end surgjort)": "Selen",
    "Uran U (end surgjort)": "Uran",
    "Nitrat (NO3)": "Nitrat",
    "Nitrit (NO2)": "Nitrit",
}

METHOD_MARKERS = ["SS-EN", "SS EN", "ISO", "Intern metod", "Beräkning"]
SKIP_LINE_PATTERNS = [
    "Riktvärde",
    "Kommentar/bedömning",
    "Kemisk bedömning",
    "Mikrobiologisk bedömning",
    "Utförande laboratorium",
    "Förklaringar",
    "Denna rapport",
    "Som mottagare",
    "Eurofins tillämpar",
    "Mätosäkerheten",
    "Provet ankom:",
]


def clean_line(line: str) -> str:
    return " ".join(line.split())


def extract_text(pdf_path: str | Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_metadata(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    patterns = {
        "provnummer": r"Provnummer:\s*([0-9\-]+)",
        "provtagningsdatum": r"Provtagningsdatum\*\*\s*([0-9:\-\s]+)",
        "fastighetsbeteckning": r"Fastighetsbeteckning\*\*\s*(.+)",
        "utskriftsdatum": r"Utskriftsdatum:\s*([0-9\-]+)",
        "matris": r"Matris:\s*([A-Za-zÅÄÖåäö]+)",
        "provmarkning": r"Provmärkning:\s*(.+)",
    }
    for key, pat in patterns.items():
        match = re.search(pat, text)
        if match:
            data[key] = clean_line(match.group(1))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:12]:
        match = re.match(r"^([A-ZÅÄÖa-zåäö]+(?: [A-ZÅÄÖa-zåäö]+){1,4})\s+AR-\d{2}-", line)
        if match:
            data["kundnamn"] = clean_line(match.group(1))
            break

    if not data.get("kundnamn"):
        for i, line in enumerate(lines):
            if line.startswith("Kundnummer:") and i > 0:
                candidate = lines[i - 1]
                if len(candidate.split()) >= 2 and not re.search(r"\d{3,}", candidate):
                    data["kundnamn"] = clean_line(candidate)
                    break

    if not data.get("kundnamn") and data.get("provmarkning"):
        data["kundnamn"] = data["provmarkning"]
    return data


def extract_lab_assessment(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    mikro = re.search(r"Mikrobiologisk bedömning\s*(Tjänligt|Tjänligt med anmärkning|Otjänligt)", text)
    kemi = re.search(r"Kemisk bedömning\s*(Tjänligt|Tjänligt med anmärkning|Otjänligt)", text)
    if mikro:
        data["mikrobiologisk_bedomning_lab"] = mikro.group(1)
    if kemi:
        data["kemisk_bedomning_lab"] = kemi.group(1)
    return data


def remove_method_and_uncertainty(rest: str) -> str:
    rest = clean_line(rest)
    cut_positions: list[int] = []
    for marker in METHOD_MARKERS:
        pos = rest.find(marker)
        if pos != -1:
            cut_positions.append(pos)
    if cut_positions:
        rest = rest[: min(cut_positions)].strip()
    rest = re.sub(r"\s+\d+%$", "", rest).strip()
    rest = re.sub(r"\s+[a-d]\)\*?$", "", rest).strip()
    return rest


def parse_result_line(parameter: str, line: str) -> dict[str, Any]:
    rest = remove_method_and_uncertainty(clean_line(line[len(parameter) :].strip()))
    if parameter in ["Lukt, styrka, vid 20°C", "Lukt, art, vid 20 °C"]:
        return {
            "value_numeric": None,
            "value_text": rest,
            "less_than": False,
            "unit": None,
            "raw_result": rest,
        }
    if parameter == "pH":
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", rest)
        if match:
            value_text = match.group(1)
            return {
                "value_numeric": float(value_text.replace(",", ".")),
                "value_text": value_text,
                "less_than": False,
                "unit": None,
                "raw_result": rest,
            }

    match = re.match(r"^([<>]\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(.*)$", rest)
    if match:
        operator = (match.group(1) or "").strip()
        less_than = operator == "<"
        unit = match.group(3).strip() or None
        return {
            "value_numeric": float(match.group(2).replace(",", ".")),
            "value_text": (f"{operator} {match.group(2)}".strip() if operator else match.group(2)),
            "less_than": less_than,
            "unit": unit,
            "raw_result": rest,
        }

    return {
        "value_numeric": None,
        "value_text": rest,
        "less_than": False,
        "unit": None,
        "raw_result": rest,
    }


def should_skip_line(line: str) -> bool:
    return any(pattern in line for pattern in SKIP_LINE_PATTERNS)


def extract_parameters(text: str) -> list[dict[str, Any]]:
    lines = [clean_line(line) for line in text.splitlines() if line.strip()]
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    for line in lines:
        if should_skip_line(line):
            continue
        for parameter in sorted(KNOWN_PARAMETERS, key=len, reverse=True):
            if line.startswith(parameter):
                item = {
                    "parameter_original": parameter,
                    "parameter": PARAMETER_MAP.get(parameter, parameter),
                    **parse_result_line(parameter, line),
                }
                key = (item["parameter_original"], item["value_text"], item["unit"])
                if key not in seen:
                    seen.add(key)
                    results.append(item)
                break
    return results


def main(pdf_path: str, output_path: str = "water_report.json") -> None:
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"Kunde inte hitta PDF-filen: {pdf}")

    text = extract_text(pdf)
    data = {
        "metadata": extract_metadata(text),
        "lab_bedomning": extract_lab_assessment(text),
        "parameters": extract_parameters(text),
        "source_pdf": pdf.name,
    }
    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KLAR ✅ -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("output_path", nargs="?", default="water_report.json")
    args = parser.parse_args()
    main(args.pdf_path, args.output_path)
