@echo off
cd /d "%~dp0"

python run_water_report_pipeline.py "%~1"

pause