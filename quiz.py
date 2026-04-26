import telebot
import random


def start_quiz(bot, chat_id, user_id, get_db_connection_func):
    """
    Начинает викторину: выбирает слово, генерирует кнопки и отправляет вопрос.
    Возвращает правильный ответ (en) и русское слово (ru), чтобы main мог их запомнить.
    """
    conn = get_db_connection_func()
    if not conn:
        bot.send_message(chat_id, "Ошибка подключения к базе 😢")
        return None, None

    cur = conn.cursor()
    try:
        # 1. Берем случайное правильное слово из global_words
        cur.execute("SELECT word_ru, word_en FROM global_words ORDER BY RANDOM() LIMIT 1")
        correct_row = cur.fetchone()

        if not correct_row:
            bot.send_message(chat_id, "В базе пока нет слов для изучения.")
            return None, None

        correct_ru, correct_en = correct_row

        # 2. Берем 3 случайных НЕПРАВИЛЬНЫХ ответа
        cur.execute("""
            SELECT word_en FROM global_words 
            WHERE word_en != %s 
            ORDER BY RANDOM() 
            LIMIT 3
        """, (correct_en,))

        wrong_rows = cur.fetchall()
        wrong_answers = [row[0] for row in wrong_rows]

        # Если слов мало, дополняем заглушками, чтобы всегда было 4 варианта
        while len(wrong_answers) < 3:
            wrong_answers.append("FakeWord")

        # 3. Собираем варианты и перемешиваем
        options = wrong_answers + [correct_en]
        random.shuffle(options)

        # 4. Создаем клавиатуру с кнопками
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for option in options:
            markup.add(telebot.types.KeyboardButton(option))

        # 5. Отправляем вопрос пользователю
        bot.send_message(chat_id, f"Как переводится слово: **{correct_ru}**?", parse_mode="Markdown",
                         reply_markup=markup)

        # Возвращаем правильные данные, чтобы main сохранил их для проверки следующего сообщения
        return correct_en, correct_ru

    except Exception as e:
        print(f"Ошибка в викторине: {e}")
        bot.send_message(chat_id, "Произошла ошибка при генерации вопроса.")
        return None, None
    finally:
        cur.close()
        conn.close()


def check_answer(user_answer, correct_answer, ru_word):
    """
    Проверяет ответ пользователя.
    Возвращает строку с результатом (сообщение для отправки).
    """
    if user_answer.lower() == correct_answer.lower():
        return f"✅ Отлично! {correct_answer} — это {ru_word}. ❤️"
    else:
        return f"❌ Не совсем. Правильный ответ: {correct_answer}. Попробуй еще раз!"