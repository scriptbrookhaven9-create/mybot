import telebot
from telebot import types

TOKEN = "8840831117:AAFsuZW65TrEdPFVUv9vYCZNhmdNfzIj0lY"
ADMIN_ID = 8232776469

bot = telebot.TeleBot(TOKEN)

waiting_for_form = {}

RULES = """
📜 Правила подразделения FOF | 46 ОАеМБр
Добро пожаловать в подразделение FOF. Вступая в отряд, вы соглашаетесь соблюдать все правила, перечисленные ниже.
1. Дисциплина
Каждый участник обязан соблюдать дисциплину и выполнять распоряжения командования. Игнорирование приказов недопустимо 
2. Уважение
Запрещены оскорбления, провокации, угрозы, травля, дискриминация и любые действия, нарушающие уважительное общение между участниками.
3. Активность
Участники должны поддерживать активность в подразделении. При длительном отсутствии без предупреждения командования возможны санкции вплоть до исключения.
4. Честная игра
Использование читов, эксплойтов, багов или любого стороннего ПО, дающего нечестное преимущество, строго запрещено.
5. Конфиденциальность
Запрещено распространять внутреннюю информацию подразделения, материалы проекта, переписки или документы без разрешения командира это исключение с отряда.
6. Субординация
Во время тренировок, мероприятий и операций необходимо соблюдать субординацию и выполнять указания командиров.
7. Discord
Каждый участник обязан соблюдать правила Discord-сервера и поддерживать порядок в голосовых и текстовых каналах.
8. Репутация подразделения
Любые действия, наносящие ущерб репутации FOF или 46 ОАеМБр, недопустимы.
9. Наказания
За нарушение правил администрация вправе вынести предупреждение, временно ограничить доступ, понизить в должности или исключить из подразделения. В зависимости от тяжести нарушения санкции могут применяться без предварительного предупреждения.
10. Незнание правил
Незнание правил не освобождает от ответственности.
Спасибо за понимание. Желаем успешной службы и приятной игры в составе FOF | 46 ОАеМБр. 🇺🇦
"""

DISCORD = "https://discord.gg/zwNXncdn"

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Подать анкету")
    markup.add("📜 Правила отряда")
    markup.add("💬 Дискорд FOF")
    markup.add("🎒 Получить снаряжение")

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
        """
        
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
@bot.message_handler(func=lambda m: m.text == "🎒 Получить информацию")
def info(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Пулемётчик")
    markup.add("Спец. БПЛА")
    markup.add("Штурмовик")
    markup.add("Снайпер")
    markup.add("Сапёр")
    markup.add("Гранатомётчик")
    markup.add("Оператор ПЗРК")
    markup.add("⬅️ Назад")

    bot.send_message(
        message.chat.id,
        "Выберите роль:",
        reply_markup=markup
    )
    
@bot.message_handler(commands=["ankets"])
def ankets(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Все новые анкеты будут приходить сюда автоматически.")

@bot.message_handler(func=lambda m: True)
def text(message):
    if waiting_for_form.get(message.chat.id):
        waiting_for_form.pop(message.chat.id)

        bot.send_message(
            ADMIN_ID,
            f"📨 Новая анкета\n\n"
            f"👤 @{message.from_user.username}\n"
            f"🆔 {message.from_user.id}\n\n"
            f"{message.text}"
        )

        bot.send_message(
            message.chat.id,
            "✅ Спасибо! Ваша анкета отправлена. Ожидайте ответа администрации."
        )

@bot.message_handler(commands=["reply"])
def reply(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        bot.send_message(
            message.chat.id,
            "Использование:\n/reply ID сообщение"
        )
        return

    try:
        user_id = int(parts[1])
        text = parts[2]

        bot.send_message(
            user_id,
            f"📨 Ответ администрации:\n\n{text}"
        )

        bot.send_message(
            message.chat.id,
            "✅ Сообщение отправлено."
        )
    except:
        bot.send_message(
            message.chat.id,
            "❌ Не удалось отправить сообщение." )bot.infinity_polling()
