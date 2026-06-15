UPPDATERINGAR

1. Filerna har döpts om till produktionsnamn utan versionssuffix.
2. build_report_model_v3.py har fått kombinationsregler:
   - Järn + mangan
   - Natrium + klorid
   - Aluminium + lågt pH
   - Koliforma bakterier + nitrat
   - Nitrat + nitrit
   - Flera avvikande parametrar samtidigt
3. advice_rules.json har uppdaterats/skärpts för:
   - Fluorid
   - Uran
   - Aluminium
   - Nitrat
   - Mangan
   - Järn
   - Klorid
   - Radon
   - E. coli
4. Koden är syntaxtestad med python -m py_compile *.py.

KÖRNING
python run_water_report_pipeline.py "sökväg/till/labbrapport.pdf"

VIKTIGT
Börja gärna med manuell snabbgranskning innan kundutskick tills systemet testats på ett större antal riktiga rapporter.
