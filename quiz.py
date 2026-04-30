import telebot
import random


def start_quiz(bot, chat_id, user_id, get_db_connection_func):
    """
    Начинает викторину. Приоритет: личные слова пользователя, если их > 3.
    Иначе - общие слова.
    """
    conn = get_db_connection_func()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе 😢")
        return None, None

    cur = conn.cursor()
    try:
        # Проверяем, есть ли у пользователя свои слова
        cur.execute("""
            SELECT word_ru, word_en FROM user_words 
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
        """, (user_id,))
        user_words = cur.fetchall()

        # Если личных слов достаточно (больше 3, чтобы были варианты ответов), берем их
        if len(user_words) >= 4:
            correct_row = random.choice(user_words)
            source_table = 'user_words'
        else:
            # Иначе берем из общих
            cur.execute("SELECT word_ru, word_en FROM global_words ORDER BY RANDOM() LIMIT 1")
            correct_row = cur.fetchone()
            source_table = 'global_words'

            if not correct_row:
                # Если и общих нет (маловероятно), пробуем взять любые личные, даже если их мало
                if user_words:
                    correct_row = random.choice(user_words)
                    source_table = 'user_words'
                else:
                    bot.send_message(chat_id, "В базе пока нет слов для изучения.")
                    return None, None

        correct_ru, correct_en = correct_row

        # 2. Берем 3 случайных НЕПРАВИЛЬНЫХ ответа из той же таблицы или общей
        # Для простоты и разнообразия, неправильные ответы всегда берем из global_words,
        # кроме случая, когда правильным было личное слово, которого нет в global.
        # Но проще всего брать неправильные из global_words, так как там гарантированно есть данные.

        cur.execute("""
            SELECT word_en FROM global_words 
            WHERE word_en != %s 
            ORDER BY RANDOM() 
            LIMIT 3
        """, (correct_en,))

        wrong_rows = cur.fetchall()
        wrong_answers = [row[0] for row in wrong_rows]

        # Если в global_words мало слов, дополняем из user_words или заглушками
        while len(wrong_answers) < 3:
            # Пробуем добрать из других слов пользователя
            cur.execute("""
                SELECT word_en FROM user_words 
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s) AND word_en != %s
                ORDER BY RANDOM() LIMIT 1
            """, (user_id, correct_en))
            extra = cur.fetchone()
            if extra:
                wrong_answers.append(extra[0])
            else:
                wrong_answers.append("FakeWord")

        options = wrong_answers + [correct_en]
        random.shuffle(options)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for option in options:
            markup.add(telebot.types.KeyboardButton(option))

        bot.send_message(chat_id, f"Как переводится слово: **{correct_ru}**?", parse_mode="Markdown",
                         reply_markup=markup)

        return correct_en, correct_ru, markup

    except Exception as e:

        print(f"Ошибка в викторине: {e}")

        bot.send_message(chat_id, "Произошла ошибка при генерации вопроса.")

        return None, None, None
    finally:
        cur.close()
        conn.close()


def check_answer(user_answer, correct_answer, ru_word):
    if user_answer.lower() == correct_answer.lower():
        return f"✅ Отлично! {correct_answer} — это {ru_word}. ❤️"
    else:
        return f"❌ Не совсем. Правильный ответ: {correct_answer}. Попробуй еще раз!"