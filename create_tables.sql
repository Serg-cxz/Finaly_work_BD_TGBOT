-- create_tables.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS global_words (
    id SERIAL PRIMARY KEY,
    word_ru VARCHAR(100) NOT NULL,
    word_en VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_words (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_ru VARCHAR(100) NOT NULL,
    word_en VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);