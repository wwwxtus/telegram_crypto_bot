import time
import requests
from datetime import datetime
import threading
import re

import telebot
import webbrowser

from psycopg2.extras import DictCursor
from telebot import types
import psycopg2

from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, BigInteger, DateTime, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

from conf_bd import host, user, password, db_name
from price import check_price
from start_command import first_command
from alerts import set_notification, check_alerts, adding_alerts_db
from data_unloading import db_upload

# Подключение токена бота
bot = telebot.TeleBot('7801057162:AAFeo2tmLBEcfOZj3FoYIB9QdZu8CpdMYgY')

first_command(bot)

Base = declarative_base()

DATABASE_URL = f"postgresql://{user}:{password}@{host}/{db_name}"
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base.metadata.create_all(engine)


class Alerts(Base):
    __tablename__ = 'alerts'

    alert_id = Column(Integer, Sequence('alerts_alert_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    symbol = Column(String(50))
    target_price = Column(Numeric(20, 10))
    direction = Column(String(10), nullable=False)
    alerts_date = Column(DateTime)
    number_repetitions = Column(Integer, default=1)

    user = relationship("Users", back_populates="alerts")


class Cryptocurrencies(Base):
    __tablename__ = 'cryptocurrencies'

    currency_id = Column(Integer, Sequence('cryptocurrencies_currency_id_seq'), primary_key=True)
    symbol = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    market_cap = Column(Numeric(20, 2))
    price = Column(Numeric(20, 10))
    price_change_percentage_24h = Column(Numeric(20, 2))
    volume_24h = Column(Numeric(20, 2))
    last_updated = Column(DateTime)


class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    id_user = Column(String(50), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    language = Column(String(10), nullable=False)
    chat_id = Column(Integer, nullable=False)
    last_alert_id = Column(BigInteger)

    alerts = relationship("Alerts", back_populates="user")


# Функция подключения к базе данных
def get_db_connection():
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True
        return connection
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к базе данных: {e}")
        return None


# Обработчик для всех сообщений, который будет постоянно проверять нажатие кнопок
def on_click(message):
    language = message.from_user.language_code
    if language == 'en':
        if message.text == '🌐 Go to website CoinMarketCup':
            print("User visited the website")
            bot.send_message(
                message.chat.id,
                "🌐 <b>Visit CoinMarketCap:</b> [Click here](https://coinmarketcap.com)",
                parse_mode="HTML"
            )
        elif message.text == '❗ Help information':
            print("User viewed help information")
            bot.send_message(
                message.chat.id,
                "📘 <b>Help Information:</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "💹 <b>Check Prices:</b> /price [currency]\n"
                "🔔 <b>Set Alerts:</b> /alert [currency]\n"
                "📊 <b>Portfolio Tracking:</b> /portfolio\n"
                "📰 <b>Get News:</b> /news\n"
                "━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        elif message.text == '👤 My profile':
            print("User viewed their profile")
            first_name = message.from_user.first_name or "Not provided"
            last_name = message.from_user.last_name or "Not provided"
            bot.send_message(
                message.chat.id,
                f"👤 <b>Your Profile:</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>First Name:</b> {first_name}\n"
                f"👥 <b>Last Name:</b> {last_name}\n"
                f"🆔 <b>ID:</b> {message.from_user.id}\n"
                f"━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )

    elif language == 'ru':
        if message.text == '🌐 Перейдите на сайт CoinMarketCup':
            print("User visited the website")
            bot.send_message(
                message.chat.id,
                "🌐 <b>Visit CoinMarketCap:</b> [Click here](https://coinmarketcap.com)",
                parse_mode="HTML"
            )
        elif message.text == '❗️ Справочная информация':
            print("User viewed help information")
            bot.send_message(
                message.chat.id,
                "📘 <b>Help Information:</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "💹 <b>Check Prices:</b> /price [currency]\n"
                "🔔 <b>Set Alerts:</b> /alert [currency]\n"
                "📊 <b>Portfolio Tracking:</b> /portfolio\n"
                "📰 <b>Get News:</b> /news\n"
                "━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        elif message.text == '👤 Мой профиль':
            print("User viewed their profile")
            first_name = message.from_user.first_name or "Not provided"
            last_name = message.from_user.last_name or "Not provided"
            bot.send_message(
                message.chat.id,
                f"👤 <b>Your Profile:</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>First Name:</b> {first_name}\n"
                f"👥 <b>Last Name:</b> {last_name}\n"
                f"🆔 <b>ID:</b> {message.from_user.id}\n"
                f"━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        elif message.text == '⚙️ Мои оповещения':
            # Подключение к базе данных
            connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )

            connection.autocommit = True

            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT alert_id, symbol, target_price, alerts_date, number_repetitions
                    FROM alerts
                    JOIN users ON alerts.user_id = users.id
                    WHERE id_user = %s
                    ORDER BY alerts.alerts_date
                """, (str(message.from_user.id),))
                result = cursor.fetchall()

            if not result:
                bot.send_message(
                    message.chat.id,
                    "У вас нет активных оповещений.",
                    parse_mode="HTML"
                )
                return

            alerts_text = "<b>Ваши оповещения:</b>\n\n"
            bot.send_message(
                message.chat.id,
                alerts_text,
                parse_mode="HTML"
            )
            i = 1

            print(result)

            for my_alert in result:
                # Создание кнопок для всех оповещений
                markup = types.InlineKeyboardMarkup(row_width=1)
                alert_id = str(my_alert['alert_id'])

                alerts_text = (
                    f"📈 <b>Оповещение № {i}</b>\n"
                    f"🔹 <b>Символ:</b> {my_alert['symbol']}\n"
                    f"🔹 <b>Цена:</b> {my_alert['target_price']} USD\n"
                    f"🔹 <b>Дата создания:</b> {my_alert['alerts_date']}\n"
                    f"🔹 <b>Осталось срабатываний:</b> {my_alert['number_repetitions']} раз(а)\n\n"
                )

                # Создаем кнопки настройки и удаления
                button_1 = types.InlineKeyboardButton(
                    f'⚙️ Настроить оповещение №{i}', callback_data=f'configure_alert_{alert_id}'
                )
                button_2 = types.InlineKeyboardButton(
                    f'❌ Удалить оповещение №{i}', callback_data=f'delete_alert'
                )
                markup.add(button_1, button_2)
                i += 1

                bot.send_message(
                    message.chat.id,
                    alerts_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )


check_price(bot)

adding_alerts_db()

set_notification(bot)


def delete_alert(callback):
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True

        # Извлечение даты из сообщения
        alert_text = callback.message.text
        match = re.search(r'🔹 Дата создания: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', alert_text)
        number = re.search(r'📈 Оповещение № (\d+)', alert_text)

        if match:
            alert_date = match.group(1)  # Извлекаем дату в формате YYYY-MM-DD
            number_date = number.group(1)

            # Удаление оповещения из базы данных
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM alerts
                    WHERE alerts_date = %s
                    AND user_id = (
                        SELECT id 
                        FROM users
                        WHERE id_user = %s
                    )
                """, (alert_date, str(callback.from_user.id)))
                print(callback.from_user.id)

                if cursor.rowcount > 0:
                    bot.send_message(
                        callback.message.chat.id,
                        f"✅ Оповещение № {number_date} успешно удалено."
                    )
                else:
                    bot.send_message(
                        callback.message.chat.id,
                        f"❌ Оповещение с № {number_date} не найдено."
                    )
        else:
            bot.send_message(
                callback.message.chat.id,
                "❌ Не удалось извлечь дату создания из сообщения. Проверьте формат."
            )
    except Exception as e:
        bot.send_message(callback.message.chat.id, "Произошла ошибка при удалении оповещения.")
        print(f"Error: {e}")
    finally:
        connection.close()
        print("[INFO] PostgreSQL connection closed")


def setup_alert_count(callback):
    markup = types.InlineKeyboardMarkup()

    # Создаем кнопки с количеством срабатываний
    button_1 = types.InlineKeyboardButton('1 раз', callback_data='new_set_alert_count_1')
    button_3 = types.InlineKeyboardButton('3 раза', callback_data='new_set_alert_count_3')
    button_5 = types.InlineKeyboardButton('5 раз', callback_data='new_set_alert_count_5')

    markup.add(button_1, button_3, button_5)

    bot.send_message(
        callback.message.chat.id,
        "Выберите количество срабатываний уведомления",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('new_set_alert_count_'))
def set_alert_count_callback(call):
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )

        # Извлекаем количество срабатываний из callback_data
        count_str = call.data.split('_')[-1]
        alert_count = int(count_str)

        # Получаем user_id и извлекаем last_alert_id для этого пользователя
        user_id = call.from_user.id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT last_alert_id
                FROM users
                WHERE id_user = %s;
            """, (str(user_id),))
            result = cursor.fetchone()
            if result[0]:
                alert_id = result[0]
                cursor.execute("""
                    SELECT id 
                    FROM users
                    WHERE id_user = %s
                """, (str(user_id),))
                check = cursor.fetchone()[0]
                cursor.execute("""
                    UPDATE alerts
                    SET number_repetitions = %s
                    WHERE alert_id = %s AND user_id = %s
                """, (alert_count, alert_id, check))

                connection.commit()

                bot.send_message(call.message.chat.id, f"Количество срабатываний установлено: {count_str}")
            else:
                bot.send_message(call.message.chat.id, "Не удалось найти последний алерт для пользователя.")
    except Exception as e:
        bot.send_message(call.message.chat.id, "Произошла ошибка при установке оповещения.")
        print(f"Error: {e}")
    finally:
        connection.close()
        print("[INFO] PostgreSQL connection closed")


@bot.callback_query_handler(func=lambda call: call.data.startswith("configure_alert_"))
def configure_alert(call):
    alert_id = int(call.data.split("_")[2])

    # Создаем клавиатуру с кнопками для выбора количества срабатываний
    markup = types.InlineKeyboardMarkup()
    for count in [1, 3, 5, 10]:
        markup.add(
            types.InlineKeyboardButton(
                f"🔢 {count} раз(а)",
                callback_data=f"set_alert_count_{alert_id}_{count}"
            )
        )

    # Кнопка отмены
    markup.add(
        types.InlineKeyboardButton(
            "❌ Отмена", callback_data="cancel_alert_configure"
        )
    )

    # Сообщение с инструкцией
    bot.edit_message_text(
        f"⚙️ Настройка уведомления №{alert_id}\n\n"
        f"🔔 Выберите, сколько раз сработает уведомление перед его деактивацией.\n\n"
        f"➡️ Нажмите на один из вариантов ниже:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_alert_count_"))
def set_alert_count(call):
    count_str = call.data.split('_')[-1]
    count = int(count_str)
    alert_id = call.data.split("_")[-2]
    alert_id = int(alert_id)

    try:
        connection = psycopg2.connect(
            host=host, user=user, password=password, database=db_name
        )
        cursor = connection.cursor()

        # Обновляем количество срабатываний для уведомления
        cursor.execute(
            "UPDATE alerts SET number_repetitions = %s WHERE alert_id = %s",
            (count, alert_id)
        )
        connection.commit()
        cursor.close()
        connection.close()

        # Подтверждаем выбор
        bot.edit_message_text(
            f"✅ Настройка завершена!\n\n"
            f"🔔 Уведомление №{alert_id} теперь будет срабатывать {count} раз(а).",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Ошибка при обновлении: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_alert_configure")
def cancel_alert_configure(call):
    bot.edit_message_text(
        "❌ Настройка уведомления отменена.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda callback: callback.data == 'delete_alert')
def delete_alert_handler(callback):
    delete_alert(callback)


@bot.callback_query_handler(func=lambda callback: callback.data == 'configure_alerts')
def setup_alert_count_handler(callback):
    setup_alert_count(callback)


# Декоратор для обработки callback_data
@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == 'delete':
        # Чтобы удалить предыдущее сообщение вызывается `callback.message.message_id - 1`
        bot.delete_message(callback.message.chat.id, callback.message.message_id - 1)
    elif callback.data == 'edit':
        bot.edit_message_text('Stop', callback.message.chat.id, callback.message.message_id)


# Обработка команды /message (выводит всю информацию об этом параметре)
@bot.message_handler(commands=['message'])
def info_message(message):
    bot.send_message(message.chat.id, message)


# Обработка команды /upload (выгрузка всех таблиц в разных форматах)
@bot.message_handler(commands=['upload'])
def all_upload_data(message):
    bot.reply_to(message, "Upload process started!")
    db_upload()


# Обработка сообщения от пользователя (если вводит id, ответом на его сообщение выводим его ID)
@bot.message_handler()
def info(message):
    on_click(message)
    if message.text.lower() == 'id':
        bot.reply_to(message, f'ID: {message.from_user.id}')


def fetch_cryptocurrencies(page, per_page=250):
    try:
        response = requests.get("https://api.coingecko.com/api/v3/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page
        })
        response.raise_for_status()  # Проверка статуса ответа
        data = response.json()
        if isinstance(data, list):
            return data
        else:
            print("[WARNING] Некорректный формат ответа от API.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Ошибка получения данных из CoinGecko API: {e}")
        return []


def update_data():
    """Обновляет данные о криптовалютах в базе данных."""
    connection = get_db_connection()
    if not connection:
        print("[ERROR] Нет соединения с базой данных.")
        return

    try:
        cursor = connection.cursor()
        total_pages = 2

        for page in range(1, total_pages + 1):
            cryptocurrencies = fetch_cryptocurrencies(page)
            if not cryptocurrencies:
                print(f"[WARNING] Пустая страница данных: {page}")
                continue

            for currency in cryptocurrencies:
                if not all(key in currency for key in
                           ['symbol', 'name', 'market_cap', 'current_price', 'price_change_percentage_24h',
                            'total_volume']):
                    print(f"[WARNING] Пропущены обязательные поля в данных: {currency}")
                    continue

                cursor.execute("SELECT 1 FROM cryptocurrencies WHERE symbol = %s", (currency['symbol'].upper(),))
                exists = cursor.fetchone()

                if exists:
                    cursor.execute("""
                        UPDATE cryptocurrencies
                        SET 
                            market_cap = %s,
                            price = %s,
                            volume_24h = %s,
                            last_updated = %s
                        WHERE name = %s;
                    """, (
                        currency.get('market_cap', 0),
                        currency.get('current_price', 0),
                        currency.get('total_volume', 0),
                        datetime.now(),
                        currency['name']
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO cryptocurrencies (symbol, name, market_cap, price, price_change_percentage_24h, volume_24h, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        currency['symbol'].upper(),
                        currency['name'],
                        currency.get('market_cap', 0),
                        currency.get('current_price', 0),
                        currency.get('price_change_percentage_24h', 0),
                        currency.get('total_volume', 0),
                        datetime.now()
                    ))

        connection.commit()
        print("[INFO] Данные успешно обновлены.")
    except Exception as e:
        print(f"[ERROR] Ошибка обновления данных: {e}")
    finally:
        connection.close()


def infinite_loop():
    while True:
        check_alerts(bot)
        update_data()
        time.sleep(10)


# Запускаем `infinite_loop` в отдельном потоке
thread = threading.Thread(target=infinite_loop)
thread.start()

# Запускаем бота
bot.infinity_polling()
