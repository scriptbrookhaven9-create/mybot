import telebot
from telebot import types
import time

TOKEN = "8840831117:AAFsuZW65TrEdPFVUv9vYCZNhmdNfzIj0lY"
ADMIN_ID = 8232776469

bot = telebot.TeleBot(TOKEN)

waiting_for_form = {}
anketa_messages = {}  # message_id (у админа) -> chat_id пользователя, подавшего анкету

# ---- система предупреждений за мат и спам ----
BAD_WORDS = ["мат1", "мат2", "мат3"]  # впиши сюда свои слова для фильтра
SPAM_INTERVAL = 3      # если сообщения идут быстрее, чем раз в 3 секунды - подозрение на спам
SPAM_STREAK_LIMIT = 4  # столько быстрых сообщений подряд = спам
MAX_WARNINGS = 3        # после скольких предупреждений бот перестаёт отвечать

warnings_count = {}
blocked_users = set()
last_message_time = {}
message_streak = {}


def check_violation(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        return False  # админа не проверяем

    if user_id in blocked_users:
        return True  # бот уже не отвечает этому пользователю

    text = (message.text or "").lower()

    is_spam = False
    now = time.time()
    last_time = last_message_time.get(user_id, 0)
    if now - last_time < SPAM_INTERVAL:
        message_streak[user_id] = message_streak.get(user_id, 0) + 1
        if message_streak[user_id] >= SPAM_STREAK_LIMIT:
            is_spam = True
    else:
        message_streak[user_id] = 0
    last_message_time[user_id] = now

    is_mat = any(word in text for word in BAD_WORDS)

    if is_mat or is_spam:
        warnings_count[user_id] = warnings_count.get(user_id, 0) + 1
        count = warnings_count[user_id]

        if count >= MAX_WARNINGS:
            blocked_users.add(user_id)
            bot.send_message(
                message.chat.id,
                f"🚫 Вы получили {count} предупреждений. Бот больше не будет вам отвечать."
            )
        else:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, не делайте так. Вы получили предупреждение "
                f"({count}/{MAX_WARNINGS}). Если вы получите достаточное количество "
                "предупреждений, бот перестанет вам отвечать."
            )
        return True

    return False


@bot.message_handler(commands=["unblock"])
def unblock_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Использование: /unblock ID_пользователя")
        return
    try:
        target_id = int(parts[1])
        blocked_users.discard(target_id)
        warnings_count.pop(target_id, None)
        bot.send_message(message.chat.id, f"Пользователь {target_id} разблокирован.")
    except ValueError:
        bot.send_message(message.chat.id, "ID должен быть числом.")
# ---- конец системы предупреждений ----

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
    if check_violation(message):
        return
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


@bot.message_handler(commands=["craka"])
def craka(message):
    bot.send_message(message.chat.id, "Я люблю Бандеру ♥️")


@bot.message_handler(func=lambda m: m.text == "📋 Подать анкету")
def form(message):
    if check_violation(message):
        return
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


# Ответ администратора на анкету:
# Если ты (ADMIN_ID) отвечаешь (Reply) на сообщение с анкетой в этом чате с ботом,
# бот перешлёт твой ответ тому пользователю, который подавал именно эту анкету.
@bot.message_handler(
    func=lambda m: m.reply_to_message is not None
    and m.from_user.id == ADMIN_ID
    and m.reply_to_message.message_id in anketa_messages
)
def admin_reply(message):
    user_chat_id = anketa_messages[message.reply_to_message.message_id]
    bot.send_message(
        user_chat_id,
        f"📩 Ответ от администрации:\n\n{message.text}"
    )
    bot.send_message(message.chat.id, "✅ Ответ отправлен пользователю.")


@bot.message_handler(func=lambda m: True)
def text(message):
    if check_violation(message):
        return

    if waiting_for_form.get(message.chat.id):
        waiting_for_form.pop(message.chat.id)

        sent = bot.send_message(
            ADMIN_ID,
            f"📨 Новая анкета\n\n"
            f"👤 @{message.from_user.username}\n"
            f"🆔 {message.from_user.id}\n\n"
            f"{message.text}\n\n"
            f"↩️ Чтобы ответить, сделайте Reply на это сообщение."
        )

        # запоминаем связь: сообщение у админа -> чат пользователя
        anketa_messages[sent.message_id] = message.chat.id

        bot.send_message(
            message.chat.id,
            "✅ Спасибо! Ваша анкета отправлена. Ожидайте ответа администрации."
        )


bot.infinity_polling()
