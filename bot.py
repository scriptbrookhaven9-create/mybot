import telebot
from telebot import types

TOKEN = "8840831117:AAFsuZW65TrEdPFVUv9vYCZNhmdNfzIj0lY"
ADMIN_ID = 8232776469

bot = telebot.TeleBot(TOKEN)

waiting_for_form = {}
saved_forms = []

RULES = """
📜 Правила отряда FOF | 46 ОАеМБр

1. Уважайте участников проекта.
2. Выполняйте приказы командования.
3. Не используйте запрещённые программы.
4. Соблюдайте дисциплину.
5. Будьте активны.
6. Соблюдайте правила Discord-сервера.
"""

DISCORD = "https://discord.gg/zwNXncdn"

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Подать анкету")
    markup.add("📜 Правила отряда")
    markup.add("💬 Дискорд FOF")

    bot.send_message(
        message.chat.id,
        "Привет!\n\n"
        "Этот бот принадлежит проекту FOF | 46 ОАеМБр.\n\n"
        "Для того чтобы подать анкету в подразделение, пожалуйста, выберите команду снизу, чтобы продолжить разговор.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "📋 Подать анкету")
def form(message):
    waiting_for_form[message.chat.id] = True

    bot.send_message(
        message.chat.id,
        "Хорошо! Заполни, пожалуйста, анкету. Пример ниже."
    )

    bot.send_message(
        message.chat.id,
        """Здравствуйте, пожалуйста, заполните анкету по примеру ниже.

Возраст:
Роль:
Причина вступления:
Сколько времени сможете уделять активности в день:
Есть ли опыт в подобных отрядах:
Ваш DS аккаунт:

После заполнения ожидайте, пожалуйста."""
    )

@bot.message_handler(func=lambda m: m.text == "📜 Правила отряда")
def rules(message):
    bot.send_message(message.chat.id, RULES)

@bot.message_handler(func=lambda m: m.text == "💬 Дискорд FOF")
def discord(message):
    bot.send_message(message.chat.id, DISCORD)

@bot.message_handler(commands=["craka"])
def craka(message):
    bot.send_message(message.chat.id, "Я люблю Бандеру ♥️")

@bot.message_handler(commands=["ankets"])
def ankets(message):
    if message.from_user.id != ADMIN_ID:
        return

    if not saved_forms:
        bot.send_message(message.chat.id, "📭 Пока нет ни одной анкеты.")
        return

    bot.send_message(
        message.chat.id,
        "\n\n--------------------\n\n".join(saved_forms)
    )

@bot.message_handler(func=lambda m: True)
def text(message):
    if waiting_for_form.get(message.chat.id):
        waiting_for_form.pop(message.chat.id)

        form_text = (
            f"📨 Новая анкета\n\n"
            f"👤 @{message.from_user.username}\n"
            f"🆔 {message.from_user.id}\n\n"
            f"{message.text}"
        )

        saved_forms.append(form_text)

        bot.send_message(ADMIN_ID, form_text)

        bot.send_message(
            message.chat.id,
            "✅ Спасибо! Ваша анкета отправлена. Ожидайте ответа администрации."
        )

bot.infinity_polling()
