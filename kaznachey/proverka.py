"""Проверка бота-казначея на выдуманном классе: события в формате MAX, без сети.

Запуск: python3 proverka.py            (проверки)
        python3 proverka.py dialog.json (ещё и записать диалог для картинки)
"""
import datetime as dt
import json
import sys

from kaznachey import Kaznachey, parse_date, parse_money, rub
from max_bot import to_body

T, P1, P2, P3 = 100, 201, 202, 203          # казначей и трое родителей
NAMES = {T: "Ольга", P1: "Марина", P2: "Сергей", P3: "Анна"}
bot = Kaznachey(today=dt.date(2026, 11, 18), bot_name="se12345_bot")
log, n_cb = [], 0


def show(who, kind, text, outs):
    log.append({"from": who, "kind": kind, "text": text})
    for o in outs:
        if o.get("callback_id"):
            continue
        to_body(o)                                           # тело запроса к MAX собирается без ошибок
        assert len(o["text"]) <= 4000
        log.append({"to": o["user_id"], "text": o["text"], "buttons": [[b[0] for b in r] for r in o["buttons"]], "photos": o["photos"]})
    return [o for o in outs if not o.get("callback_id")]


def start(uid, payload=""):
    return show(uid, "start", payload, bot.handle({"update_type": "bot_started", "timestamp": 0, "chat_id": uid,
                                                    "user": {"user_id": uid, "first_name": NAMES[uid], "is_bot": False}, "payload": payload}))


def say(uid, text, photo=None):
    body = {"mid": "m", "seq": 1, "text": text}
    if photo:
        body["attachments"] = [{"type": "image", "payload": {"photo_id": 1, "token": "t", "url": photo}}]
    return show(uid, "text", text + (" [фото]" if photo else ""), bot.handle({
        "update_type": "message_created", "timestamp": 0,
        "message": {"sender": {"user_id": uid, "first_name": NAMES[uid], "is_bot": False},
                    "recipient": {"chat_type": "dialog", "user_id": 1}, "timestamp": 0, "body": body}}))


def press(uid, outs, label):
    """Нажать кнопку с подписью label в одном из сообщений outs."""
    global n_cb
    n_cb += 1
    payload = next(p for o in outs for r in o["buttons"] for t, p in r if t.startswith(label))
    return show(uid, "button", label, bot.handle({"update_type": "message_callback", "timestamp": 0,
                                                  "callback": {"timestamp": 0, "callback_id": f"cb{n_cb}", "payload": payload,
                                                               "user": {"user_id": uid, "first_name": NAMES[uid], "is_bot": False}}}))


def to(outs, uid):
    return [o for o in outs if o["user_id"] == uid]


# --- мелкие разборы ---
assert parse_money("1 500") == 150000 and parse_money("500,5") == 50050 and parse_money("500р") == 50000 and parse_money("abc") is None
assert rub(150000) == "1 500 ₽" and rub(50050) == "500,50 ₽"
d = dt.date(2026, 11, 18)
assert parse_date("25.11", d) == "2026-11-25" and parse_date("5 января", d) == "2027-01-05"
assert parse_date("25-го", d) == "2026-11-25" and parse_date("10", d) == "2026-12-10" and parse_date("32.13", d) is None

# --- казначей заводит класс ---
o = start(T)
assert "Как назвать" in o[0]["text"]
o = say(T, "3Б, школа 12")
assert "Пришлите список детей" in o[0]["text"]
o = say(T, "1. Иванов Петя\n2. Иванова Маша\n3. Петрова Аня\n4. Сидоров Коля\n5. Ёлкин Дима")
assert "всего в списке 5" in o[0]["text"]
o = say(T, "сбор экскурсия в планетарий по 500 до 25.11")
assert "по 500 ₽ до 25.11" in o[0]["text"] and "2 500 ₽ с 5 детей" in o[0]["text"]
link = o[1]["text"].split()[-1]
assert link.startswith("https://max.ru/se12345_bot?start=k") and len(link.split("start=")[1]) <= 128
code = link.split("start=")[1]

# --- казначей отмечает сам ---
o = say(T, "сдали Петрова, елкин")
assert "Петрова Аня: 500 ₽" in o[0]["text"] and "Ёлкин Дима: 500 ₽" in o[0]["text"] and "Сдали 2 из 5" in o[0]["text"]
o = say(T, "сдал Иванов")                                   # двое подходят: бот спрашивает
assert "кто именно" in o[0]["text"] and len(o[0]["buttons"]) == 2
o = press(T, o, "Иванова Маша")
assert "Иванова Маша: 500 ₽" in o[0]["text"] and "Сдали 3 из 5" in o[0]["text"]
o = say(T, "Сидоров 200")                                   # частичный взнос
assert "Сидоров Коля: 200 ₽, осталось 300 ₽" in o[0]["text"] and "Сдали 3 из 5, собрано 1 700 ₽" in o[0]["text"]
o = say(T, "сдал Кузнецов")
assert "не нашёл" in o[0]["text"]

# --- родитель заходит по ссылке и отмечается ---
o = start(P1, code)
assert "Чей вы родитель" in o[0]["text"] and sum(len(r) for r in o[0]["buttons"]) == 5
o = press(P1, o, "Иванов Петя")
assert "▫️ Экскурсия в планетарий: 500 ₽ до 25.11" in o[0]["text"]
o = press(P1, o, "Я перевёл")
assert "Передал казначею" in to(o, P1)[0]["text"] and "Иванов Петя: родитель (Марина)" in to(o, T)[0]["text"]
o2 = press(T, to(o, T), "Да, пришли")
assert "Сдали 4 из 5" in to(o2, T)[0]["text"] and "Казначей подтвердил" in to(o2, P1)[0]["text"]

# --- второй родитель: казначей не видит перевод ---
o = start(P2, code)
o = press(P2, o, "Сидоров Коля")
assert "Экскурсия в планетарий: 300 ₽" in o[0]["text"]       # с учётом уже сданных 200
o = press(P2, o, "Я перевёл")
o2 = press(T, to(o, T), "Нет")
assert "не видит перевод" in to(o2, P2)[0]["text"]
assert "Сдали 4 из 5, собрано 2 200 ₽" in say(T, "отчёт")[0]["text"]   # частичные 200 не потерялись

# --- расходы и отчёт ---
o = say(T, "расход 1800 билеты в планетарий", photo="https://example.org/chek1.jpg")
assert "1 800 ₽, билеты в планетарий, чек приложен. Остаток 400 ₽" in o[0]["text"]
o = say(T, "купили воду 150")
assert "150 ₽, воду, без чека. Остаток 250 ₽" in o[0]["text"]
o = say(T, "отчёт")
r = o[0]["text"]
assert "Собрано: 2 200 ₽" in r and "Потрачено: 1 950 ₽" in r and "Остаток: 250 ₽" in r and "• Сидоров Коля" in r
assert o[0]["photos"] == ["https://example.org/chek1.jpg"]
o = press(P1, start(P1, code), "Отчёт по деньгам")
assert "Остаток: 250 ₽" in o[0]["text"] and "Сидоров" not in o[0]["text"]   # родителям фамилии должников не видны

# --- напоминание ---
o = say(T, "напомнить")
assert "Отправил напоминаний: 1" in to(o, T)[0]["text"] and "сбор «Экскурсия в планетарий», 300 ₽ до 25.11" in to(o, P2)[0]["text"]
o = press(P2, to(o, P2), "Я перевёл")
o2 = press(T, to(o, T), "Да, пришли")
assert "Сдали 5 из 5, собрано 2 500 ₽" in to(o2, T)[0]["text"]
assert "сдали все" in say(T, "должники")[0]["text"]

# --- чужие не видят и не правят ---
assert press(P3, [{"buttons": [[("Отчёт", f"p:otchet:1")]]}], "Отчёт") == []          # не из класса
assert press(P3, [{"buttons": [[("Да", "t:yes:1:1")]]}], "Да") == []                  # не казначей
assert "Ссылка устарела" in start(P3, "kНЕТТАКОГО")[0]["text"]
# сообщение из общего чата бот не трогает
assert bot.handle({"update_type": "message_created", "timestamp": 0, "message": {
    "sender": {"user_id": P3, "first_name": "Анна", "is_bot": False}, "recipient": {"chat_type": "chat", "chat_id": 5},
    "timestamp": 0, "body": {"mid": "m", "seq": 1, "text": "отчёт"}}}) == []

print("Все проверки прошли, сообщений в диалоге:", len(log))
if len(sys.argv) > 1:
    json.dump({"names": NAMES, "log": log}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
