from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT_ROOT = HERE / "output"


def safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', '_', value)
    cleaned = re.sub(r'\s+', '_', cleaned).strip('._ ')
    return cleaned or 'rapport'


def build_run_directory(pdf_path: Path) -> Path:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder_name = f"{safe_name(pdf_path.stem)}_{timestamp}"
    run_dir = OUTPUT_ROOT / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_step(script_name: str, *args: str) -> None:
    script_path = HERE / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Kunde inte hitta skriptet: {script_path}")

    cmd = [sys.executable, str(script_path), *args]
    print("KÖR:", " ".join(f'"{part}"' if ' ' in part else part for part in cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kör hela vattenrapportflödet.")
    parser.add_argument("pdf_path", help="Sökväg till laboratoriets PDF")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Kunde inte hitta PDF-filen: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Filen måste vara en PDF: {pdf_path}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = build_run_directory(pdf_path)

    water_report = run_dir / "water_report.json"
    classified_report = run_dir / "classified_report_v3.json"
    report_model = run_dir / "report_model_v3.json"
    text_report = run_dir / "report_text_v3.txt"
    html_report = run_dir / "report_v3.html"
    pdf_report = html_report.with_suffix(".pdf")

    run_step("extract_water_data.py", str(pdf_path), str(water_report))
    run_step("classify_water_v3.py", str(water_report), str(classified_report))
    run_step(
        "build_report_model_v3.py",
        str(classified_report),
        str(HERE / "advice_rules.json"),
        str(report_model),
    )
    run_step("generate_text_report_v3.py", str(report_model), str(text_report))
    run_step("generate_html_report_v3.py", str(report_model), str(html_report))

    print()
    print("KLART ✅")
    print("Utmatningsmapp:", run_dir)
    print("HTML:", html_report)
    print("PDF:", pdf_report)
    print("TXT:", text_report)
    print("MODEL:", report_model)


if __name__ == "__main__":
    main()
