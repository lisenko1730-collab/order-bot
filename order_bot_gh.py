"""Бот заявок на 3D-печать для запуска по расписанию (GitHub Actions).

Каждый запуск: забирает новые сообщения, отвечает и завершается.
Ничего не хранится. Клиент пишет заявку ОДНИМ сообщением
(что напечатать, размер, срок; можно с фото), бот пересылает её владельцу.
"""
import json
import os
import urllib.request

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
API = f"https://api.telegram.org/bot{TOKEN}/"

GREETING = (
    "Здравствуйте! Я принимаю заявки на 3D-печать.\n\n"
    "Напишите ОДНИМ сообщением: что нужно напечатать, какой размер "
    "и к какому сроку. Можно приложить фото.\n\n"
    "Отвечаю не мгновенно, а в течение нескольких минут."
)
ASK_DETAILS = (
    "Спасибо! Теперь опишите одним сообщением: что нужно напечатать, "
    "какой размер и к какому сроку. Можно приложить фото."
)
THANKS = "Спасибо! Заявка принята, я скоро с вами свяжусь."
NEED_TEXT = "Напишите заявку текстом или пришлите фото с подписью: что напечатать, размер и срок."


def call(method, **params):
    request = urllib.request.Request(
        API + method,
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def say(chat_id, text):
    call("sendMessage", chat_id=chat_id, text=text)


def clean(text):
    return " ".join(text.split())[:1000]


def only_greeting(text):
    # текст-заготовка с сайта без подробностей: просим описать заказ
    return text.startswith("Здравствуйте! Хочу заказать") and len(text) < 60


def handle(msg):
    chat = msg["chat"]
    if chat.get("type") != "private":
        return
    chat_id = chat["id"]
    user = msg.get("from", {})
    text = clean(msg.get("text") or msg.get("caption") or "")
    has_media = any(k in msg for k in ("photo", "document", "video"))

    if text.startswith("/start"):
        say(chat_id, GREETING)
        return

    if not text and not has_media:
        say(chat_id, NEED_TEXT)
        return

    if only_greeting(text) and not has_media:
        say(chat_id, ASK_DETAILS)
        return

    contact = f"@{user['username']}" if user.get("username") else f"id {user.get('id')}"
    note = (
        "Новая заявка!\n\n"
        f"От: {user.get('first_name', '')} ({contact})\n"
        f"Заявка: {text or '(без текста, см. пересланное сообщение)'}"
    )
    call("sendMessage", chat_id=ADMIN_ID, text=note)
    if has_media:
        call(
            "forwardMessage",
            chat_id=ADMIN_ID,
            from_chat_id=chat_id,
            message_id=msg["message_id"],
        )
    say(chat_id, THANKS)


def main():
    for _ in range(5):
        updates = call("getUpdates", timeout=0, allowed_updates=["message"])["result"]
        if not updates:
            break
        for update in updates:
            message = update.get("message")
            if message:
                try:
                    handle(message)
                except Exception as error:
                    print("Ошибка при обработке сообщения:", type(error).__name__)
        # подтверждаем получение, чтобы не обрабатывать эти сообщения снова
        call("getUpdates", offset=max(u["update_id"] for u in updates) + 1, timeout=0)
        print("Обработано сообщений:", len(updates))


if __name__ == "__main__":
    main()
