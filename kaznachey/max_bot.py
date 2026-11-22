"""Запуск бота-казначея в MAX через Long Polling (режим для проверки и разработки).

Формат запросов взят из официального описания API: github.com/max-messenger/api-schema (schema.yaml).
На настоящем MAX этот файл ЕЩЁ НЕ ЗАПУСКАЛСЯ: из облака закрыт platform-api2.max.ru.
Для постоянной работы MAX требует Webhook по HTTPS (POST /subscriptions), это отдельный шаг.

Запуск:  MAX_TOKEN=... python3 max_bot.py kaznachey.sqlite
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from kaznachey import Kaznachey

API = "https://platform-api2.max.ru"
TYPES = "message_created,message_callback,bot_started"


class Max:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, query=None, body=None, timeout=60):
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")

    def send(self, out):
        """Исходящее сообщение логики -> запрос к MAX."""
        if out.get("callback_id"):
            return self.call("POST", "/answers", {"callback_id": out["callback_id"]}, {"notification": out.get("notification", "")})
        return self.call("POST", "/messages", {"user_id": out["user_id"]}, to_body(out))


def to_body(out):
    """Тело POST /messages: текст, кнопки (inline_keyboard) и фото чеков."""
    att = [{"type": "image", "payload": {"url": u}} for u in out.get("photos") or []]
    if out.get("buttons"):
        rows = [[{"type": "link", "text": t[:128], "url": p} if p.startswith("https://") else
                 {"type": "callback", "text": t[:128], "payload": p} for t, p in row] for row in out["buttons"]]
        att.append({"type": "inline_keyboard", "payload": {"buttons": rows}})
    body = {"text": out["text"][:4000]}
    if att:
        body["attachments"] = att
    return body


def main():
    token = os.environ.get("MAX_TOKEN")
    if not token:
        sys.exit("Нужна переменная MAX_TOKEN с токеном бота")
    api = Max(token)
    me = api.call("GET", "/me")
    bot = Kaznachey(sys.argv[1] if len(sys.argv) > 1 else "kaznachey.sqlite", bot_name=me.get("username") or "bot")
    print("Бот запущен:", me.get("username"), flush=True)
    marker = None
    while True:
        try:
            q = {"timeout": 30, "limit": 100, "types": TYPES}
            if marker is not None:
                q["marker"] = marker
            res = api.call("GET", "/updates", q, timeout=45)
        except (urllib.error.URLError, TimeoutError) as e:
            print("Сеть:", e, flush=True)
            time.sleep(5)
            continue
        marker = res.get("marker", marker)
        for u in res.get("updates") or []:
            try:
                for out in bot.handle(u):
                    try:
                        api.send(out)
                    except urllib.error.HTTPError as e:      # например, человек остановил бота
                        print("Не отправлено:", e.code, e.read()[:200], flush=True)
            except Exception as e:                           # одно плохое событие не роняет бота
                print("Ошибка обработки:", repr(e), flush=True)


if __name__ == "__main__":
    main()
