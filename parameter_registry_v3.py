from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ParameterSpec:
    canonical_name: str
    display_name: str
    category: str
    unit_hint: Optional[str] = None


PARAMETER_ALIASES: Dict[str, str] = {
    "Odlingsbara mikroorganismer 22°C": "Odlingsbara mikroorganismer",
    "Escherichia coli": "Escherichia coli",
    "E. coli": "Escherichia coli",
    "Koliforma bakterier 35°C": "Koliforma bakterier",
    "Vattentemperatur vid provtagning": "Vattentemperatur vid provtagning",
    "Lukt, styrka, vid 20°C": "Lukt, styrka",
    "Lukt, art, vid 20 °C": "Lukt, art",
    "Turbiditet": "Turbiditet",
    "Färg (410 nm)": "Färg",
    "pH": "pH",
    "Temperatur vid pH-mätning": "Temperatur vid pH-mätning",
    "Alkalinitet": "Alkalinitet",
    "Konduktivitet": "Konduktivitet",
    "Klorid": "Klorid",
    "Sulfat": "Sulfat",
    "Fluorid": "Fluorid",
    "Radon": "Radon",
    "COD-Mn": "Kemisk syreförbrukning",
    "Ammonium": "Ammonium",
    "Ammoniumkväve (NH4-N)": "Ammoniumkväve",
    "Fosfat (PO4)": "Fosfat",
    "Fosfatfosfor (PO4-P)": "Fosfatfosfor",
    "Nitrat (NO3)": "Nitrat",
    "Nitratkväve (NO3-N)": "Nitratkväve",
    "Nitrit (NO2)": "Nitrit",
    "Nitrit-nitrogen (NO2-N)": "Nitrit-nitrogen",
    "NO3/50+NO2/0,5": "Nitrat/Nitrit-kvot",
    "Hårdhet": "Total hårdhet",
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
}


PARAMETER_SPECS: Dict[str, ParameterSpec] = {
    "Escherichia coli": ParameterSpec("Escherichia coli", "Escherichia coli", "mikrobiologi"),
    "Koliforma bakterier": ParameterSpec("Koliforma bakterier", "Koliforma bakterier", "mikrobiologi"),
    "Odlingsbara mikroorganismer": ParameterSpec("Odlingsbara mikroorganismer", "Odlingsbara mikroorganismer", "mikrobiologi"),
    "Lukt, styrka": ParameterSpec("Lukt, styrka", "Lukt, styrka", "sensorik"),
    "Lukt, art": ParameterSpec("Lukt, art", "Lukt, art", "sensorik"),
    "Turbiditet": ParameterSpec("Turbiditet", "Turbiditet", "kvalitet"),
    "Färg": ParameterSpec("Färg", "Färg", "kvalitet"),
    "pH": ParameterSpec("pH", "pH", "teknik"),
    "Alkalinitet": ParameterSpec("Alkalinitet", "Alkalinitet", "teknik"),
    "Konduktivitet": ParameterSpec("Konduktivitet", "Konduktivitet", "kemi"),
    "Klorid": ParameterSpec("Klorid", "Klorid", "kemi"),
    "Sulfat": ParameterSpec("Sulfat", "Sulfat", "kemi"),
    "Fluorid": ParameterSpec("Fluorid", "Fluorid", "hälsa"),
    "Radon": ParameterSpec("Radon", "Radon", "hälsa"),
    "Kemisk syreförbrukning": ParameterSpec("Kemisk syreförbrukning", "COD-Mn", "kemi"),
    "Ammonium": ParameterSpec("Ammonium", "Ammonium", "kemi"),
    "Fosfat": ParameterSpec("Fosfat", "Fosfat", "kemi"),
    "Nitrat": ParameterSpec("Nitrat", "Nitrat", "hälsa"),
    "Nitrit": ParameterSpec("Nitrit", "Nitrit", "hälsa"),
    "Nitrat/Nitrit-kvot": ParameterSpec("Nitrat/Nitrit-kvot", "NO3/50 + NO2/0,5", "hälsa"),
    "Total hårdhet": ParameterSpec("Total hårdhet", "Hårdhet", "teknik"),
    "Natrium": ParameterSpec("Natrium", "Natrium", "kemi"),
    "Kalium": ParameterSpec("Kalium", "Kalium", "kemi"),
    "Kalcium": ParameterSpec("Kalcium", "Kalcium", "teknik"),
    "Järn": ParameterSpec("Järn", "Järn", "teknik"),
    "Magnesium": ParameterSpec("Magnesium", "Magnesium", "teknik"),
    "Mangan": ParameterSpec("Mangan", "Mangan", "teknik"),
    "Aluminium": ParameterSpec("Aluminium", "Aluminium", "hälsa"),
    "Antimon": ParameterSpec("Antimon", "Antimon", "hälsa"),
    "Arsenik": ParameterSpec("Arsenik", "Arsenik", "hälsa"),
    "Bly": ParameterSpec("Bly", "Bly", "hälsa"),
    "Kadmium": ParameterSpec("Kadmium", "Kadmium", "hälsa"),
    "Koppar": ParameterSpec("Koppar", "Koppar", "teknik"),
    "Krom": ParameterSpec("Krom", "Krom", "hälsa"),
    "Nickel": ParameterSpec("Nickel", "Nickel", "hälsa"),
    "Selen": ParameterSpec("Selen", "Selen", "hälsa"),
    "Uran": ParameterSpec("Uran", "Uran", "hälsa"),
    "Vattentemperatur vid provtagning": ParameterSpec("Vattentemperatur vid provtagning", "Vattentemperatur vid provtagning", "metadata"),
    "Temperatur vid pH-mätning": ParameterSpec("Temperatur vid pH-mätning", "Temperatur vid pH-mätning", "metadata"),
    "Ammoniumkväve": ParameterSpec("Ammoniumkväve", "Ammoniumkväve", "metadata"),
    "Fosfatfosfor": ParameterSpec("Fosfatfosfor", "Fosfatfosfor", "metadata"),
    "Nitratkväve": ParameterSpec("Nitratkväve", "Nitratkväve", "metadata"),
    "Nitrit-nitrogen": ParameterSpec("Nitrit-nitrogen", "Nitrit-nitrogen", "metadata"),
}


def normalize_parameter_name(name: str) -> str:
    return PARAMETER_ALIASES.get(name, name)


def get_display_name(name: str) -> str:
    canonical = normalize_parameter_name(name)
    spec = PARAMETER_SPECS.get(canonical)
    return spec.display_name if spec else canonical


def get_category(name: str) -> str:
    canonical = normalize_parameter_name(name)
    spec = PARAMETER_SPECS.get(canonical)
    return spec.category if spec else "övrigt"


def enrich_parameter(param: Dict[str, Any]) -> Dict[str, Any]:
    original = param.get("parameter_original") or param.get("parameter") or ""
    canonical = normalize_parameter_name(original)
    enriched = dict(param)
    enriched["parameter_original"] = original
    enriched["parameter"] = canonical
    enriched["parameter_display"] = get_display_name(canonical)
    enriched["category"] = get_category(canonical)
    return enriched
