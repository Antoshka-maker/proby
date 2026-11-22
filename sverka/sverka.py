"""Сверка кассовых чеков ОФД с эквайрингом и СБП.
Вход: выгрузка чеков ОФД, реестр эквайринга, выписка СБП (CSV).
Выход: Excel-реестр расхождений: подтверждённые ошибки отдельно от спорных.

Порядок:
1. По каждому магазину и каналу находит сдвиг часов между кассой и банком.
2. Сопоставляет безналичные чеки с операциями банка один к одному: та же сумма,
   ближайшее время с учётом сдвига.
3. Всё, что осталось без пары, разбирает по типам ошибок и пишет основание.
"""
import sys, time, bisect, collections
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

WINDOW = {"Эквайринг": 60, "СБП": 100}   # допуск по времени после поправки на сдвиг, сек
NEAR = 180                                # окно поиска «соседних» чеков для разбора остатков, сек
REFUND_DAYS = 14                          # сколько дней ждать возврат денег в банке


def load(ofd, acq, sbp):
    r = pd.read_csv(ofd, sep=";", dtype=str)
    r = pd.DataFrame({
        "store": r["Торговая точка"], "fd": r["Номер ФД"].astype(int),
        "t": pd.to_datetime(r["Дата и время"], format="%d.%m.%Y %H:%M:%S"),
        "kind": r["Признак расчёта"], "total": r["Итог"].astype(float),
        "cash": r["Наличными"].astype(float), "card": r["Безналичными"].astype(float)})
    a = pd.read_csv(acq, sep=";", dtype=str)
    a = pd.DataFrame({
        "store": a["Точка"], "t": pd.to_datetime(a["Дата операции"]),
        "kind": a["Тип операции"].map({"Оплата": "pay", "Возврат": "refund"}),
        "amount": a["Сумма"].astype(float), "ref": a["RRN"], "channel": "Эквайринг"})
    s = pd.read_csv(sbp, sep=";", dtype=str)
    s = pd.DataFrame({
        "store": s["Точка"], "t": pd.to_datetime(s["Дата"], format="%d.%m.%Y %H:%M") + pd.Timedelta(seconds=30),
        "kind": s["Операция"].map({"Зачисление": "pay", "Возврат": "refund"}),
        "amount": s["Сумма"].astype(float), "ref": s["Идентификатор СБП"], "channel": "СБП"})
    b = pd.concat([a, s], ignore_index=True)
    r["ts"] = ((r["t"] - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).astype("int64")
    b["ts"] = ((b["t"] - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).astype("int64")
    r["kop"] = (r["card"] * 100).round().astype(int)
    b["kop"] = (b["amount"] * 100).round().astype(int)
    return r, b


def clock_shift(rec, bank):
    """Сдвиг часов банка относительно кассы: самая частая разница времени у пар с равной суммой."""
    by_amount = collections.defaultdict(list)
    for ts, kop in zip(rec["ts"], rec["kop"]):
        by_amount[kop].append(ts)
    for v in by_amount.values():
        v.sort()
    diffs = []
    for ts, kop in zip(bank["ts"], bank["kop"]):
        lst = by_amount.get(kop)
        if not lst:
            continue
        i = bisect.bisect_left(lst, ts - 7200)
        while i < len(lst) and lst[i] <= ts + 7200:
            diffs.append(ts - lst[i])
            i += 1
    if not diffs:
        return 0, 0
    hist = collections.Counter(d // 20 for d in diffs)
    top = hist.most_common(1)[0][0] * 20
    near = sorted(d for d in diffs if top - 60 <= d <= top + 80)
    return int(near[len(near) // 2]), len(near)


def match(rec, bank, shift, window):
    """Пары один к одному: равная сумма, минимальная разница времени в пределах окна."""
    pairs = []
    by_amount = collections.defaultdict(list)
    for idx, ts, kop in zip(rec.index, rec["ts"], rec["kop"]):
        by_amount[kop].append((ts, idx))
    for v in by_amount.values():
        v.sort()
    cand = []
    for bidx, ts, kop in zip(bank.index, bank["ts"], bank["kop"]):
        lst = by_amount.get(kop)
        if not lst:
            continue
        want = ts - shift
        i = bisect.bisect_left(lst, (want - window, -1))
        while i < len(lst) and lst[i][0] <= want + window:
            cand.append((abs(lst[i][0] - want), lst[i][1], bidx))
            i += 1
    cand.sort()
    used_r, used_b = set(), set()
    for d, ridx, bidx in cand:
        if ridx in used_r or bidx in used_b:
            continue
        used_r.add(ridx)
        used_b.add(bidx)
        pairs.append((ridx, bidx))
    return pairs


def run(ofd, acq, sbp, out):
    t0 = time.time()
    rec, bank = load(ofd, acq, sbp)
    rec["pair"] = -1
    bank["pair"] = -1
    shifts = []
    for store in sorted(rec["store"].unique()):
        for channel in ("Эквайринг", "СБП"):
            b = bank[(bank.store == store) & (bank.channel == channel)]
            r = rec[(rec.store == store) & (rec.card > 0)]
            sh, n = clock_shift(r[r.kind == "Приход"], b[b.kind == "pay"])
            shifts.append([store, channel, sh, n])
            for rk, bk in (("Приход", "pay"), ("Возврат прихода", "refund")):
                rr = r[(r.kind == rk) & (rec.loc[r.index, "pair"] == -1)]
                bb = b[b.kind == bk]
                for ridx, bidx in match(rr, bb, sh, WINDOW[channel]):
                    rec.at[ridx, "pair"] = bidx
                    bank.at[bidx, "pair"] = ridx
    shift_of = {(s, c): v for s, c, v, _ in shifts}

    sure, doubt = [], []

    def row(store, kind, r=None, b=None, why="", todo=""):
        d = ""
        if r is not None and b is not None:
            d = int(b.ts - shift_of[(store, b.channel)] - r.ts)
        return [store, kind,
                r.t if r is not None else None, int(r.fd) if r is not None else None,
                ("наличные" if r.cash > 0 else "безналичные") if r is not None else "",
                (r.total if r.kind == "Приход" else -r.total) if r is not None else None,
                b.t if b is not None else None, b.channel if b is not None else "",
                b.ref if b is not None else "",
                (b.amount if b.kind == "pay" else -b.amount) if b is not None else None,
                d, why, todo]

    free_r = rec[rec.pair == -1]
    free_b = bank[bank.pair == -1]
    taken_r = set()

    # 1. Оплаты в банке без безналичного чека
    for store, grp in free_b[free_b.kind == "pay"].groupby("store"):
        R = rec[rec.store == store]
        Rts = R["ts"].values
        order = Rts.argsort()
        Rs = R.iloc[order]
        ts_sorted = Rs["ts"].values
        for b in grp.itertuples():
            want = b.ts - shift_of[(store, b.channel)]
            lo, hi = bisect.bisect_left(ts_sorted, want - NEAR), bisect.bisect_right(ts_sorted, want + NEAR)
            near = Rs.iloc[lo:hi]
            near = near[(near.pair == -1) & (near.kind == "Приход") & (~near.index.isin(taken_r))]
            cash_same = near[(near.card == 0) & ((near.cash * 100).round() == b.kop)]
            card_other = near[(near.card > 0)]
            if len(cash_same) >= 1:
                c = cash_same.iloc[(cash_same.ts - want).abs().argsort()].iloc[0]
                taken_r.add(c.name)
                line = row(store, "Безналичная оплата пробита как наличные", c, b,
                           f"Банк получил {b.amount:.2f} ₽ ({b.channel}), безналичного чека на эту сумму нет, "
                           f"в то же время пробит чек наличными на ту же сумму",
                           "Исправить форму оплаты в чеке: наличные заменить на безналичные")
                (sure if len(cash_same) == 1 else doubt).append(line)
            elif len(card_other) >= 1:
                c = card_other.iloc[(card_other.ts - want).abs().argsort()].iloc[0]
                taken_r.add(c.name)
                line = row(store, "Сумма чека не равна сумме оплаты", c, b,
                           f"Безналичный чек на {c.total:.2f} ₽ и оплата в банке на {b.amount:.2f} ₽ "
                           f"в одно время, других пар для них нет",
                           f"Исправить сумму в чеке на {b.amount:.2f} ₽ или выяснить, какая сумма верная")
                (sure if len(card_other) == 1 and abs(c.ts - want) <= WINDOW[b.channel] else doubt).append(line)
            else:
                sure.append(row(store, "Оплата в банке без чека", None, b,
                                f"Банк получил {b.amount:.2f} ₽ ({b.channel}), в пределах {NEAR // 60} минут "
                                f"нет ни одного чека без пары",
                                "Пробить чек коррекции прихода на эту сумму, оплата безналичными"))

    # 2. Безналичные чеки без оплаты в банке
    for store, grp in free_r[(free_r.kind == "Приход") & (free_r.card > 0)].groupby("store"):
        R = rec[(rec.store == store) & (rec.kind == "Приход") & (rec.card > 0)].sort_values("ts")
        ts_sorted = R["ts"].values
        for r in grp.itertuples():
            if r.Index in taken_r:
                continue
            lo, hi = bisect.bisect_left(ts_sorted, r.ts - 120), bisect.bisect_right(ts_sorted, r.ts + 120)
            twins = R.iloc[lo:hi]
            twins = twins[(twins.kop == r.kop) & (twins.index != r.Index) & (twins.pair != -1)]
            rr = rec.loc[r.Index]
            if len(twins) >= 1:
                tw = twins.iloc[0]
                b = bank.loc[tw.pair]
                sure.append(row(store, "Дубль чека", rr, b,
                                f"Два безналичных чека на {r.total:.2f} ₽ с разницей {abs(int(tw.ts - r.ts))} сек "
                                f"(ФД {int(tw.fd)} и ФД {int(r.fd)}), оплата в банке одна",
                                "Лишний чек сторнировать: чек возврата прихода или чек коррекции"))
            else:
                doubt.append(row(store, "Безналичный чек без оплаты в банке", rr, None,
                                 f"Чек на {r.total:.2f} ₽ безналичными, в банке за это время нет оплаты на эту сумму "
                                 f"ни по эквайрингу, ни по СБП",
                                 "Проверить: оплата наличными, другой терминал или несостоявшаяся оплата"))

    # 3. Возвраты
    pays = bank[bank.kind == "refund"]
    for r in free_r[(free_r.kind == "Возврат прихода") & (free_r.card > 0)].itertuples():
        later = pays[(pays.store == r.store) & (pays.kop == r.kop) & (pays.pair == -1) &
                     (pays.ts >= r.ts - 3600) & (pays.ts <= r.ts + REFUND_DAYS * 86400)]
        rr = rec.loc[r.Index]
        if len(later):
            b = later.iloc[0]
            bank.at[b.name, "pair"] = r.Index
            doubt.append(row(r.store, "Возврат денег в банке позже чека возврата", rr, b,
                             f"Чек возврата на {r.total:.2f} ₽, деньги в банке возвращены {b.t:%d.%m.%Y %H:%M}",
                             "Ошибки, скорее всего, нет: банк провёл возврат с задержкой"))
        else:
            sure.append(row(r.store, "Возврат по чеку без возврата денег в банке", rr, None,
                            f"Чек возврата прихода на {r.total:.2f} ₽ безналичными, возврата в банке на эту сумму "
                            f"нет в течение {REFUND_DAYS} дней",
                            "Если деньги покупателю не возвращались: сторнировать чек возврата"))
    for b in bank[(bank.kind == "refund") & (bank.pair == -1)].itertuples():
        sure.append(row(b.store, "Возврат денег в банке без чека возврата", None, bank.loc[b.Index],
                        f"Банк вернул покупателю {b.amount:.2f} ₽ ({b.channel}), чека возврата прихода нет",
                        "Пробить чек возврата прихода (или чек коррекции) на эту сумму"))

    write_xlsx(out, rec, bank, shifts, sure, doubt, time.time() - t0)
    return rec, bank, shifts, sure, doubt


HEAD = ["Магазин", "Тип расхождения", "Чек: дата и время", "Номер ФД", "Чек: форма оплаты", "Чек: сумма, ₽",
        "Банк: дата и время", "Канал", "RRN или номер СБП", "Банк: сумма, ₽", "Разница времени после поправки, сек",
        "Основание", "Что сделать"]
WIDTH = [12, 34, 19, 10, 14, 13, 19, 12, 16, 13, 14, 70, 52]


def sheet(ws, rows):
    thin = Side(style="thin", color="D0D5DD")
    ws.append(HEAD)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3A5F")
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[1].height = 45
    for r in sorted(rows, key=lambda x: (x[0], x[1], str(x[2] or x[6]))):
        ws.append(r)
    for i, w in enumerate(WIDTH, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row_ in ws.iter_rows(min_row=2):
        for c in row_:
            c.border = Border(bottom=thin)
            c.alignment = Alignment(vertical="top", wrap_text=c.column >= 12)
            if c.column in (3, 7) and c.value is not None:
                c.number_format = "DD.MM.YYYY HH:MM:SS"
            if c.column in (6, 10) and c.value is not None:
                c.number_format = "#,##0.00"
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions


def write_xlsx(out, rec, bank, shifts, sure, doubt, sec):
    wb = Workbook()
    ws = wb.active
    ws.title = "Сводка"
    bold = Font(bold=True)
    ws.append(["Сверка чеков ОФД с эквайрингом и СБП"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([f"Период: {rec.t.min():%d.%m.%Y} - {rec.t.max():%d.%m.%Y}. Время расчёта: {sec:.0f} сек"])
    ws.append([])
    ws.append(["Магазин", "Чеков всего", "Безналичных чеков", "Операций эквайринга", "Операций СБП",
               "Сошлось пар", "Подтверждённых ошибок", "Требуют проверки", "Сумма подтверждённых, ₽"])
    for c in ws[4]:
        c.font = bold
        c.fill = PatternFill("solid", fgColor="E8EEF5")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    stores = sorted(rec.store.unique())
    for s in stores + ["Итого"]:
        m = (rec.store == s) if s != "Итого" else (rec.store == rec.store)
        mb = (bank.store == s) if s != "Итого" else (bank.store == bank.store)
        ss = [x for x in sure if s == "Итого" or x[0] == s]
        dd = [x for x in doubt if s == "Итого" or x[0] == s]
        ws.append([s, int(m.sum()), int((m & (rec.card > 0)).sum()), int((mb & (bank.channel == "Эквайринг")).sum()),
                   int((mb & (bank.channel == "СБП")).sum()), int((m & (rec.pair != -1)).sum()), len(ss), len(dd),
                   round(sum(abs(x[9] if x[9] is not None else x[5]) for x in ss), 2)])
    for c in ws[ws.max_row]:
        c.font = bold
    ws.append([])
    ws.append(["Тип расхождения", "Подтверждено", "Требует проверки"])
    for c in ws[ws.max_row]:
        c.font = bold
        c.fill = PatternFill("solid", fgColor="E8EEF5")
    kinds = collections.Counter(x[1] for x in sure), collections.Counter(x[1] for x in doubt)
    for k in sorted(set(kinds[0]) | set(kinds[1])):
        ws.append([k, kinds[0].get(k, 0), kinds[1].get(k, 0)])
    ws.append([])
    ws.append(["Сдвиг часов между кассой и банком (найден по данным)"])
    ws[f"A{ws.max_row}"].font = bold
    ws.append(["Магазин", "Канал", "Банк впереди кассы, сек", "Пар, по которым найден"])
    for c in ws[ws.max_row]:
        c.font = bold
        c.fill = PatternFill("solid", fgColor="E8EEF5")
    for s in shifts:
        ws.append(s)
    ws.column_dimensions["A"].width = 44
    for col in "BCDEFGHI":
        ws.column_dimensions[col].width = 18
    ws.row_dimensions[4].height = 32
    sheet(wb.create_sheet("Подтверждённые ошибки"), sure)
    sheet(wb.create_sheet("Требуют проверки"), doubt)
    wb.save(out)


if __name__ == "__main__":
    rec, bank, shifts, sure, doubt = run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print("чеков", len(rec), "операций банка", len(bank), "подтверждено", len(sure), "спорных", len(doubt))
    for s in shifts:
        print(s)
