"""Бот заявок на 3D-печать для запуска по расписанию (GitHub Actions).

Каждый запуск: забирает новые сообщения, отвечает и завершается.
Ничего не хранится: ответы клиента лежат в тексте вопросов бота
(клиент отвечает «ответом» на вопрос, это включается автоматически).
"""
import json
import os
import urllib.request

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
API = f"https://api.telegram.org/bot{TOKEN}/"

Q_WHAT = "Что нужно напечатать? Опишите коротко или пришлите фото."
Q_SIZE = "Какой нужен размер? Например: 10 см в высоту."
Q_DEADLINE = "К какому сроку нужно? Например: до 25 октября."

FORCE_REPLY = {"force_reply": True, "input_field_placeholder": "Ваш ответ"}


def call(method, **params):
    request = urllib.request.Request(
        API + method,
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def ask(chat_id, text):
    call("sendMessage", chat_id=chat_id, text=text, reply_markup=FORCE_REPLY)


def clean(text):
    return " ".join(text.split())[:500]


def field(question, prefix):
    for line in question.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return "(не указано)"


def handle(msg):
    chat = msg["chat"]
    if chat.get("type") != "private":
        return
    chat_id = chat["id"]
    user = msg.get("from", {})
    text = clean(msg.get("text") or msg.get("caption") or "")
    has_photo = "photo" in msg

    reply = msg.get("reply_to_message") or {}
    question = reply.get("text", "") if reply.get("from", {}).get("is_bot") else ""

    if text.startswith("/start"):
        ask(
            chat_id,
            "Здравствуйте! Я принимаю заявки на 3D-печать. "
            "Отвечаю не мгновенно, а в течение нескольких минут.\n\n" + Q_WHAT,
        )
        return

    if Q_DEADLINE in question:
        contact = f"@{user['username']}" if user.get("username") else f"id {user.get('id')}"
        what = field(question, "Что: ")
        size = field(question, "Размер: ")
        call(
            "sendMessage",
            chat_id=ADMIN_ID,
            text=(
                "Новая заявка!\n\n"
                f"От: {user.get('first_name', '')} ({contact})\n"
                f"Что: {what}\n"
                f"Размер: {size}\n"
                f"Срок: {text or '(не указано)'}"
            ),
        )
        call(
            "sendMessage",
            chat_id=chat_id,
            text="Спасибо! Заявка принята, я скоро с вами свяжусь.",
        )
    elif Q_SIZE in question:
        what = field(question, "Что: ")
        ask(
            chat_id,
            f"Что: {what}\nРазмер: {text or '(не указано)'}\n\n" + Q_DEADLINE,
        )
    elif Q_WHAT in question:
        what = text or "(фото)"
        if has_photo:
            call(
                "forwardMessage",
                chat_id=ADMIN_ID,
                from_chat_id=chat_id,
                message_id=msg["message_id"],
            )
            what += " (фото переслано отдельным сообщением)"
        ask(chat_id, f"Что: {what}\n\n" + Q_SIZE)
    else:
        call(
            "sendMessage",
            chat_id=chat_id,
            text="Чтобы оставить заявку, нажмите /start",
        )


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
