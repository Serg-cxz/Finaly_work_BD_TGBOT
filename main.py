import telebot
import psycopg2
import quiz


# --- НАСТРОЙКИ ИЗ .ENV ---
BOT_TOKEN = '8781516451:AAErDnwhPTAi7OHNLOLCTJfTycypYBEOaWc'
DB_NAME = "postgres"
DB_USER = "bot_user_clean"
DB_PASSWORD = "918273vip"
DB_HOST = "localhost"
DB_PORT = "5432"
if not BOT_TOKEN or not DB_PASSWORD:
    print("❌ Ошибка: Не найдены необходимые переменные в файле .env")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Глобальные словари
user_states = {}
temp_words = {}
temp_quiz = {}


def get_db_connection():
    try:
        dsn = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} port={DB_PORT}"
        conn = psycopg2.connect(dsn)
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return None


def show_main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    btn_add = telebot.types.KeyboardButton("➕ Добавить слово")
    btn_learn = telebot.types.KeyboardButton("📚 Учить слова")
    btn_delete = telebot.types.KeyboardButton("❌ Удалить слово")
    markup.add(btn_add, btn_learn)
    markup.add(btn_delete)
    bot.send_message(chat_id, "Выбери действие:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "User"

    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "Ошибка подключения к базе 😢")
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        result = cur.fetchone()

        if not result:
            cur.execute("""
                INSERT INTO users (telegram_id, username, first_name)
                VALUES (%s, %s, %s)
            """, (user_id, username, first_name))
            conn.commit()
            bot.send_message(message.chat.id, f"Привет, {first_name}! Ты зарегистрирован в базе. 🎉")
        else:
            bot.send_message(message.chat.id, f"С возвращением, {first_name}! 👋")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при работе с базой: {e}")
    finally:
        cur.close()
        conn.close()

    show_main_menu(message.chat.id)


@bot.message_handler(func=lambda message: message.text == '➕ Добавить слово')
def start_add_word(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "Ошибка подключения к базе 😢")
        show_main_menu(message.chat.id)
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        if not cur.fetchone():
            bot.send_message(message.chat.id, "Сначала напиши /start.")
            show_main_menu(message.chat.id)
            return
    finally:
        cur.close()
        conn.close()

    user_states[user_id] = 'waiting_ru'
    bot.send_message(message.chat.id, "Напиши слово на русском языке:",
                     reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == 'waiting_ru')
def process_ru_word(message):
    user_id = message.from_user.id
    temp_words[user_id] = {'ru': message.text.strip()}
    user_states[user_id] = 'waiting_en'
    bot.send_message(message.chat.id, "Теперь напиши перевод на английский:")


@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == 'waiting_en')
def process_en_word(message):
    user_id = message.from_user.id
    ru_word = temp_words[user_id]['ru']
    en_word = message.text.strip()

    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "Ошибка подключения к базе 😢")
        del user_states[user_id]
        del temp_words[user_id]
        show_main_menu(message.chat.id)
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            bot.send_message(message.chat.id, "❌ Ошибка пользователя.")
            show_main_menu(message.chat.id)
            return

        user_id_db = result[0]
        cur.execute("""
            INSERT INTO user_words (user_id, word_ru, word_en)
            VALUES (%s, %s, %s)
        """, (user_id_db, ru_word, en_word))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Слово '{ru_word}' -> '{en_word}' добавлено!")
        cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id_db,))
        count = cur.fetchone()[0]
        bot.send_message(message.chat.id, f"📚 У тебя уже {count} слов.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка при сохранении.")
    finally:
        cur.close()
        conn.close()

    del user_states[user_id]
    del temp_words[user_id]
    show_main_menu(message.chat.id)


@bot.message_handler(func=lambda message: message.text == '📚 Учить слова')
def start_learning(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    conn = get_db_connection()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе 😢")
        show_main_menu(chat_id)
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        if not cur.fetchone():
            bot.send_message(chat_id, "Сначала напиши /start.")
            show_main_menu(chat_id)
            return
    finally:
        cur.close()
        conn.close()

    # Получаем разметку вместе с ответами
    correct_en, correct_ru, markup = quiz.start_quiz(bot, chat_id, user_id, get_db_connection)

    if correct_en and correct_ru and markup:
        # Сохраняем ВСЁ: правильный ответ, русское слово и клавиатуру
        temp_quiz[user_id] = {
            'correct': correct_en,
            'ru': correct_ru,
            'markup': markup # <-- Сохраняем клавиатуру!
        }
        user_states[user_id] = 'learning'
    else:
        show_main_menu(chat_id)


@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == 'learning')
def check_quiz_answer(message):
    user_id = message.from_user.id
    user_answer = message.text.strip()

    if user_id not in temp_quiz:
        bot.send_message(message.chat.id, "Ошибка. Напиши /start заново.")
        del user_states[user_id]
        show_main_menu(message.chat.id)
        return

    correct_answer = temp_quiz[user_id]['correct']
    ru_word = temp_quiz[user_id]['ru']
    saved_markup = temp_quiz[user_id]['markup']  # Берем сохраненную клавиатуру

    if user_answer.lower() == correct_answer.lower():
        # --- ПРАВИЛЬНО ---
        result_message = f"✅ Отлично! {correct_answer} — это {ru_word}. ❤️"

        del user_states[user_id]
        if user_id in temp_quiz:
            del temp_quiz[user_id]

        bot.send_message(message.chat.id, result_message, reply_markup=telebot.types.ReplyKeyboardRemove())
        show_main_menu(message.chat.id)

    else:
        # --- НЕПРАВИЛЬНО ---
        # НЕ удаляем состояние и НЕ удаляем temp_quiz!

        bot.send_message(
            message.chat.id,
            f"❌ Не совсем. Попробуй еще раз!",
            reply_markup=saved_markup  # <-- Возвращаем те же самые кнопки!
        )
        # Состояние 'learning' остается активным. Следующий клик по кнопке снова попадет сюда.


@bot.message_handler(func=lambda message: message.text == '❌ Удалить слово')
def start_delete_word(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    conn = get_db_connection()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе 😢")
        show_main_menu(chat_id)
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        if not cur.fetchone():
            bot.send_message(chat_id, "Сначала напиши /start.")
            show_main_menu(chat_id)
            return

        cur.execute("""
            SELECT id, word_ru, word_en 
            FROM user_words 
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
        """, (user_id,))
        words = cur.fetchall()

        if not words:
            bot.send_message(chat_id, "У тебя нет слов. Добавь их через меню.")
            show_main_menu(chat_id)
            return

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for word_id, ru, en in words:
            callback_data = f"del_{word_id}"
            btn_text = f"❌ {ru} → {en}"
            markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=callback_data))

        bot.send_message(chat_id, "Выбери слово для удаления:", reply_markup=markup)

    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(chat_id, "Произошла ошибка.")
        show_main_menu(chat_id)
    finally:
        cur.close()
        conn.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_word_callback(call):
    user_id = call.from_user.id
    word_id_str = call.data.split('_')[1]

    try:
        word_id = int(word_id_str)
    except ValueError:
        bot.answer_callback_query(call.id, text="Ошибка данных.")
        return

    conn = get_db_connection()
    if not conn:
        bot.answer_callback_query(call.id, text="Ошибка базы.")
        return

    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM user_words 
            WHERE id = %s AND user_id = (SELECT id FROM users WHERE telegram_id = %s)
            RETURNING word_ru, word_en
        """, (word_id, user_id))
        deleted_word = cur.fetchone()
        conn.commit()

        if deleted_word:
            ru, en = deleted_word
            bot.answer_callback_query(call.id, text=f"Удалено: {ru}")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Слово '{ru}' → '{en}' удалено.",
                reply_markup=None
            )

            # FIX: Показываем обновленное количество слов
            cur.execute("SELECT COUNT(*) FROM user_words WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)",
                        (user_id,))
            count = cur.fetchone()[0]
            bot.send_message(call.message.chat.id, f"📚 У тебя осталось {count} слов.")
        else:
            bot.answer_callback_query(call.id, text="Слово не найдено.")

    except Exception as e:
        print(f"Ошибка удаления: {e}")
        bot.answer_callback_query(call.id, text="Ошибка.")
    finally:
        cur.close()
        conn.close()

    show_main_menu(call.message.chat.id)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()