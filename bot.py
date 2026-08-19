import telebot
from telebot import types
import time
import sqlite3

TOKEN = "8840831117:AAFsuZW65TrEdPFVUv9vYCZNhmdNfzIj0lY"
ADMIN_ID = 8232776469

bot = telebot.TeleBot(TOKEN)

waiting_for_form = {}
anketa_messages = {}  # message_id (у админа) -> chat_id пользователя, подавшего анкету

# ---- база данных снаряжения ----
DB_PATH = "equipment.db"

ROLES = [
    "Пулемётчик",
    "Спец. БПЛА",
    "Штурмовик",
    "Снайпер",
    "Сапёр",
    "Гранатомётчик",
    "Оператор ПЗРК",
    "Мех-вод",
]


def db_connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            photo_file_id TEXT
        )
        """
    )
    # на случай, если база уже существовала без колонки photo_file_id
    cur.execute("PRAGMA table_info(equipment)")
    columns = [row[1] for row in cur.fetchall()]
    if "photo_file_id" not in columns:
        cur.execute("ALTER TABLE equipment ADD COLUMN photo_file_id TEXT")

    # таблица-курсор: какой предмет по счёту выдать следующим для каждой роли
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS equipment_cursor (
            role TEXT PRIMARY KEY,
            next_index INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def get_equipment_for_role(role):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT item_name, description, photo_file_id FROM equipment WHERE role = ? ORDER BY id",
        (role,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_next_equipment_for_role(role):
    """Возвращает следующий предмет по кругу (round-robin) для роли.
    Никогда не повторяет один и тот же предмет два раза подряд, пока не
    выдаст все — потом начинает заново, и так бесконечно."""
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, item_name, description, photo_file_id FROM equipment WHERE role = ? ORDER BY id",
        (role,)
    )
    items = cur.fetchall()

    if not items:
        conn.close()
        return None

    cur.execute("SELECT next_index FROM equipment_cursor WHERE role = ?", (role,))
    row = cur.fetchone()
    next_index = row[0] if row else 0

    # если предметы добавляли/удаляли, индекс может выйти за пределы — подстрахуемся
    index = next_index % len(items)
    chosen = items[index]

    new_index = (index + 1) % len(items)
    cur.execute(
        "INSERT INTO equipment_cursor (role, next_index) VALUES (?, ?) "
        "ON CONFLICT(role) DO UPDATE SET next_index = excluded.next_index",
        (role, new_index)
    )
    conn.commit()
    conn.close()

    _, item_name, description, photo_file_id = chosen
    return item_name, description, photo_file_id


def add_equipment(role, item_name, description, photo_file_id=None):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO equipment (role, item_name, description, photo_file_id) VALUES (?, ?, ?, ?)",
        (role, item_name, description, photo_file_id)
    )
    conn.commit()
    conn.close()


def delete_equipment(item_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM equipment WHERE id = ?", (item_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_all_equipment():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, role, item_name, description, photo_file_id FROM equipment ORDER BY role, id")
    rows = cur.fetchall()
    conn.close()
    return rows


init_db()
# ---- конец базы данных снаряжения ----

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
11. Верификация
Вы обязаны предоставить ваш Дискорд и код дружбы Steam для вашей верификации в случае нарушения и понимания наказания.
Спасибо за понимание. Желаем успешной службы и приятной игры в составе FOF | 46 ОАеМБр. 🇺🇦
"""

DISCORD = "https://discord.gg/DkvaSB9e"


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
Ваш код дружбы Steam:

После заполнения ожидайте, пожалуйста."""
    )


@bot.message_handler(func=lambda m: m.text == "📜 Правила отряда")
def rules(message):
    bot.send_message(message.chat.id, RULES)


@bot.message_handler(func=lambda m: m.text == "💬 Дискорд FOF")
def discord(message):
    bot.send_message(message.chat.id, DISCORD)


@bot.message_handler(func=lambda m: m.text == "🎒 Получить снаряжение")
def info(message):
    if check_violation(message):
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for role in ROLES:
        markup.add(role)
    markup.add("⬅️ Назад")

    bot.send_message(
        message.chat.id,
        "Выберите роль:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back_to_menu(message):
    if check_violation(message):
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Подать анкету")
    markup.add("📜 Правила отряда")
    markup.add("💬 Дискорд FOF")
    markup.add("🎒 Получить снаряжение")

    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=markup
    )


ARMOR_NOTE = (
    "🛡 Бронежилет НЕ выдаётся через бота.\n"
    "Разрешено использовать только: «Бронежилет ВСУ» или обычный безымянный «Бронежилет».\n"
    "Остальные бронежилеты (по названиям подразделений и т.п.) использовать нельзя.\n"
    "За бронежилетом обращайтесь к администрации лично."
)


@bot.message_handler(func=lambda m: m.text in ROLES)
def send_equipment(message):
    if check_violation(message):
        return
    role = message.text
    result = get_next_equipment_for_role(role)

    if result is None:
        bot.send_message(
            message.chat.id,
            f"Для роли «{role}» снаряжение пока не добавлено в базу. Обратитесь к администрации.\n\n"
            + ARMOR_NOTE
        )
        return

    item_name, description, photo_file_id = result
    caption = item_name if not description else f"{item_name} — {description}"

    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=f"🎒 {caption}")
    else:
        bot.send_message(message.chat.id, f"🎒 {caption}")

    bot.send_message(message.chat.id, ARMOR_NOTE)


def is_armor_name(name):
    lowered = name.lower()
    return "бронежилет" in lowered or "бронік" in lowered


# ---- администрирование базы снаряжения ----
# Снаряжение добавляется ТОЛЬКО через фото. Текстовая команда отключена.
@bot.message_handler(commands=["add_equipment"])
def cmd_add_equipment(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(
        message.chat.id,
        "Снаряжение теперь добавляется только через фото.\n\n"
        "Отправь боту фото предмета с подписью:\n"
        "Роль | Название предмета | Описание (необязательно)\n\n"
        f"Доступные роли:\n" + "\n".join(ROLES)
    )


# С фото: админ отправляет боту фото с подписью "Роль | Название | Описание"
@bot.message_handler(content_types=["photo"])
def cmd_add_equipment_photo(message):
    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or ""
    if "|" not in caption:
        bot.send_message(
            message.chat.id,
            "Чтобы добавить снаряжение с этим фото, отправь его ещё раз с подписью в формате:\n"
            "Роль | Название предмета | Описание (необязательно)\n\n"
            f"Доступные роли:\n" + "\n".join(ROLES)
        )
        return

    parts = [p.strip() for p in caption.split("|")]
    role = parts[0]
    item_name = parts[1] if len(parts) > 1 else ""
    description = parts[2] if len(parts) > 2 else ""

    if role not in ROLES:
        bot.send_message(
            message.chat.id,
            "Такой роли нет. Доступные роли:\n" + "\n".join(ROLES)
        )
        return

    if not item_name:
        bot.send_message(message.chat.id, "Не указано название предмета.")
        return

    if is_armor_name(item_name):
        bot.send_message(
            message.chat.id,
            "🛡 Бронежилеты через бота не добавляются — их выдают вручную. "
            "Используй ручную выдачу."
        )
        return

    # берём фото в максимальном качестве (последнее в списке)
    photo_file_id = message.photo[-1].file_id

    add_equipment(role, item_name, description, photo_file_id)
    bot.send_message(message.chat.id, f"✅ Добавлено с фото для роли «{role}»: {item_name}")


@bot.message_handler(commands=["list_equipment"])
def cmd_list_equipment(message):
    if message.from_user.id != ADMIN_ID:
        return
    rows = get_all_equipment()
    if not rows:
        bot.send_message(message.chat.id, "База снаряжения пуста.")
        return

    lines = ["📦 Всё снаряжение в базе:\n"]
    current_role = None
    for item_id, role, item_name, description, photo_file_id in rows:
        if role != current_role:
            lines.append(f"\n— {role} —")
            current_role = role
        desc_part = f" — {description}" if description else ""
        photo_mark = " 📷" if photo_file_id else ""
        lines.append(f"[{item_id}] {item_name}{desc_part}{photo_mark}")

    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["del_equipment"])
def cmd_del_equipment(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Использование: /del_equipment ID_предмета\n(ID смотри через /list_equipment)")
        return

    deleted = delete_equipment(int(parts[1]))
    if deleted:
        bot.send_message(message.chat.id, "✅ Удалено.")
    else:
        bot.send_message(message.chat.id, "Предмет с таким ID не найден.")
# ---- конец администрирования базы снаряжения ----


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
    
