"""Проверка сверки на выдуманных данных: сколько заложенных ошибок найдено и сколько лишних."""
import csv, collections
from openpyxl import load_workbook

truth = list(csv.DictReader(open("truth.csv", encoding="utf-8-sig"), delimiter=";"))
wb = load_workbook("reestr-proba.xlsx")
found = []
for name in ("Подтверждённые ошибки", "Требуют проверки"):
    for r in list(wb[name].iter_rows(values_only=True))[1:]:
        found.append((name, r[0], r[1], r[3], str(r[8] or "")))

MAP = {"Возврат по чеку без возврата денег": "Возврат по чеку без возврата денег в банке"}
by_fd = {(f[1], f[3]): f for f in found if f[3] is not None}
by_ref = {(f[1], f[4].lstrip("B")): f for f in found if f[4]}
stat = collections.defaultdict(lambda: [0, 0, 0, 0])   # всего, найдено в подтверждённых, в спорных, тип совпал
hit = set()
for t in truth:
    kind = MAP.get(t["Заложенная ошибка"], t["Заложенная ошибка"])
    f = None
    if t["Номер ФД"]:
        f = by_fd.get((t["Магазин"], int(t["Номер ФД"])))
    if f is None and t["RRN или номер СБП"]:
        ref = t["RRN или номер СБП"]
        f = by_ref.get((t["Магазин"], ref)) or by_ref.get((t["Магазин"], str(6000000000 + int(ref)))) if len(ref) < 12 else by_ref.get((t["Магазин"], ref))
    s = stat[kind]
    s[0] += 1
    if f:
        hit.add(f)
        s[1 if f[0] == "Подтверждённые ошибки" else 2] += 1
        s[3] += f[2] == kind
print(f"{'Заложенная ошибка':48} всего  подтв  спорн  тип верный")
for k, s in sorted(stat.items()):
    print(f"{k:48} {s[0]:5} {s[1]:6} {s[2]:6} {s[3]:6}")
tot = [sum(s[i] for s in stat.values()) for i in range(4)]
print(f"{'Итого':48} {tot[0]:5} {tot[1]:6} {tot[2]:6} {tot[3]:6}")
extra = [f for f in found if f not in hit]
print("Строк в реестре:", len(found), "из них не связаны с заложенными ошибками:", len(extra))
for f in extra[:15]:
    print("  лишняя:", f)
