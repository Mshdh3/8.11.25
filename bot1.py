import config
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3

bot = telebot.TeleBot(config.API_TOKEN)

def send_info(bot, message, row, with_favorite=True):
    info = f"""
📍 Название: {row[2]}
📅 Год: {row[3]}
🎭 Жанр: {row[4]}
⭐ Рейтинг IMDB: {row[5]}

🔻 Описание:
{row[6]}
"""
    markup = add_to_favorite(row[0]) if with_favorite else None
    bot.send_photo(message.chat.id, row[1], caption=info, reply_markup=markup)

def add_to_favorite(movie_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Добавить в избранное 🌟", callback_data=f'favorite_{movie_id}'),
        InlineKeyboardButton("Удалить из избранного ❌", callback_data=f'delete_{movie_id}')
    )
    return markup

def main_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('/random'), KeyboardButton('/favorites'), KeyboardButton('/top'), KeyboardButton('/help'))
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("favorite") or call.data.startswith("delete"))
def callback_query(call):
    user_id = call.from_user.id
    movie_id = call.data.split("_")[1]
    con = sqlite3.connect("movie_database.db")
    with con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS favorites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        movie_id INTEGER,
                        UNIQUE(user_id, movie_id)
                    )''')
        if call.data.startswith("favorite"):
            cur.execute("SELECT * FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id))
            if cur.fetchone():
                bot.answer_callback_query(call.id, "Этот фильм уже в избранном 🌟")
            else:
                cur.execute("INSERT INTO favorites (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
                con.commit()
                bot.answer_callback_query(call.id, "Фильм добавлен в избранное ❤️")
        elif call.data.startswith("delete"):
            cur.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id))
            con.commit()
            bot.answer_callback_query(call.id, "Фильм удалён из избранного 💔")
        cur.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 
        """Привет! 🎥 Добро пожаловать в лучший Movie-Chat-Bot!  
Здесь ты можешь найти 1000 фильмов 🔥  
Нажми /random, чтобы получить случайный фильм  
Или напиши название фильма, и я постараюсь его найти! 🎬""",
        reply_markup=main_markup())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
🎬 Команды Movie-Chat-Bot:

/start - Приветствие и главное меню  
/random - Получить случайный фильм  
/favorites - Показать твои избранные фильмы  
/top - Показать топ фильмов по рейтингу IMDB  
/help - Список команд и их описание  

Ты также можешь просто написать название фильма, и я постараюсь его найти! 🔍
"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['random'])
def random_movie(message):
    try:
        con = sqlite3.connect("movie_database.db")
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
            row = cur.fetchone()
            cur.close()
        if row:
            send_info(bot, message, row)
        else:
            bot.send_message(message.chat.id, "Пока нет фильмов в базе 😢")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.message_handler(commands=['favorites'])
def show_favorites(message):
    user_id = message.chat.id
    try:
        con = sqlite3.connect("movie_database.db")
        with con:
            cur = con.cursor()
            cur.execute('''SELECT movies.* FROM movies
                           JOIN favorites ON movies.id = favorites.movie_id
                           WHERE favorites.user_id = ?''', (user_id,))
            rows = cur.fetchall()
            cur.close()
        if not rows:
            bot.send_message(message.chat.id, "У тебя пока нет избранных фильмов 💔")
        else:
            for row in rows:
                send_info(bot, message, row)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.message_handler(commands=['top'])
def top_movies(message):
    try:
        con = sqlite3.connect("movie_database.db")
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM movies ORDER BY CAST(imdb_rating AS FLOAT) DESC LIMIT 10")
            rows = cur.fetchall()
            cur.close()
        if not rows:
            bot.send_message(message.chat.id, "Пока нет фильмов в базе 😢")
        else:
            bot.send_message(message.chat.id, "🎬 Топ 10 фильмов по рейтингу IMDB:")
            for row in rows:
                send_info(bot, message, row)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.message_handler(func=lambda message: True)
def search_movie(message):
    try:
        con = sqlite3.connect("movie_database.db")
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM movies WHERE LOWER(title) LIKE ?", ('%' + message.text.lower() + '%',))
            row = cur.fetchone()
            cur.close()
        if row:
            bot.send_message(message.chat.id, "Конечно! Я знаю этот фильм 😌")
            send_info(bot, message, row)
        else:
            bot.send_message(message.chat.id, "Я не знаю такого фильма 😢")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

bot.infinity_polling()
