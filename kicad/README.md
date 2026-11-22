# CSV → KiCad → Gerber

`csv2kicad.py` читает таблицу с линиями, дугами и окружностями (`primer.csv`), строит дорожки и отверстия на плате через Python API KiCad (pcbnew) и выгружает Gerber (F_Cu, Edge_Cuts) и сверловку Excellon.

```
python csv2kicad.py primer.csv primer.kicad_pcb --gerber gerber/
```

Проверено в KiCad 7. Параметры запуска: `python csv2kicad.py -h`.
