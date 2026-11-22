"""Бот-казначей родительского чата: логика без привязки к мессенджеру.

Бот работает только в личных диалогах. В общий чат его добавлять не нужно:
казначей пересылает в чат готовый текст со ссылкой, родители заходят по ней.

Kaznachey.handle(update) принимает событие в формате MAX Bot API
(message_created, message_callback, bot_started) и возвращает список исходящих
сообщений: {"user_id", "text", "buttons", "callback_id", "notification"}.
Деньги хранятся в копейках. Только стандартная библиотека Python.
"""
import datetime as dt
import json
import re
import secrets
import sqlite3

SCHEMA = """
create table if not exists klass(id integer primary key, code text unique, title text, treasurer integer, created text);
create table if not exists child(id integer primary key, klass integer, name text);
create table if not exists parent(user_id integer, klass integer, child integer, first_name text, primary key(user_id, klass));
create table if not exists sbor(id integer primary key, klass integer, title text, amount integer, deadline text, closed integer default 0, created text);
create table if not exists vznos(sbor integer, child integer, amount integer, status text, ts text, primary key(sbor, child));
create table if not exists rashod(id integer primary key, klass integer, title text, amount integer, photo text, ts text);
create table if not exists state(user_id integer primary key, klass integer, step text, data text);
"""

HELP_T = ("Что я умею:\n"
          "• сбор экскурсия 500 до 25.11\n"
          "• сдал Иванов (или: сдали Иванов, Петрова; или: Иванов 300)\n"
          "• расход 3200 автобус (можно с фото чека)\n"
          "• отчёт, должники, напомнить\n"
          "• дети (показать или дополнить список)")


def rub(kop):
    """Сумма в копейках -> «1 500 ₽» или «1 500,50 ₽»."""
    r, k = divmod(abs(kop), 100)
    s = f"{r:,}".replace(",", " ") + (f",{k:02d}" if k else "")
    return ("−" if kop < 0 else "") + s + " ₽"


def parse_money(s):
    """«1 500», «500,50», «500р» -> копейки или None."""
    m = re.fullmatch(r"\s*(\d[\d  ]*)(?:[.,](\d{1,2}))?\s*(?:₽|р\.?|руб\.?|рублей)?\s*", s, re.I)
    if not m:
        return None
    r = int(re.sub(r"[  ]", "", m.group(1)))
    k = int((m.group(2) or "0").ljust(2, "0"))
    return r * 100 + k


MONEY = r"(\d[\d  ]*(?:[.,]\d{1,2})?)\s*(?:₽|р\.?|руб\.?|рублей)?"


def parse_date(s, today):
    """«25.11», «25.11.2026», «25 ноября» -> дата ISO; год подбирается ближайший вперёд."""
    months = "янв фев мар апр мая июн июл авг сен окт ноя дек".split()
    m = re.fullmatch(r"\s*(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\s*", s)
    bare = re.fullmatch(r"\s*(\d{1,2})(?:-?го)?(?:\s+числа)?\s*", s, re.I)
    if bare:
        d = int(bare.group(1))
        for add in (0, 1):
            y, mo = divmod(today.month - 1 + add, 12)
            try:
                c = dt.date(today.year + y, mo + 1, d)
            except ValueError:
                continue
            if c >= today:
                return c.isoformat()
        return None
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    else:
        m = re.fullmatch(r"\s*(\d{1,2})(?:-?го)?\s+([а-яё]+)\s*", s, re.I)
        if not m:
            return None
        key = m.group(2).lower()[:3].replace("май", "мая")
        if key not in months:
            return None
        d, mo, y = int(m.group(1)), months.index(key) + 1, None
    try:
        if y:
            y = int(y) + (2000 if len(y) == 2 else 0)
            return dt.date(y, mo, d).isoformat()
        c = dt.date(today.year, mo, d)
        if c < today:
            c = dt.date(today.year + 1, mo, d)
        return c.isoformat()
    except ValueError:
        return None


def ddmm(iso):
    return dt.date.fromisoformat(iso).strftime("%d.%m") if iso else ""


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower().replace("ё", "е"))


class Kaznachey:
    def __init__(self, db_path=":memory:", bot_name="kaznachey_bot", today=None):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.bot_name = bot_name
        self._today = today

    # ---------- служебное ----------
    def today(self):
        return self._today or dt.date.today()

    def now(self):
        return dt.datetime.now().isoformat(timespec="seconds")

    def q(self, sql, *a):
        return self.db.execute(sql, a).fetchall()

    def one(self, sql, *a):
        return self.db.execute(sql, a).fetchone()

    def run(self, sql, *a):
        cur = self.db.execute(sql, a)
        self.db.commit()
        return cur.lastrowid

    def state(self, uid):
        r = self.one("select * from state where user_id=?", uid)
        return (r["klass"], r["step"], json.loads(r["data"] or "{}")) if r else (None, None, {})

    def set_state(self, uid, klass=None, step=None, data=None):
        self.run("insert or replace into state values(?,?,?,?)", uid, klass, step, json.dumps(data or {}, ensure_ascii=False))

    def link(self, code):
        return f"https://max.ru/{self.bot_name}?start=k{code}"

    @staticmethod
    def msg(uid, text, buttons=None, photos=None):
        return {"user_id": uid, "text": text, "buttons": buttons or [], "photos": photos or []}

    def menu(self):
        return [[("Новый сбор", "t:sbor"), ("Отчёт", "t:otchet")],
                [("Должники", "t:dolg"), ("Напомнить", "t:napom")],
                [("Записать расход", "t:rashod"), ("Ссылка для чата", "t:link")]]

    # ---------- вход ----------
    def handle(self, u):
        t = u.get("update_type")
        if t == "bot_started":
            user = u.get("user") or {}
            return self.on_start(user.get("user_id"), user.get("first_name") or "", u.get("payload") or "")
        if t == "message_callback":
            cb = u.get("callback") or {}
            user = cb.get("user") or {}
            out = self.on_button(user.get("user_id"), user.get("first_name") or "", cb.get("payload") or "")
            return [{"callback_id": cb.get("callback_id"), "notification": "Готово"}] + out
        if t == "message_created":
            m = u.get("message") or {}
            if (m.get("recipient") or {}).get("chat_type") != "dialog":
                return []                      # в общих чатах бот молчит
            sender = m.get("sender") or {}
            if sender.get("is_bot"):
                return []
            body = m.get("body") or {}
            photo = next((a.get("payload", {}).get("url") for a in body.get("attachments") or []
                          if a.get("type") == "image"), None)
            return self.on_text(sender.get("user_id"), sender.get("first_name") or "", body.get("text") or "", photo)
        return []

    # ---------- старт и ссылка для родителей ----------
    def on_start(self, uid, name, payload):
        if payload.startswith("k"):
            k = self.one("select * from klass where code=?", payload[1:])
            if not k:
                return [self.msg(uid, "Ссылка устарела. Попросите у казначея новую")]
            if k["treasurer"] == uid:
                self.set_state(uid, k["id"])
                return [self.msg(uid, f"Это ваш класс «{k['title']}»", self.menu())]
            return self.parent_home(uid, name, k)
        mine = self.one("select * from klass where treasurer=? order by id desc", uid)
        if mine:
            self.set_state(uid, mine["id"])
            return [self.msg(uid, f"Класс «{mine['title']}». " + HELP_T, self.menu())]
        self.set_state(uid, None, "klass_title")
        return [self.msg(uid, "Здравствуйте! Я веду сборы класса: кто сдал, на что потратили, сколько осталось. "
                              "Деньги я не принимаю, их по-прежнему переводят вам.\n\n"
                              "Как назвать класс или группу? Например: 3Б, школа 12")]

    def parent_home(self, uid, name, k):
        p = self.one("select * from parent where user_id=? and klass=?", uid, k["id"])
        if not p:
            kids = self.q("select * from child where klass=? order by name", k["id"])
            if not kids:
                self.set_state(uid, k["id"], "parent_child")
                return [self.msg(uid, f"Класс «{k['title']}». Напишите фамилию и имя ребёнка")]
            rows = [[(c["name"], f"p:child:{k['id']}:{c['id']}") for c in kids[i:i + 2]] for i in range(0, len(kids), 2)]
            return [self.msg(uid, f"Класс «{k['title']}». Чей вы родитель?", rows)]
        self.set_state(uid, k["id"])
        child = self.one("select * from child where id=?", p["child"])
        lines, rows = [f"{k['title']}, {child['name']}"], []
        for s in self.q("select * from sbor where klass=? and closed=0 order by id", k["id"]):
            v = self.one("select * from vznos where sbor=? and child=?", s["id"], child["id"])
            till = f" до {ddmm(s['deadline'])}" if s["deadline"] else ""
            if v and v["status"] == "ok" and v["amount"] >= s["amount"]:
                lines.append(f"✅ {s['title']}: {rub(s['amount'])}, сдано")
            elif v and v["status"] == "wait":
                lines.append(f"⏳ {s['title']}: {rub(s['amount'])}, ждёт подтверждения казначея")
            else:
                left = s["amount"] - (v["amount"] if v else 0)
                lines.append(f"▫️ {s['title']}: {rub(left)}{till}")
                rows.append([(f"Я перевёл(а) за «{s['title']}»", f"p:paid:{s['id']}")])
        if len(lines) == 1:
            lines.append("Открытых сборов нет")
        rows.append([("Отчёт по деньгам класса", f"p:otchet:{k['id']}")])
        return [self.msg(uid, "\n".join(lines), rows)]

    # ---------- кнопки ----------
    def on_button(self, uid, name, payload):
        p = payload.split(":")
        klass, _, _ = self.state(uid)
        if p[0] == "t" and p[1] in ("yes", "no") and len(p) == 4:
            k = self.one("select klass.* from sbor join klass on klass.id=sbor.klass where sbor.id=? and treasurer=?", int(p[2]), uid)
            return self.confirm(uid, k, int(p[2]), int(p[3]), p[1] == "yes") if k else []
        if p[0] == "t":
            k = self.one("select * from klass where id=? and treasurer=?", klass, uid)
            if not k:
                return self.on_start(uid, name, "")
            if p[1] == "sbor":
                self.set_state(uid, klass, "sbor")
                return [self.msg(uid, "На что собираем, по сколько и до какого числа? Например: экскурсия 500 до 25.11")]
            if p[1] == "rashod":
                self.set_state(uid, klass, "rashod")
                return [self.msg(uid, "Сколько и на что потратили? Например: 3200 автобус. Фото чека можно приложить к этому же сообщению")]
            if p[1] == "otchet":
                return [self.msg(uid, self.report(k, full=True), self.menu(), self.cheki(k))]
            if p[1] == "dolg":
                return [self.msg(uid, self.debtors_text(k), self.menu())]
            if p[1] == "napom":
                return self.remind(uid, k)
            if p[1] == "link":
                return [self.msg(uid, self.invite_text(k))]
            if p[1] == "pick":
                _, _, data = self.state(uid)
                self.set_state(uid, klass)
                return self.mark_paid(uid, k, [(int(p[2]), data.get("amount"))], data.get("sbor"))
        if p[0] == "p":
            if p[1] == "child":
                k = self.one("select * from klass where id=?", int(p[2]))
                c = self.one("select * from child where id=? and klass=?", int(p[3]), int(p[2]))
                if not k or not c:
                    return []
                self.run("insert or replace into parent values(?,?,?,?)", uid, k["id"], c["id"], name)
                return self.parent_home(uid, name, k)
            if p[1] == "paid":
                return self.parent_paid(uid, name, int(p[2]))
            if p[1] == "otchet":
                k = self.one("select * from klass where id=?", int(p[2]))
                if k and self.one("select 1 from parent where user_id=? and klass=?", uid, k["id"]):
                    return [self.msg(uid, self.report(k, full=False), None, self.cheki(k))]
        return []

    def parent_paid(self, uid, name, sbor_id):
        s = self.one("select * from sbor where id=? and closed=0", sbor_id)
        if not s:
            return [self.msg(uid, "Этот сбор уже закрыт")]
        p = self.one("select * from parent where user_id=? and klass=?", uid, s["klass"])
        if not p:
            return []
        v = self.one("select * from vznos where sbor=? and child=?", s["id"], p["child"])
        if v and v["status"] == "ok" and v["amount"] >= s["amount"]:
            return [self.msg(uid, "У казначея уже отмечено, что вы сдали")]
        if v and v["status"] == "ok":       # частичный взнос подтверждён, родитель доплатил
            self.run("update vznos set status='wait2', ts=? where sbor=? and child=?", self.now(), s["id"], p["child"])
        elif not v:
            self.run("insert into vznos values(?,?,?,?,?)", s["id"], p["child"], 0, "wait", self.now())
        k = self.one("select * from klass where id=?", s["klass"])
        c = self.one("select * from child where id=?", p["child"])
        ask = self.msg(k["treasurer"], f"{c['name']}: родитель ({name}) пишет, что перевёл(а) за «{s['title']}». Деньги пришли?",
                       [[("Да, пришли", f"t:yes:{s['id']}:{c['id']}"), ("Нет", f"t:no:{s['id']}:{c['id']}")]])
        return [self.msg(uid, "Передал казначею. Как только он подтвердит, я напишу"), ask]

    def confirm(self, uid, k, sbor_id, child_id, yes):
        s = self.one("select * from sbor where id=? and klass=?", sbor_id, k["id"])
        c = self.one("select * from child where id=? and klass=?", child_id, k["id"])
        if not s or not c:
            return []
        v = self.one("select * from vznos where sbor=? and child=?", sbor_id, child_id)
        out = []
        if yes:
            self.run("insert or replace into vznos values(?,?,?,?,?)", sbor_id, child_id, s["amount"], "ok", self.now())
            out.append(self.msg(uid, f"Отметил: {c['name']}, {rub(s['amount'])} за «{s['title']}». {self.progress(s)}"))
            note = f"Казначей подтвердил: {rub(s['amount'])} за «{s['title']}» получены. Спасибо!"
        else:
            if v and v["status"] == "wait2":
                self.run("update vznos set status='ok' where sbor=? and child=?", sbor_id, child_id)
            elif v and v["status"] == "wait":
                self.run("delete from vznos where sbor=? and child=?", sbor_id, child_id)
            out.append(self.msg(uid, f"Хорошо, {c['name']} остаётся в списке не сдавших"))
            note = f"Казначей пока не видит перевод за «{s['title']}». Напишите ему, пожалуйста, напрямую"
        for p in self.q("select * from parent where klass=? and child=?", k["id"], child_id):
            out.append(self.msg(p["user_id"], note))
        return out

    # ---------- текст ----------
    def on_text(self, uid, name, text, photo=None):
        text = text.strip()
        klass, step, data = self.state(uid)
        low = norm(text)
        if low in ("/start", "start", "начать"):
            return self.on_start(uid, name, "")
        if step == "klass_title" and text:
            code = secrets.token_urlsafe(6)
            kid = self.run("insert into klass(code,title,treasurer,created) values(?,?,?,?)", code, text[:80], uid, self.now())
            self.set_state(uid, kid, "kids")
            return [self.msg(uid, f"Класс «{text[:80]}» создан. Пришлите список детей, каждый с новой строки: фамилия и имя. "
                                  "Если списка под рукой нет, напишите «позже»: родители впишут детей сами")]
        if step == "parent_child" and text:
            k = self.one("select * from klass where id=?", klass)
            cid = self.find_child(k["id"], text)
            cid = cid[0] if len(cid) == 1 else self.run("insert into child(klass,name) values(?,?)", k["id"], text[:60])
            self.run("insert or replace into parent values(?,?,?,?)", uid, k["id"], cid, name)
            return self.parent_home(uid, name, k)
        k = self.one("select * from klass where id=? and treasurer=?", klass, uid) if klass else None
        if not k:
            pk = self.one("select klass.* from parent join klass on klass.id=parent.klass where user_id=? order by klass.id desc", uid)
            return self.parent_home(uid, name, pk) if pk else self.on_start(uid, name, "")
        if step == "kids":
            self.set_state(uid, k["id"])
            if low in ("позже", "потом", "нет"):
                return [self.msg(uid, "Хорошо. " + HELP_T, self.menu())]
            return self.add_kids(uid, k, text)
        if step == "sbor":
            low, text = "сбор " + low, "сбор " + text
        if step == "rashod":
            low, text = "расход " + low, "расход " + text
        if step:
            self.set_state(uid, k["id"])
        if low.startswith("сбор "):
            return self.new_sbor(uid, k, text[5:])
        if low.startswith(("расход ", "потратили ", "купили ")):
            return self.new_rashod(uid, k, text.split(" ", 1)[1], photo)
        if low in ("отчет", "отчёт"):
            return [self.msg(uid, self.report(k, full=True), self.menu(), self.cheki(k))]
        if low in ("должники", "кто не сдал"):
            return [self.msg(uid, self.debtors_text(k), self.menu())]
        if low == "напомнить":
            return self.remind(uid, k)
        if low in ("ссылка", "ссылка для чата"):
            return [self.msg(uid, self.invite_text(k))]
        if low == "дети":
            kids = self.q("select name from child where klass=? order by name", k["id"])
            self.set_state(uid, k["id"], "kids")
            return [self.msg(uid, (f"В списке {len(kids)}:\n" + "\n".join(c["name"] for c in kids) if kids else "Список пуст.")
                             + "\n\nЧтобы добавить, пришлите фамилии с новой строки. Или напишите «позже»")]
        m = re.match(r"(?:сдал[аи]?|оплатил[аи]?)[ :]+(.+)", text, re.I | re.S)
        if m:
            names = [x for x in re.split(r"[,;\n]+", m.group(1)) if x.strip()]
            return self.mark_by_names(uid, k, [(n, None) for n in names])
        m = re.fullmatch(r"(.+?)\s+" + MONEY, text, re.I)
        if m and parse_money(m.group(2)) is not None:
            return self.mark_by_names(uid, k, [(m.group(1), parse_money(m.group(2)))])
        if photo:
            return [self.msg(uid, "Фото получил. Чтобы записать его как чек, напишите подпись: расход 3200 автобус")]
        return [self.msg(uid, "Не понял. " + HELP_T, self.menu())]

    def add_kids(self, uid, k, text):
        have = {norm(c["name"]) for c in self.q("select name from child where klass=?", k["id"])}
        n = 0
        for line in re.split(r"[\n;]+", text):
            nm = re.sub(r"^\s*\d+[.)]?\s*", "", line).strip()[:60]
            if nm and norm(nm) not in have:
                self.run("insert into child(klass,name) values(?,?)", k["id"], nm)
                have.add(norm(nm))
                n += 1
        return [self.msg(uid, f"Добавил детей: {n}, всего в списке {len(have)}. Теперь можно открыть сбор: сбор экскурсия 500 до 25.11", self.menu())]

    def new_sbor(self, uid, k, text):
        deadline = None
        m = re.search(r"\s+до\s+(.+)$", text, re.I)
        if m:
            deadline = parse_date(m.group(1), self.today())
            if deadline:
                text = text[:m.start()]
        m = re.fullmatch(r"(.+?)\s+(?:по\s+)?" + MONEY, text.strip(), re.I)
        amount = parse_money(m.group(2)) if m else None
        if not m or not amount:
            self.set_state(uid, k["id"], "sbor")
            return [self.msg(uid, "Не вижу сумму. Напишите так: экскурсия 500 до 25.11")]
        title = m.group(1).strip(" :,-")[:60]
        title = title[0].upper() + title[1:]
        self.run("insert into sbor(klass,title,amount,deadline,created) values(?,?,?,?,?)", k["id"], title, amount, deadline, self.now())
        till = f" до {ddmm(deadline)}" if deadline else ""
        n = self.one("select count(*) c from child where klass=?", k["id"])["c"]
        total = f" Всего ждём {rub(amount * n)} с {n} детей." if n else ""
        return [self.msg(uid, f"Сбор «{title}» открыт: по {rub(amount)}{till}.{total}\n\nПерешлите в чат класса следующее сообщение:"),
                self.msg(uid, self.invite_text(k, title, amount, deadline)),
                self.msg(uid, "Когда деньги приходят, пишите мне: сдал Иванов. Родители могут отмечаться и сами по ссылке, я спрошу у вас подтверждение", self.menu())]

    def invite_text(self, k, title=None, amount=None, deadline=None):
        head = f"Собираем на «{title}»: по {rub(amount)}" + (f" до {ddmm(deadline)}" if deadline else "") + ". Деньги переводите мне, как обычно.\n\n" if title else ""
        return (head + "Чтобы видеть, что ваш взнос учтён и на что потрачены деньги класса, нажмите на ссылку, "
                f"это бот-казначей нашего класса:\n{self.link(k['code'])}")

    def find_child(self, klass_id, text):
        t = norm(text)
        kids = self.q("select * from child where klass=?", klass_id)
        exact = [c["id"] for c in kids if norm(c["name"]) == t]
        if exact:
            return exact
        return [c["id"] for c in kids if any(w.startswith(t) for w in [norm(c["name"])] + norm(c["name"]).split()) or
                all(any(w.startswith(x) for w in norm(c["name"]).split()) for x in t.split())]

    def open_sbor(self, k):
        return self.q("select * from sbor where klass=? and closed=0 order by id desc", k["id"])

    def mark_by_names(self, uid, k, pairs):
        sbors = self.open_sbor(k)
        if not sbors:
            return [self.msg(uid, "Сначала откройте сбор: сбор экскурсия 500 до 25.11")]
        found, out = [], []
        for nm, amount in pairs:
            ids = self.find_child(k["id"], nm)
            if len(ids) == 1:
                found.append((ids[0], amount))
            elif not ids:
                out.append(self.msg(uid, f"«{nm.strip()}» в списке детей не нашёл. Проверьте фамилию или добавьте ребёнка: дети"))
            else:
                self.set_state(uid, k["id"], None, {"amount": amount, "sbor": sbors[0]["id"]})
                kids = [self.one("select * from child where id=?", i) for i in ids]
                out.append(self.msg(uid, f"«{nm.strip()}»: таких несколько, кто именно?", [[(c["name"], f"t:pick:{c['id']}")] for c in kids]))
        return (self.mark_paid(uid, k, found, sbors[0]["id"]) if found else []) + out

    def mark_paid(self, uid, k, pairs, sbor_id):
        s = self.one("select * from sbor where id=? and klass=?", sbor_id, k["id"])
        if not s:
            return []
        lines, out = [], []
        for cid, amount in pairs:
            c = self.one("select * from child where id=? and klass=?", cid, k["id"])
            v = self.one("select * from vznos where sbor=? and child=?", s["id"], cid)
            paid = (v["amount"] if v else 0) + amount if amount else s["amount"]
            self.run("insert or replace into vznos values(?,?,?,?,?)", s["id"], cid, paid, "ok", self.now())
            left = s["amount"] - paid
            lines.append(f"{c['name']}: {rub(paid)}" + (f", осталось {rub(left)}" if left > 0 else ""))
            for p in self.q("select * from parent where klass=? and child=?", k["id"], cid):
                out.append(self.msg(p["user_id"], f"Казначей отметил ваш взнос за «{s['title']}»: {rub(paid)}"
                                    + (f". Осталось {rub(left)}" if left > 0 else ". Спасибо!")))
        return [self.msg(uid, f"Отметил за «{s['title']}»:\n" + "\n".join(lines) + f"\n{self.progress(s)}")] + out

    def progress(self, s):
        n = self.one("select count(*) c from child where klass=?", s["klass"])["c"]
        r = self.one("select count(*) c, coalesce(sum(amount),0) a from vznos where sbor=? and status in ('ok','wait2') and amount>=?", s["id"], s["amount"])
        a = self.one("select coalesce(sum(amount),0) a from vznos where sbor=? and status in ('ok','wait2')", s["id"])["a"]
        return f"Сдали {r['c']} из {n}, собрано {rub(a)}"

    def new_rashod(self, uid, k, text, photo):
        m = re.fullmatch(MONEY + r"\s+(.+)", text.strip(), re.I | re.S) or None
        amount, title = (parse_money(m.group(1)), m.group(2)) if m else (None, None)
        if not m:
            m = re.fullmatch(r"(.+?)\s+" + MONEY, text.strip(), re.I | re.S)
            amount, title = (parse_money(m.group(2)), m.group(1)) if m else (None, None)
        if not amount:
            self.set_state(uid, k["id"], "rashod")
            return [self.msg(uid, "Не вижу сумму. Напишите так: 3200 автобус")]
        title = title.strip(" :,-")[:80]
        self.run("insert into rashod(klass,title,amount,photo,ts) values(?,?,?,?,?)", k["id"], title, amount, photo, self.now())
        t = self.totals(k)
        return [self.msg(uid, f"Записал расход: {rub(amount)}, {title}" + (", чек приложен" if photo else ", без чека")
                         + f". Остаток {rub(t['left'])}", self.menu())]

    def totals(self, k):
        got = self.one("select coalesce(sum(v.amount),0) a from vznos v join sbor s on s.id=v.sbor where s.klass=? and v.status in ('ok','wait2')", k["id"])["a"]
        spent = self.one("select coalesce(sum(amount),0) a from rashod where klass=?", k["id"])["a"]
        return {"got": got, "spent": spent, "left": got - spent}

    def debtors(self, k, s):
        return self.q("select c.* from child c left join vznos v on v.child=c.id and v.sbor=? and v.status in ('ok','wait2') "
                      "where c.klass=? and coalesce(v.amount,0)<? order by c.name", s["id"], k["id"], s["amount"])

    def debtors_text(self, k):
        out = []
        for s in self.open_sbor(k)[::-1]:
            d = self.debtors(k, s)
            till = f" (до {ddmm(s['deadline'])})" if s["deadline"] else ""
            part = {v["child"]: v["amount"] for v in self.q("select * from vznos where sbor=? and status in ('ok','wait2')", s["id"])}
            rows = ["• " + c["name"] + (f" (осталось {rub(s['amount'] - part[c['id']])})" if part.get(c["id"]) else "") for c in d]
            out.append(f"«{s['title']}»{till}: " + (f"не сдали {len(d)}\n" + "\n".join(rows) if d else "сдали все"))
        return "\n\n".join(out) or "Открытых сборов нет"

    def report(self, k, full):
        """Отчёт. Казначею (full) с фамилиями не сдавших, родителям только суммы и расходы."""
        t = self.totals(k)
        lines = [f"Деньги класса «{k['title']}» на {self.today().strftime('%d.%m.%Y')}",
                 f"Собрано: {rub(t['got'])}", f"Потрачено: {rub(t['spent'])}", f"Остаток: {rub(t['left'])}", "", "Сборы:"]
        for s in self.q("select * from sbor where klass=? order by id", k["id"]):
            lines.append(f"• {s['title']}, по {rub(s['amount'])}. {self.progress(s)}")
        ras = self.q("select * from rashod where klass=? order by id", k["id"])
        if ras:
            lines += ["", "Расходы:"]
            for r in ras:
                chek = " (чек приложен)" if r["photo"] else " (без чека)"
                lines.append(f"• {dt.datetime.fromisoformat(r['ts']).strftime('%d.%m')} {r['title']}: {rub(r['amount'])}{chek}")
        if full:
            lines += ["", self.debtors_text(k)]
        return "\n".join(lines)

    def cheki(self, k, limit=10):
        """Ссылки на фото последних чеков: уходят вложениями к отчёту."""
        return [r["photo"] for r in self.q("select photo from rashod where klass=? and photo is not null order by id desc limit ?", k["id"], limit)][::-1]

    def remind(self, uid, k):
        sent, no_bot, out = 0, [], []
        for s in self.open_sbor(k):
            till = f" до {ddmm(s['deadline'])}" if s["deadline"] else ""
            for c in self.debtors(k, s):
                ps = self.q("select * from parent where klass=? and child=?", k["id"], c["id"])
                v = self.one("select * from vznos where sbor=? and child=? and status in ('ok','wait2')", s["id"], c["id"])
                left = s["amount"] - (v["amount"] if v else 0)
                if not ps and c["name"] not in no_bot:
                    no_bot.append(c["name"])
                for p in ps:
                    sent += 1
                    out.append(self.msg(p["user_id"], f"Напоминание от казначея: сбор «{s['title']}», {rub(left)}{till}. "
                                        "Если уже перевели, нажмите кнопку", [[(f"Я перевёл(а) за «{s['title']}»", f"p:paid:{s['id']}")]]))
        tail = ("\nЕщё не заходили по ссылке, им я написать не могу:\n" + "\n".join("• " + n for n in no_bot)) if no_bot else ""
        return [self.msg(uid, f"Отправил напоминаний: {sent}.{tail}", self.menu())] + out
