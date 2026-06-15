from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from parameter_registry_v3 import enrich_parameter


RULES: Dict[str, Dict[str, Any]] = {
    "Escherichia coli": {"type": "presence", "unfit_if_detected": True},
    "Koliforma bakterier": {"type": "high", "remark_gt": 50, "unfit_gt": 500},
    "Odlingsbara mikroorganismer": {"type": "high", "remark_gt": 1000},
    "Lukt, styrka": {"type": "smell_strength"},
    "Lukt, art": {"type": "smell_art"},
    "Turbiditet": {"type": "high", "remark_gt": 3.0},
    "Färg": {"type": "high", "remark_gt": 30},
    "pH": {"type": "ph", "remark_lt": 6.5, "unfit_gt": 10.5},
    "Alkalinitet": {"type": "no_threshold"},
    "Konduktivitet": {"type": "no_threshold"},
    "Klorid": {"type": "high", "remark_gt": 100},
    "Sulfat": {"type": "high", "remark_gt": 100},
    "Fluorid": {"type": "high", "unfit_gt": 1.5},
    "Radon": {"type": "high", "unfit_gt": 1000},
    "Kemisk syreförbrukning": {"type": "high", "remark_gt": 8.0},
    "Ammonium": {"type": "high", "remark_gt": 0.50},
    "Ammoniumkväve": {"type": "no_threshold"},
    "Fosfat": {"type": "high", "remark_gt": 0.60},
    "Fosfatfosfor": {"type": "no_threshold"},
    "Nitrat": {"type": "high", "remark_gt": 20, "unfit_gt": 50},
    "Nitratkväve": {"type": "no_threshold"},
    "Nitrit": {"type": "high", "remark_gt": 0.10, "unfit_gt": 0.50},
    "Nitrit-nitrogen": {"type": "no_threshold"},
    "Nitrat/Nitrit-kvot": {"type": "high", "unfit_gt": 1.0},
    "Total hårdhet": {"type": "high", "remark_gt": 15},
    "Natrium": {"type": "high", "remark_gt": 100},
    "Kalium": {"type": "high", "remark_gt": 12},
    "Kalcium": {"type": "high", "remark_gt": 100},
    "Järn": {"type": "high", "remark_gt": 0.5},
    "Magnesium": {"type": "high", "remark_gt": 30},
    "Mangan": {"type": "high", "remark_gt": 0.3},
    "Aluminium": {"type": "high", "remark_gt": 0.50},
    "Antimon": {"type": "high", "unfit_gt": 0.010},
    "Arsenik": {"type": "high", "unfit_gt": 0.005},
    "Bly": {"type": "high", "unfit_gt": 0.005},
    "Kadmium": {"type": "high", "unfit_gt": 0.0005},
    "Koppar": {"type": "high", "remark_gt": 0.20, "unfit_gt": 2.0},
    "Krom": {"type": "high", "unfit_gt": 0.050},
    "Nickel": {"type": "high", "unfit_gt": 0.020},
    "Selen": {"type": "high", "unfit_gt": 0.020},
    "Uran": {"type": "high", "remark_gt": 0.03},
    "Vattentemperatur vid provtagning": {"type": "no_threshold"},
    "Temperatur vid pH-mätning": {"type": "no_threshold"},
}


# Riktvärden enligt "Analysparametrar och riktvärden", version 2026-02-04.
# "remark" = tjänligt med anmärkning, "unfit" = otjänligt.
REFERENCE_VALUES: Dict[str, Dict[str, Any]] = {
    "Escherichia coli": {"unit": "Antal/100 ml", "remark": "-", "unfit": "Påvisad (h)"},
    "Koliforma bakterier": {"unit": "Antal/100 ml", "remark": "50 (h)", "unfit": "500 (h)"},
    "Odlingsbara mikroorganismer": {"unit": "Antal/ml", "remark": "1000 (h)", "unfit": "-"},
    "Alkalinitet": {"unit": "mg/l HCO3", "remark": "-", "unfit": "-"},
    "Arsenik": {"unit": "µg/l As", "remark": "-", "unfit": "5,0 (h)"},
    "Ammonium": {"unit": "mg/l NH4", "remark": "0,50 (t); 1,5 (h, t)", "unfit": "-"},
    "Bly": {"unit": "µg/l Pb", "remark": "-", "unfit": "5,0 (h)"},
    "Fluorid": {"unit": "mg/l F", "remark": "-", "unfit": "1,5 (h)"},
    "Fosfat": {"unit": "mg/l PO4", "remark": "0,60", "unfit": "-"},
    "Färg": {"unit": "mg/l Pt", "remark": "30 (e)", "unfit": "-"},
    "Järn": {"unit": "µg/l Fe", "remark": "500 (e, t)", "unfit": "-"},
    "Kadmium": {"unit": "µg/l Cd", "remark": "-", "unfit": "0,5 (h)"},
    "Kalcium": {"unit": "mg/l Ca", "remark": "100 (t)", "unfit": "-"},
    "Kalium": {"unit": "mg/l K", "remark": "12", "unfit": "-"},
    "Kemisk syreförbrukning": {"unit": "mg/l O2", "remark": "8,0 (e)", "unfit": "-"},
    "Klorid": {"unit": "mg/l Cl", "remark": "100 (t); 300 (e, t)", "unfit": "-"},
    "Konduktivitet": {"unit": "µS/cm", "remark": "-", "unfit": "-"},
    "Koppar": {"unit": "mg/l Cu", "remark": "0,20 (e, t)", "unfit": "2,0 (h, e, t)"},
    "Magnesium": {"unit": "mg/l Mg", "remark": "30 (e)", "unfit": "-"},
    "Mangan": {"unit": "µg/l Mn", "remark": "300 (e, t)", "unfit": "-"},
    "Natrium": {"unit": "mg/l Na", "remark": "100 (t); 200 (e, t)", "unfit": "-"},
    "Nitrat": {"unit": "mg/l NO3", "remark": "20 (t)", "unfit": "50 (h, t)"},
    "Nitrit": {"unit": "mg/l NO2", "remark": "0,10 (h, t)", "unfit": "0,50 (h)"},
    "pH": {"unit": "-", "remark": "< 6,5 (t)", "unfit": "10,5 (h)"},
    "Sulfat": {"unit": "mg/l SO4", "remark": "100 (t); 250 (h, e, t)", "unfit": "-"},
    "Total hårdhet": {"unit": "°dH", "remark": "15 (t)", "unfit": "-"},
    "Turbiditet": {"unit": "FNU", "remark": "3,0", "unfit": "-"},
    "Uran": {"unit": "µg/l U", "remark": "30 (h)", "unfit": "-"},
    "Aluminium": {"unit": "µg/l Al", "remark": "500 (t)", "unfit": "-"},
    "Antimon": {"unit": "µg/l Sb", "remark": "-", "unfit": "10 (h)"},
    "Krom": {"unit": "µg/l Cr", "remark": "-", "unfit": "50 (h)"},
    "Nickel": {"unit": "µg/l Ni", "remark": "-", "unfit": "20 (h)"},
    "Selen": {"unit": "µg/l Se", "remark": "-", "unfit": "20 (h)"},
    "Radon": {"unit": "Bq/l", "remark": "-", "unfit": "1000 (h)"},
    "Lukt, styrka": {"unit": "-", "remark": "Tydlig (e)", "unfit": "Svag/tydlig främmande eller stark/mycket stark (e, h)"},
    "Lukt, art": {"unit": "-", "remark": "Tydlig (e)", "unfit": "Svag/tydlig främmande eller stark/mycket stark (e, h)"},
}


def build_reference_text(parameter_name: str) -> str:
    ref = REFERENCE_VALUES.get(parameter_name)
    if not ref:
        return "Riktvärde saknas eller är inte angivet i aktuell tabell."
    return (
        f"Enhet: {ref.get('unit', '-')} | "
        f"Tjänligt med anmärkning: {ref.get('remark', '-')} | "
        f"Otjänligt: {ref.get('unfit', '-')}"
    )


def add_reference_values(param: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(param)
    ref = REFERENCE_VALUES.get(updated.get("parameter"))
    updated["reference_values"] = ref or {"unit": "-", "remark": "-", "unfit": "-"}
    updated["reference_text"] = build_reference_text(updated.get("parameter", ""))
    return updated


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def has_detection(param: Dict[str, Any]) -> bool:
    value = to_float(param.get("value_numeric"))
    less_than = bool(param.get("less_than", False))
    return value is not None and not less_than and value >= 1


def classify_high(param: Dict[str, Any], rule: Dict[str, Any]) -> str:
    value = to_float(param.get("value_numeric"))
    if value is None:
        return "ej bedömd"
    if rule.get("unfit_gt") is not None and value > rule["unfit_gt"]:
        return "otjänligt"
    if rule.get("remark_gt") is not None and value > rule["remark_gt"]:
        return "tjänligt med anmärkning"
    return "tjänligt"


def classify_presence(param: Dict[str, Any], rule: Dict[str, Any]) -> str:
    return "otjänligt" if rule.get("unfit_if_detected") and has_detection(param) else "tjänligt"


def classify_ph(param: Dict[str, Any], rule: Dict[str, Any]) -> str:
    value = to_float(param.get("value_numeric"))
    if value is None:
        return "ej bedömd"
    if rule.get("unfit_gt") is not None and value > rule["unfit_gt"]:
        return "otjänligt"
    if rule.get("remark_lt") is not None and value < rule["remark_lt"]:
        return "tjänligt med anmärkning"
    return "tjänligt"


def classify_smell_strength(param: Dict[str, Any]) -> str:
    text = norm_text(param.get("value_text"))
    if text in {"", "ingen"}:
        return "tjänligt"
    if "mycket stark" in text or text == "stark":
        return "otjänligt"
    if "tydlig" in text or "svag" in text:
        return "tjänligt med anmärkning"
    return "ej bedömd"


def classify_smell_art(param: Dict[str, Any]) -> str:
    text = norm_text(param.get("value_text"))
    if text in {"", "ingen"}:
        return "tjänligt"
    if any(word in text for word in ["petroleum", "kemisk", "konstgjord", "främmande", "motbjudande"]):
        return "otjänligt"
    return "tjänligt med anmärkning"


def classify_parameter(param: Dict[str, Any]) -> str:
    rule = RULES.get(param.get("parameter"))
    if not rule:
        return "ej bedömd"
    rule_type = rule["type"]
    if rule_type == "high":
        return classify_high(param, rule)
    if rule_type == "presence":
        return classify_presence(param, rule)
    if rule_type == "ph":
        return classify_ph(param, rule)
    if rule_type == "smell_strength":
        return classify_smell_strength(param)
    if rule_type == "smell_art":
        return classify_smell_art(param)
    if rule_type == "no_threshold":
        return "ej bedömd"
    return "ej bedömd"


def classify_overall(parameters: List[Dict[str, Any]]) -> str:
    statuses = [p.get("status") for p in parameters]
    if "otjänligt" in statuses:
        return "otjänligt"
    if "tjänligt med anmärkning" in statuses:
        return "tjänligt med anmärkning"
    return "tjänligt"


def classify_group(parameters: List[Dict[str, Any]], include_categories: set[str]) -> str:
    statuses = [
        p.get("status")
        for p in parameters
        if p.get("category") in include_categories and p.get("status") != "ej bedömd"
    ]
    if not statuses:
        return "ej bedömd"
    if "otjänligt" in statuses:
        return "otjänligt"
    if "tjänligt med anmärkning" in statuses:
        return "tjänligt med anmärkning"
    return "tjänligt"


def classify_all(input_path: str = "water_report.json", output_path: str = "classified_report_v3.json") -> None:
    input_file = Path(input_path)
    with input_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    parameters = [add_reference_values(enrich_parameter(p)) for p in data.get("parameters", [])]
    for param in parameters:
        param["status"] = classify_parameter(param)

    data["parameters"] = parameters
    data["mikrobiologisk_status"] = classify_group(parameters, {"mikrobiologi"})
    data["kemisk_status"] = classify_group(parameters, {"hälsa", "kemi", "kvalitet", "teknik", "sensorik"})
    data["overall_status"] = classify_overall(parameters)

    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"KLAR ✅ -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", nargs="?", default="water_report.json")
    parser.add_argument("output_path", nargs="?", default="classified_report_v3.json")
    args = parser.parse_args()
    classify_all(args.input_path, args.output_path)
