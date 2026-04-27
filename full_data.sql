-- fill_data.sql

INSERT INTO global_words (word_ru, word_en) VALUES
('Я', 'I'), ('Мы', 'We'), ('Ты', 'You'), ('Он', 'He'), ('Она', 'She'),
('Оно', 'It'), ('Красный', 'Red'), ('Синий', 'Blue'), ('Кот', 'Cat'), ('Собака', 'Dog')
ON CONFLICT DO NOTHING;