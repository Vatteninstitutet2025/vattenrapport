from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

ALIASES = {
    "Escherichia coli": ["E. coli"],
    "E. coli": ["Escherichia coli"],
    "Odlingsbara mikroorganismer": ["Odlingsbara mikroorganismer 22°C"],
    "Koliforma bakterier": ["Koliforma bakterier 35°C"],
    "Lukt, styrka": ["Lukt, styrka, vid 20°C"],
    "Lukt, art": ["Lukt, art, vid 20 °C"],
    "Färg": ["Färg (410 nm)"],
    "Kemisk syreförbrukning": ["COD-Mn"],
    "Total hårdhet": ["Hårdhet"],
}

CRITICAL_POSITIVE_PARAMETERS = [
    "Escherichia coli",
    "Koliforma bakterier",
    "Nitrat",
    "Nitrit",
    "Arsenik",
    "Bly",
    "Kadmium",
    "Uran",
]

SPECIAL_FIELD_OVERRIDES: Dict[str, Dict[str, str]] = {
    "Radon": {
        "health": "Förhöjd radonhalt innebär hälsorisk vid långvarig exponering, främst ökad risk för lungcancer.",
        "causes": "Naturligt förekommande i berggrund och kan lösas i grundvatten.",
        "installations": "Radon kan avgå till inomhusluften vid användning av vatten, särskilt vid dusch och annan luftning.",
        "action": "Installera radonavskiljare eller annan lämplig luftningslösning och följ upp med ny analys.",
    }
}


def load_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_rule(advice_rules: Dict[str, Any], parameter_name: str) -> Dict[str, Any] | None:
    if parameter_name in advice_rules:
        return advice_rules[parameter_name]
    for alias in ALIASES.get(parameter_name, []):
        if alias in advice_rules:
            return advice_rules[alias]
    return None


def format_param_value(param: Dict[str, Any]) -> str:
    return f"{(param.get('value_text') or '').strip()} {(param.get('unit') or '').strip()}".strip()


def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        clean = " ".join((item or "").split()).strip()
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def priority_label(priority: str) -> str:
    return {
        "kritisk": "Akut att börja med",
        "viktig": "Bör följas upp",
        "info": "Information",
    }.get(priority, priority.title())


def build_priority_level(status: str) -> str:
    return "kritisk" if status == "otjänligt" else "viktig" if status == "tjänligt med anmärkning" else "info"


def apply_special_overrides(item: Dict[str, Any]) -> Dict[str, Any]:
    overrides = SPECIAL_FIELD_OVERRIDES.get(item.get("parameter") or "")
    if not overrides:
        return item
    updated = dict(item)
    for field, value in overrides.items():
        updated[field] = value
    return updated


def should_skip_installation_text(text: str, priority: str) -> bool:
    clean = " ".join((text or "").split()).strip().lower().rstrip(".")
    if not clean:
        return True
    if priority != "kritisk" and clean in {
        "ingen påverkan",
        "ingen direkt påverkan",
        "ingen tydlig teknisk påverkan, men källan bör utredas",
        "ingen tydlig teknisk påverkan, men ursprunget bör utredas",
    }:
        return True
    return False


def normalize_cause_text(text: str) -> str:
    clean = " ".join((text or "").split()).strip()
    if not clean:
        return ""
    low = clean.lower()
    if "ytvatten" in low and ("inträng" in low or "påverkan" in low):
        return "Ytvattenpåverkan eller inträngning i brunnen."
    if "otät brunn" in low or ("brunn" in low and "tät" in low):
        return "Otät eller bristfälligt skyddad brunn."
    if "organiskt material" in low:
        return "Organiskt material i eller runt brunnen."
    if "omgivning" in low:
        return "Påverkan från omgivningen nära brunnen."
    if "korrosion" in low and ("rör" in low or "ledning" in low):
        return "Korrosion i rör eller ledningssystem."
    if not clean.endswith("."):
        clean += "."
    return clean[0].upper() + clean[1:]


def default_explanations(parameter: str, status: str, category: str) -> Dict[str, str]:
    if status == "otjänligt":
        if category == "mikrobiologi":
            return {
                "meaning": "Vattnet bör inte användas som vanligt dricksvatten innan orsaken är utredd och åtgärdad.",
                "health": "Det finns risk för påverkan från omgivningen eller förorening i brunnen.",
                "water_quality": "Vattnet kan vara påverkat även om lukt, smak eller utseende inte alltid förändras tydligt.",
                "causes": "Vanliga orsaker är ytvattenpåverkan, bristfällig tätning eller annan påverkan runt brunnen.",
                "installations": "Problemet sitter oftast i vattenkällan eller skyddet runt brunnen snarare än i hushållets installationer.",
                "action": "Använd inte vattnet som vanligt dricksvatten innan uppföljning har gjorts. Kontrollera brunn, lock och tätningar och ta om prov efter åtgärd.",
            }
        return {
            "meaning": "Värdet är så pass avvikande att det behöver åtgärdas eller utredas vidare innan fortsatt normal användning.",
            "health": "Avvikelsen kan innebära hälsorisk eller annan tydlig påverkan som behöver tas på allvar.",
            "water_quality": "Vattenkvaliteten är påverkad på en nivå som kräver åtgärd eller vidare bedömning.",
            "causes": "Orsaken behöver utredas utifrån vattenkälla, installationer och omgivande påverkan.",
            "installations": "Tekniska åtgärder eller kontroll av anläggningen kan behövas beroende på källa till avvikelsen.",
            "action": "Följ upp med omprov och riktad utredning innan fortsatt normal användning.",
        }

    if status == "tjänligt med anmärkning":
        if category == "mikrobiologi":
            return {
                "meaning": "Värdet gör inte vattnet otjänligt i sig, men det är en signal om att vattenkvaliteten bör följas upp.",
                "health": "Det är inte i sig klassat som otjänligt, men det kan tyda på påverkan från omgivningen och motiverar uppföljning.",
                "water_quality": "Det kan vara ett tidigt tecken på att vattenkvaliteten håller på att förändras.",
                "causes": "Vanliga orsaker är ytvattenpåverkan, bristande tätning eller organiskt material i brunnen.",
                "installations": "Det pekar oftast mot behov av kontroll av brunn och vattenkälla snarare än hushållets installationer.",
                "action": "Se över brunnens skydd, lock och tätningar och ta om prov för att se om avvikelsen kvarstår.",
            }
        return {
            "meaning": "Värdet är förhöjt och bör följas upp.",
            "health": "Det finns normalt ingen akut risk, men resultatet bör bedömas tillsammans med övriga värden och hur vattnet används.",
            "water_quality": "Du kan märka påverkan på smak, lukt, färg eller teknisk funktion.",
            "causes": "Avvikelsen kan bero på naturlig geologi, installationer eller lokal påverkan.",
            "installations": "Det kan finnas risk för tekniska problem eller behov av justering i vattenbehandlingen.",
            "action": "Följ upp med kontroll, eventuell teknisk åtgärd och omprov vid behov.",
        }

    return {"meaning": "", "health": "", "water_quality": "", "causes": "", "installations": "", "action": ""}


def compose_finding_explanation(item: Dict[str, Any]) -> str:
    status = item.get("status")
    pieces: List[str] = []

    if status == "otjänligt":
        ordered_keys = ["water_quality", "health", "action"]
    else:
        ordered_keys = ["water_quality", "health", "action"]

    for key in ordered_keys:
        text = " ".join((item.get(key) or "").split()).strip()
        if text:
            pieces.append(text)

    return " ".join(dedupe_keep_order(pieces))


def build_findings(parameters: List[Dict[str, Any]], advice_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for p in parameters:
        status = p.get("status")
        if status not in {"otjänligt", "tjänligt med anmärkning"}:
            continue

        category = p.get("category", "övrigt")
        rule = get_rule(advice_rules, p.get("parameter", "")) or {}
        rule_for_status = rule.get(status, {}) if isinstance(rule, dict) else {}
        fallback = default_explanations(p.get("parameter", ""), status, category)
        priority = build_priority_level(status)

        item = {
            "parameter": p.get("parameter"),
            "display_name": p.get("parameter_display") or p.get("parameter") or "Okänd parameter",
            "value": format_param_value(p),
            "status": status,
            "priority": priority,
            "priority_label": priority_label(priority),
            "category": category,
            "meaning": rule_for_status.get("meaning", fallback.get("meaning", "")),
            "health": rule_for_status.get("health", fallback.get("health", "")),
            "water_quality": rule_for_status.get("water_quality", fallback.get("water_quality", "")),
            "causes": rule_for_status.get("causes", fallback.get("causes", "")),
            "installations": rule_for_status.get("installations", fallback.get("installations", "")),
            "action": rule_for_status.get("action", fallback.get("action", "")),
        }

        item = apply_special_overrides(item)
        item["explanation"] = compose_finding_explanation(item)
        findings.append(item)

    order = {"kritisk": 0, "viktig": 1, "info": 2}
    findings.sort(key=lambda x: (order.get(x["priority"], 9), x["display_name"]))
    return findings


def get_param(parameters: List[Dict[str, Any]], name: str) -> Dict[str, Any] | None:
    for p in parameters:
        if p.get("parameter") == name:
            return p
    return None


def is_abnormal(param: Dict[str, Any] | None) -> bool:
    return bool(param and param.get("status") in {"otjänligt", "tjänligt med anmärkning"})


def numeric_value(param: Dict[str, Any] | None) -> float | None:
    if not param:
        return None
    value = param.get("value_numeric")
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def make_combination_finding(
    *,
    parameter: str,
    display_name: str,
    value: str,
    status: str,
    priority: str,
    category: str,
    health: str,
    water_quality: str,
    causes: str,
    installations: str,
    action: str,
) -> Dict[str, Any]:
    item = {
        "parameter": parameter,
        "display_name": display_name,
        "value": value,
        "status": status,
        "priority": priority,
        "priority_label": priority_label(priority),
        "category": category,
        "meaning": "",
        "health": health,
        "water_quality": water_quality,
        "causes": causes,
        "installations": installations,
        "action": action,
    }
    item["explanation"] = compose_finding_explanation(item)
    return item


def build_combination_findings(parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    iron = get_param(parameters, "Järn")
    manganese = get_param(parameters, "Mangan")
    sodium = get_param(parameters, "Natrium")
    chloride = get_param(parameters, "Klorid")
    aluminium = get_param(parameters, "Aluminium")
    ph = get_param(parameters, "pH")
    nitrate = get_param(parameters, "Nitrat")
    nitrite = get_param(parameters, "Nitrit")
    coliform = get_param(parameters, "Koliforma bakterier")

    if is_abnormal(sodium) and is_abnormal(chloride):
        findings.append(make_combination_finding(
            parameter="Kombination: Natrium och klorid",
            display_name="Natrium och klorid tillsammans",
            value="Möjlig saltpåverkan eller påverkan från vattenbehandling",
            status="tjänligt med anmärkning",
            priority="viktig",
            category="kemi",
            health="Förhöjda halter kan vara olämpliga för personer som behöver begränsa saltintaget.",
            water_quality="Vattnet kan få saltsmak, särskilt om nivåerna ökar över tid.",
            causes="Förhöjt natrium kan påverkas av avhärdningsfilter där kalcium och magnesium byts mot natrium. Om även klorid är förhöjt bör saltpåverkan också övervägas, särskilt i kustnära områden, vid vägsaltpåverkan eller lokala markförhållanden.",
            installations="Förhöjd klorid kan öka risken för korrosion i ledningar och installationer. Natrium i sig ger normalt inte samma tekniska korrosionsrisk.",
            action="Kontrollera om fastigheten har avhärdningsfilter eller annan vattenbehandling. Följ upp natrium och klorid över tid och utred eventuell saltpåverkan om båda halterna är förhöjda.",
        ))

    ph_value = numeric_value(ph)
    if is_abnormal(aluminium) and ph_value is not None and ph_value < 6.5:
        findings.append(make_combination_finding(
            parameter="Kombination: Aluminium och lågt pH",
            display_name="Aluminium och lågt pH",
            value="Surt/korrosivt vatten kan bidra",
            status="tjänligt med anmärkning",
            priority="viktig",
            category="teknik",
            health="Aluminium bör bedömas tillsammans med pH, alkalinitet och övriga värden snarare än isolerat.",
            water_quality="Lågt pH kan påverka smak och bidra till att metaller löses ut.",
            causes="Kombinationen kan bero på surt vatten, naturliga markförhållanden eller påverkan från installationer.",
            installations="Lågt pH kan öka risken för korrosion i ledningar, kopplingar och varmvattenberedare.",
            action="Utred pH, alkalinitet och installationer tillsammans. pH-höjande filter kan vara aktuellt om korrosivitet eller metallutfällning bekräftas.",
        ))

    if is_abnormal(coliform) and is_abnormal(nitrate):
        findings.append(make_combination_finding(
            parameter="Kombination: Koliforma bakterier och nitrat",
            display_name="Koliforma bakterier och nitrat",
            value="Möjlig ytvatten- eller omgivningspåverkan",
            status="tjänligt med anmärkning",
            priority="viktig",
            category="mikrobiologi",
            health="Kombinationen bör tas på allvar, särskilt om vattnet används av barn, gravida eller känsliga personer.",
            water_quality="Vattnet kan vara påverkat även om smak, lukt och färg verkar normala.",
            causes="Kan tyda på påverkan från ytvatten, avlopp, gödsel, otät brunn eller bristande skydd runt brunnen.",
            installations="Problemet sitter ofta i brunnen eller omgivningen snarare än i hushållets installationer.",
            action="Kontrollera brunnens lock, tätningar, avstånd till avlopp/gödsel och ta om prov efter eventuell åtgärd.",
        ))

    if is_abnormal(nitrate) and is_abnormal(nitrite):
        critical = nitrate.get("status") == "otjänligt" or nitrite.get("status") == "otjänligt"
        findings.append(make_combination_finding(
            parameter="Kombination: Nitrat och nitrit",
            display_name="Nitrat och nitrit tillsammans",
            value="Prioriterad hälsobedömning",
            status="otjänligt" if critical else "tjänligt med anmärkning",
            priority="kritisk" if critical else "viktig",
            category="hälsa",
            health="Kombinationen är särskilt viktig för spädbarn och små barn eftersom syretransporten i blodet kan påverkas.",
            water_quality="Nitrat och nitrit påverkar normalt inte lukt, smak eller färg.",
            causes="Kan bero på avlopp, jordbruk, gödsel, ytvattenpåverkan eller biologiska processer i vattenmiljön.",
            installations="Ger normalt inga tekniska problem, men kräver utredning av vattenkälla och eventuell riktad rening.",
            action="Använd annat vatten till spädbarn och små barn tills nivån är utredd och säkerställd. Följ upp med omprov och orsaksutredning.",
        ))


    return findings


def build_positive_observations(parameters: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    good_by_name = {p.get("parameter"): p for p in parameters if p.get("status") == "tjänligt"}
    selected: List[str] = []

    for name in CRITICAL_POSITIVE_PARAMETERS:
        param = good_by_name.get(name)
        if param:
            selected.append(f"{param.get('parameter_display', param.get('parameter'))}: {format_param_value(param)}")

    if len(selected) < limit:
        remaining = [
            p for p in parameters
            if p.get("status") == "tjänligt"
            and f"{p.get('parameter_display', p.get('parameter'))}: {format_param_value(p)}" not in selected
        ]
        remaining.sort(key=lambda x: (str(x.get("category") or ""), str(x.get("parameter_display") or x.get("parameter") or "")))
        for p in remaining:
            selected.append(f"{p.get('parameter_display', p.get('parameter'))}: {format_param_value(p)}")
            if len(selected) >= limit:
                break

    return dedupe_keep_order(selected)[:limit]


def build_quality_check(data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []

    metadata = data.get("metadata", {})
    parameters = data.get("parameters", [])

    if not metadata.get("provnummer"):
        issues.append("Provnummer saknas.")

    if not metadata.get("kundnamn") and not metadata.get("provmarkning"):
        issues.append("Kundnamn eller provmärkning saknas.")

    if len(parameters) < 15:
        issues.append(f"Få parametrar hittades: {len(parameters)}. Kontrollera att PDF:en har tolkats korrekt.")

    assessed = [
        p for p in parameters
        if p.get("status") not in ("ej bedömd", None, "")
    ]

    if len(assessed) < 10:
        issues.append(f"Få bedömda parametrar hittades: {len(assessed)}.")

    critical_health_parameters = {
        "Arsenik",
        "Bly",
        "Kadmium",
        "Uran",
        "Fluorid",
        "Nitrat",
        "Nitrit",
        "Radon",
        "Escherichia coli",
    }

    health_abnormal = [
        p for p in parameters
        if p.get("parameter") in critical_health_parameters
        and p.get("status") in ("otjänligt", "tjänligt med anmärkning")
    ]

    if health_abnormal:
        names = ", ".join(
            sorted({p.get("parameter_display") or p.get("parameter") for p in health_abnormal})
        )
        issues.append(
            f"Hälsorelaterade avvikelser finns ({names}). Rapporten bör granskas manuellt före utskick."
        )

    if not issues:
        return {
            "quality_status": "approved",
            "quality_issues": [],
        }

    return {
        "quality_status": "review_required",
        "quality_issues": issues,
    }


def build_not_assessed_observations(parameters: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    not_assessed = [p for p in parameters if p.get("status") == "ej bedömd"]
    not_assessed.sort(key=lambda x: (str(x.get("category") or ""), str(x.get("parameter_display") or x.get("parameter") or "")))
    return [f"{p.get('parameter_display', p.get('parameter'))}: {format_param_value(p)}" for p in not_assessed[:limit]]


def build_health_section(findings: List[Dict[str, Any]]) -> str:
    critical: List[str] = []
    followup: List[str] = []

    for finding in findings:
        text = " ".join((finding.get("health") or "").split()).strip()
        if not text:
            continue
        line = f"{finding.get('display_name')}: {text}"
        if finding.get("priority") == "kritisk":
            critical.append(line)
        else:
            followup.append(line)

    parts: List[str] = []
    if critical:
        parts.append("Kritiska hälsorelaterade avvikelser:\n- " + "\n- ".join(dedupe_keep_order(critical)))
    if followup:
        parts.append("Övriga avvikelser att följa upp:\n- " + "\n- ".join(dedupe_keep_order(followup)))

    return "\n\n".join(parts) or "Inga tydliga hälsorisker framgår av de klassificerade parametrarna i detta prov."


def build_causes_section(findings: List[Dict[str, Any]]) -> str:
    water: List[str] = []
    environment: List[str] = []
    installations: List[str] = []

    for finding in findings:
        cause = normalize_cause_text(finding.get("causes", ""))
        if not cause:
            continue
        line = f"{finding.get('display_name')}: {cause}"
        low = cause.lower()
        if any(x in low for x in ["brunn", "ytvatten", "tätning", "inträng"]):
            water.append(line)
        elif any(x in low for x in ["berggrund", "grundvatten", "geologi", "organiskt", "omgivning", "mark"]):
            environment.append(line)
        elif any(x in low for x in ["korrosion", "ledning", "rör", "installation"]):
            installations.append(line)
        else:
            environment.append(line)

    parts: List[str] = []
    if water:
        parts.append("Vattenkälla:\n- " + "\n- ".join(dedupe_keep_order(water)))
    if environment:
        parts.append("Omgivning/geologi:\n- " + "\n- ".join(dedupe_keep_order(environment)))
    if installations:
        parts.append("Installationer:\n- " + "\n- ".join(dedupe_keep_order(installations)))

    return "\n\n".join(parts) or "Inga tydliga avvikelser kräver särskild orsaksförklaring i nuläget."


def build_installations_section(findings: List[Dict[str, Any]]) -> str:
    critical_lines: List[str] = []
    followup_lines: List[str] = []

    for finding in findings:
        text = " ".join((finding.get("installations") or "").split()).strip()
        priority = finding.get("priority", "")
        if should_skip_installation_text(text, priority):
            continue
        line = f"{finding.get('display_name')}: {text}"
        if priority == "kritisk":
            critical_lines.append(line)
        else:
            followup_lines.append(line)

    parts: List[str] = []
    if critical_lines:
        parts.append("Kritiska konsekvenser/åtgärder per fynd:\n- " + "\n- ".join(dedupe_keep_order(critical_lines)))
    if followup_lines:
        parts.append("Tekniska följder att följa upp:\n- " + "\n- ".join(dedupe_keep_order(followup_lines)))

    return "\n\n".join(parts) or "Inga tydliga tekniska konsekvenser framgår av de klassificerade parametrarna i detta prov."


def summarize_findings(
    findings: List[Dict[str, Any]],
    field: str,
    critical_header: str,
    followup_header: str,
    empty_text: str,
) -> str:
    critical_lines: List[str] = []
    followup_lines: List[str] = []

    for finding in findings:
        text = " ".join((finding.get(field) or "").split()).strip()
        if not text:
            continue
        line = f"{finding.get('display_name')}: {text}"
        if finding.get("priority") == "kritisk":
            critical_lines.append(line)
        else:
            followup_lines.append(line)

    parts: List[str] = []
    if critical_lines:
        parts.append(f"{critical_header}\n- " + "\n- ".join(dedupe_keep_order(critical_lines)))
    if followup_lines:
        parts.append(f"{followup_header}\n- " + "\n- ".join(dedupe_keep_order(followup_lines)))

    return "\n\n".join(parts) or empty_text


def build_practical_advice(findings: List[Dict[str, Any]], overall: str) -> str:
    advice: List[str] = []

    names = {f.get("parameter") for f in findings}
    display_names = {f.get("display_name") for f in findings}

    if "Järn" in names:
        advice.append(
            "Förhöjd järnhalt ger ofta estetiska problem i form av missfärgningar och beläggningar och kan även påverka lukt, färg och smak. Om detta märks i vardagen bör orsaken följas upp och eventuell vattenbehandling bedömas utifrån pH, alkalinitet och övriga värden."
        )

    if "Mangan" in names:
        advice.append(
            "Förhöjd manganhalt kan framför allt ge svarta utfällningar och leda till igensättning av armaturer, ventiler, rör och hushållsmaskiner varför en inriktad vattenrening ofta är nödvändig för att undvika slitage."
        )

    if "Natrium" in names or "Klorid" in names or "Natrium och klorid tillsammans" in display_names:
        advice.append(
            "Om natrium eller klorid är förhöjt bör du kontrollera om fastigheten har avhärdningsfilter eller annan vattenbehandling. Vid kustnära lägen eller stigande halter över tid bör även saltpåverkan utredas."
        )

    if "Koliforma bakterier" in names:
        advice.append(
            "Vid koliforma bakterier bör brunnslock, tätningar och eventuell ytvattenpåverkan kontrolleras. Ta gärna omprov efter kontroll eller åtgärd för att se om påverkan kvarstår."
        )

    if "Escherichia coli" in names:
        advice.append(
            "Vid E. coli bör vattnet tills vidare inte användas till dryck, matlagning eller tandborstning. Kontrollera brunnen, utred möjlig fekal påverkan och ta omprov efter åtgärd."
        )

    if "Nitrat" in names or "Nitrit" in names:
        advice.append(
            "Vid förhöjt nitrat eller nitrit bör annat vatten användas till spädbarn och små barn tills nivån är utredd och säkerställd. Utred möjliga källor som avlopp, gödsel, jordbruk eller ytvattenpåverkan."
        )

    if "Fluorid" in names:
        advice.append(
            "Vid förhöjd fluoridhalt bör vattnet bedömas särskilt om barn använder det som dricksvatten. Följ upp halten och utred lämplig åtgärd innan långvarig användning fortsätter."
        )

    if "Radon" in names:
        advice.append(
            "Vid förhöjd radonhalt bör åtgärd inriktas på luftning eller radonavskiljning, eftersom radon framför allt avgår till inomhusluften vid duschning, tvätt och annan användning av vattnet."
        )

    if "Aluminium" in names:
        advice.append(
            "Förhöjt aluminium bör bedömas tillsammans med pH, alkalinitet och installationer. Om vattnet är surt kan korrosion eller urlakning från mark och installationer behöva utredas."
        )

    if "Koppar" in names:
        advice.append(
            "Förhöjd kopparhalt bör bedömas tillsammans med pH och installationer, eftersom surt eller korrosivt vatten kan lösa ut koppar från ledningar och varmvattenberedare."
        )

    if not advice:
        if overall == "otjänligt":
            advice.append(
                "Eftersom provet är otjänligt bör vattnet inte användas som normalt dricksvatten innan orsaken är utredd och eventuell åtgärd är genomförd."
            )
        elif overall == "tjänligt med anmärkning":
            advice.append(
                "Följ upp de avvikande parametrarna och bedöm dem tillsammans med brunnstyp, installationer och hur vattnet används i hushållet."
            )
        else:
            advice.append(
                "Fortsätt med regelbunden provtagning för att följa vattenkvaliteten över tid."
            )

    advice.append(
        "Ta ett nytt vattenprov efter genomförd åtgärd eller om du vill kontrollera om avvikelsen är tillfällig eller återkommande."
    )

    return "\n".join(f"- {item}" for item in dedupe_keep_order(advice))


def build_sections(data: Dict[str, Any], findings: List[Dict[str, Any]], not_assessed: List[str]) -> Dict[str, str]:
    overall = data.get("overall_status", "okänd")
    critical_findings = [f for f in findings if f.get("priority") == "kritisk"]

    if overall == "otjänligt":
        summary = "Vattnet bedöms som otjänligt. Minst en parameter ligger på en nivå där vattnet inte bör användas som normalt dricksvatten utan åtgärd eller vidare bedömning."
        conclusion = "Slutsatsen är att vattnet bör följas upp med åtgärd innan fortsatt normal användning som dricksvatten."
        what_it_means = "Otjänligt innebär att vattnet inte bör användas som vanligt dricksvatten innan orsaken är utredd och lämpliga åtgärder har genomförts."
    elif overall == "tjänligt med anmärkning":
        summary = "Vattnet bedöms som tjänligt med anmärkning. Det går ofta att använda, men avvikande värden bör följas upp eftersom de kan påverka smak, teknik eller i vissa fall hälsobedömning."
        conclusion = "Slutsatsen är att vattnet kan användas men att avvikelserna bör prioriteras och följas upp."
        what_it_means = "Tjänligt med anmärkning innebär att vattnet kan användas, men att vissa parametrar avviker från önskad nivå och bör följas upp."
    else:
        summary = "Vattnet bedöms som tjänligt utifrån klassificerade parametrar. Inga värden sticker ut på nivåer som ger anmärkning eller otjänlighet."
        conclusion = "Slutsatsen är att provet ser bra ut utifrån de parametrar som har bedömts."
        what_it_means = "Rapporten visar inga avvikelser som kräver särskild tolkning i detta prov."

    if critical_findings:
        main_reason = ", ".join(f"{f['display_name']} {f['value']}" for f in critical_findings)
        summary += f" Huvudorsak till otjänligt i detta prov: {main_reason}."

    health_assessment = build_health_section(findings)
    causes = build_causes_section(findings)
    installations = build_installations_section(findings)
    actions = summarize_findings(
        findings,
        "action",
        "Bör göras direkt:",
        "Bör planeras in:",
        "Ingen omedelbar särskild åtgärd framstår som nödvändig utifrån klassificeringen.",
    )

    return {
        "summary": summary,
        "what_it_means": what_it_means,
        "health_assessment": health_assessment,
        "causes": causes,
        "installations": installations,
        "actions": actions,
        "practical_advice": build_practical_advice(findings, overall),
        "conclusion": conclusion,
    }


def validate_report_model(report_model: Dict[str, Any]) -> None:
    for key in [
        "metadata",
        "overall_status",
        "mikrobiologisk_status",
        "kemisk_status",
        "quality_status",
        "quality_issues",
        "parameters",
        "priority_findings",
        "positive_observations",
        "not_assessed_observations",
        "generated_sections",
    ]:
        if key not in report_model:
            raise ValueError(f"Saknar nyckel i report_model: {key}")

    for key in [
        "summary",
        "what_it_means",
        "health_assessment",
        "causes",
        "installations",
        "actions",
        "practical_advice",
        "conclusion",
    ]:
        if key not in report_model["generated_sections"]:
            raise ValueError(f"Saknar sektion i generated_sections: {key}")


def build_report_model(
    input_path: str = "classified_report_v3.json",
    advice_rules_path: str = "advice_rules.json",
    output_path: str = "report_model_v3.json",
) -> None:
    data = load_json(input_path)
    advice_rules = load_json(advice_rules_path)

    parameters = data.get("parameters", [])

    findings = build_findings(parameters, advice_rules)
    findings.extend(build_combination_findings(parameters))

    order = {"kritisk": 0, "viktig": 1, "info": 2}
    findings.sort(key=lambda x: (order.get(x.get("priority"), 9), x.get("display_name", "")))

    not_assessed = build_not_assessed_observations(parameters)
    quality = build_quality_check(data)

    report_model = {
        "metadata": data.get("metadata", {}),
        "overall_status": data.get("overall_status", "okänd"),
        "mikrobiologisk_status": data.get("mikrobiologisk_status", "ej bedömd"),
        "kemisk_status": data.get("kemisk_status", "ej bedömd"),
        "quality_status": quality["quality_status"],
        "quality_issues": quality["quality_issues"],
        "parameters": parameters,
        "priority_findings": findings,
        "positive_observations": build_positive_observations(parameters),
        "not_assessed_observations": not_assessed,
        "generated_sections": build_sections(data, findings, not_assessed),
    }

    validate_report_model(report_model)
    save_json(output_path, report_model)
    print(f"KLAR ✅ -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", nargs="?", default="classified_report_v3.json")
    parser.add_argument("advice_rules_path", nargs="?", default="advice_rules.json")
    parser.add_argument("output_path", nargs="?", default="report_model_v3.json")
    args = parser.parse_args()

    build_report_model(args.input_path, args.advice_rules_path, args.output_path)