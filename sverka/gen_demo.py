"""Выдуманные выгрузки для пробы сверки: чеки ОФД, реестр эквайринга, выписка СБП.
Три магазина, 01.01-31.10.2026. В данные заложены ошибки, список сохраняется в truth.csv
для проверки сверки. Настоящих данных здесь нет."""
import random, csv, datetime as dt

random.seed(5529583)
STORES = [
    # магазин, РН ККТ, терминал, сдвиг часов терминала относительно кассы (сек), чеков в день
    ("Магазин 1", "0001234567012345", "T0011001", 0, 70),
    ("Магазин 2", "0001234567023456", "T0022002", 185, 60),     # часы терминала спешат на 3 минуты
    ("Магазин 3", "0001234567034567", "T0033003", -3600 + 40, 45),  # касса в другом часовом поясе
]
START, END = dt.date(2026, 1, 1), dt.date(2026, 10, 31)

receipts, acq, sbp, truth = [], [], [], []
fd = {s[0]: 0 for s in STORES}
rrn = 100000000000
sbp_id = 0


def price():
    return round(random.choice([random.uniform(80, 900), random.uniform(80, 900), random.uniform(900, 6000)]), 0) + random.choice([0, 0, 0, 0.5, 0.9])


def add_receipt(store, kkt, t, kind, cash, card):
    fd[store] += 1
    receipts.append([store, kkt, fd[store], t.strftime("%d.%m.%Y %H:%M:%S"), kind, f"{cash + card:.2f}", f"{cash:.2f}", f"{card:.2f}"])
    return fd[store]


def add_acq(store, term, t, kind, amount):
    global rrn
    rrn += random.randint(1, 9)
    acq.append([store, term, t.strftime("%Y-%m-%d %H:%M:%S"), kind, f"{amount:.2f}", f"{amount * 0.018:.2f}", str(rrn), f"{random.choice(['2200', '2202', '4276', '5536'])}****{random.randint(1000, 9999)}"])
    return rrn


def add_sbp(store, t, kind, amount):
    global sbp_id
    sbp_id += 1
    sbp.append([store, t.strftime("%d.%m.%Y %H:%M"), kind, f"{amount:.2f}", f"B{6000000000 + sbp_id}"])
    return sbp_id


d = START
while d <= END:
    for store, kkt, term, shift, per_day in STORES:
        n = int(per_day * random.uniform(0.7, 1.3))
        for _ in range(n):
            t = dt.datetime.combine(d, dt.time(9, 0)) + dt.timedelta(seconds=random.randint(0, 12 * 3600))
            a = price()
            way = random.choices(["cash", "card", "sbp"], [0.3, 0.55, 0.15])[0]
            bank_t = t + dt.timedelta(seconds=shift + random.randint(-25, 5))
            r = random.random()
            if way == "cash":
                add_receipt(store, kkt, t, "Приход", a, 0)
            elif r < 0.0030:   # ошибка 1: оплата картой или СБП пробита как наличные
                n_fd = add_receipt(store, kkt, t, "Приход", a, 0)
                ref = add_acq(store, term, bank_t, "Оплата", a) if way == "card" else add_sbp(store, bank_t, "Зачисление", a)
                truth.append([store, "Безналичная оплата пробита как наличные", n_fd, ref, a])
            elif r < 0.0048:   # ошибка 2: деньги в банк пришли, чека нет
                ref = add_acq(store, term, bank_t, "Оплата", a) if way == "card" else add_sbp(store, bank_t, "Зачисление", a)
                truth.append([store, "Оплата в банке без чека", "", ref, a])
            elif r < 0.0062:   # ошибка 3: чек пробит дважды, оплата одна
                n1 = add_receipt(store, kkt, t, "Приход", 0, a)
                n2 = add_receipt(store, kkt, t + dt.timedelta(seconds=random.randint(8, 50)), "Приход", 0, a)
                ref = add_acq(store, term, bank_t, "Оплата", a) if way == "card" else add_sbp(store, bank_t, "Зачисление", a)
                truth.append([store, "Дубль чека", n2, ref, a])
            elif r < 0.0074:   # ошибка 4: чек возврата без возврата денег в банке
                add_receipt(store, kkt, t, "Приход", 0, a)
                if way == "card":
                    add_acq(store, term, bank_t, "Оплата", a)
                else:
                    add_sbp(store, bank_t, "Зачисление", a)
                n2 = add_receipt(store, kkt, t + dt.timedelta(minutes=random.randint(2, 40)), "Возврат прихода", 0, a)
                truth.append([store, "Возврат по чеку без возврата денег", n2, "", a])
            elif r < 0.0084:   # ошибка 5: сумма чека не равна сумме оплаты
                wrong = round(a + random.choice([-100, -10, 10, 100, 1000]), 2)
                if wrong <= 0:
                    wrong = a + 10
                n_fd = add_receipt(store, kkt, t, "Приход", 0, wrong)
                ref = add_acq(store, term, bank_t, "Оплата", a) if way == "card" else add_sbp(store, bank_t, "Зачисление", a)
                truth.append([store, "Сумма чека не равна сумме оплаты", n_fd, ref, a])
            elif r < 0.0092:   # ошибка 6: безналичный чек, денег в банке нет
                n_fd = add_receipt(store, kkt, t, "Приход", 0, a)
                truth.append([store, "Безналичный чек без оплаты в банке", n_fd, "", a])
            else:              # норма
                add_receipt(store, kkt, t, "Приход", 0, a)
                if way == "card":
                    add_acq(store, term, bank_t, "Оплата", a)
                else:
                    add_sbp(store, bank_t, "Зачисление", a)
                if random.random() < 0.004:   # честный возврат: чек возврата и возврат в банке
                    t2 = t + dt.timedelta(minutes=random.randint(3, 90))
                    add_receipt(store, kkt, t2, "Возврат прихода", 0, a)
                    b2 = t2 + dt.timedelta(seconds=shift + random.randint(-25, 5))
                    if way == "card":
                        add_acq(store, term, b2, "Возврат", a)
                    else:
                        add_sbp(store, b2, "Возврат", a)
    d += dt.timedelta(days=1)

random.shuffle(acq)
with open("demo_ofd_cheki.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Торговая точка", "РН ККТ", "Номер ФД", "Дата и время", "Признак расчёта", "Итог", "Наличными", "Безналичными"])
    w.writerows(receipts)
with open("demo_ekvairing.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Точка", "Терминал", "Дата операции", "Тип операции", "Сумма", "Комиссия", "RRN", "Карта"])
    w.writerows(acq)
with open("demo_sbp.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Точка", "Дата", "Операция", "Сумма", "Идентификатор СБП"])
    w.writerows(sbp)
with open("truth.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Магазин", "Заложенная ошибка", "Номер ФД", "RRN или номер СБП", "Сумма"])
    w.writerows(truth)
print("чеков", len(receipts), "эквайринг", len(acq), "СБП", len(sbp), "заложено ошибок", len(truth))
