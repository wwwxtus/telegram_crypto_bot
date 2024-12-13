import webbrowser
from telebot import types

import psycopg2
from conf_bd import host, user, password, db_name


def first_command(bot):
    def adding_users_db(message):
        try:
            # Подключение к базе
            connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )
            # Сохранение изменений в БД автоматом
            connection.autocommit = True
            # Подключение курсора для работы с БД
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version();"
                )

                print(f'Server version: {cursor.fetchone()}')

            with connection.cursor() as cursor:
                cursor.execute(
                    """CREATE TABLE IF NOT EXISTS users(
                        id serial PRIMARY KEY, 
                        id_user varchar(50) NOT NULL,
                        first_name varchar(50),
                        last_name varchar(50),
                        language varchar(10) NOT NULL,
                        chat_id INT NOT NULL);"""
                )
                print("[INFO] Table created successfully")

            with connection.cursor() as cursor:
                # Проверка на существование записи
                cursor.execute(
                    "SELECT * FROM users WHERE id_user = %s AND language = %s;",
                    (str(message.from_user.id), message.from_user.language_code)
                )

                # Если запись не найдена, выполняем вставку
                if cursor.fetchone() is None:
                    cursor.execute(
                        "INSERT INTO users (id_user, first_name, last_name, language, chat_id) VALUES (%s, %s, %s, %s, %s);",
                        (str(message.from_user.id), message.from_user.first_name, message.from_user.last_name,
                         message.from_user.language_code, message.chat.id)
                    )
                    print("[INFO] Data inserted successfully")
                else:
                    print("[INFO] User already exists, skipping insertion")

        except Exception as ex:
            print("[INFO] Error while working:", ex)

        finally:
            connection.close()
            print("[INFO] PostgresSQL connection closed")

    # Обработка комнады /site /website (перекидывает пользователя на сайт, который указан в параметре)
    @bot.message_handler(commands=['site', 'website'])
    def site(message):
        webbrowser.open('https://coinmarketcap.com')

    @bot.message_handler(commands=['start'])
    def start(message):
        try:
            # Подключение к базе
            connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )
            # Блок с работой над базой данных
            adding_users_db(message)

            cursor = connection.cursor()
            connection.autocommit = True
            a = message.from_user.id
            cursor.execute("SELECT language FROM users WHERE id_user = %s", (str(a),))

            language = cursor.fetchone()[0]
            cursor.close()
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            # Создание кнопок с помощью ReplyKeyboardMarkup
            if language == 'en':
                btn1 = types.KeyboardButton('🌐 Go to website CoinMarketCup')
                btn2 = types.KeyboardButton('❗ Help information')
                btn3 = types.KeyboardButton('👤 My profile')
                markup.row(btn1, btn2)
                markup.row(btn3)
            elif language == 'ru':
                # Добавление этой кнопки(1 параметр - Сообщение в этой кнопке)
                btn1 = types.KeyboardButton('🌐 Перейдите на сайт CoinMarketCup')
                btn2 = types.KeyboardButton('❗️ Справочная информация')
                # Дизайн кнопок в плане расположения, каждая кнопка в своей строке
                btn3 = types.KeyboardButton('👤 Мой профиль')
                btn4 = types.KeyboardButton('⚙️ Мои оповещения')
                markup.row(btn1, btn2)
                markup.row(btn3, btn4)

            # Отправка фото и приветственного сообщения
            file = open('./photo.png', 'rb')
            bot.send_photo(message.chat.id, file)

            if language == 'en':
                bot.send_message(message.chat.id,
                                 f'{message.from_user.first_name} {message.from_user.last_name} Welcome to CryptoTrackerBot! 📈🚀'
                                 '\n Your personal assistant for tracking and analyzing the cryptocurrency market.'
                                 '\nHere’s what you can do:'
                                 '\n💰 Check Prices: Use /price [currency] (e.g., /price BTC) to get the latest market prices.'
                                 '\n🔔 Set Alerts: Use /alert [currency] [price] (e.g., /alert ETH 2000) to set custom price alerts.'
                                 '\n📊 Portfolio Tracking: Manage your holdings and view real-time updates using /portfolio.'
                                 '\n📰 Get News: Stay informed with the latest news by typing /news.'
                                 '\nType /help to see all available commands.'
                                 '\nLet’s keep an eye on the market together! 📊🔥', reply_markup=markup)
            elif language == 'ru':
                bot.send_message(message.chat.id,
                                 f'{message.from_user.first_name} {message.from_user.last_name} Добро пожаловать в CryptoTrackerBot! 📈🚀'
                                 '\nВаш персональный помощник для отслеживания и анализа рынка криптовалют.'
                                 '\nВот что вы можете делать:'
                                 '\n💰 Проверка цен: используйте /price [валюта] (например, /price BTC), чтобы узнать последние рыночные цены.'
                                 '\n🔔 Установка оповещений: используйте /alert [валюта] [цена] (например, /alert ETH 2000), чтобы установить пользовательские оповещения о ценах.'
                                 '\n📊 Отслеживание портфеля: управляйте своими активами и просматривайте обновления в реальном времени с помощью /portfolio.'
                                 '\n📰 Получение новостей: будьте в курсе последних новостей, введя /news.'
                                 '\nВведите /help, чтобы увидеть все доступные команды.'
                                 '\nДавайте следить за рынком вместе!  📊🔥', reply_markup=markup)
        except Exception as ex:
            print("[INFO] Error while working:", ex)

        finally:
            connection.close()
            print("[INFO] PostgresSQL connection closed")

    # Обработка комнады /help (Выводит все возможности бота)
    @bot.message_handler(commands=['help'])
    def help_info(message):
        try:
            # Подключение к базе
            connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )

            cursor = connection.cursor()
            connection.autocommit = True
            a = message.from_user.id
            cursor.execute("SELECT language FROM users WHERE id_user = %s", (str(a),))

            language = cursor.fetchone()[0]
            cursor.close()
            if language == 'en':
                bot.send_message(
                    message.chat.id,
                    "📘 <b>Help Information:</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "💹 <b>Check Prices:</b> /price [currency]\n"
                    "🔔 <b>Set Alerts:</b> /alert [currency]\n"
                    "📊 <b>Portfolio Tracking:</b> /portfolio\n"
                    "📰 <b>Get News:</b> /news\n"
                    "━━━━━━━━━━━━━━━\n"
                    "ℹ️ <i>Use the commands above to interact with the bot.</i>",
                    parse_mode="HTML"
                )
            elif language == 'ru':
                bot.send_message(
                    message.chat.id,
                    "📘 <b>Справочная информация:</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "💹 <b>Проверьте цены:</b> /price [валюта]\n"
                    "🔔 <b>Установите оповещения:</b> /alert [валюта]\n"
                    "📊 <b>Отслеживание портфеля:</b> /portfolio\n"
                    "📰 <b>Получите новости:</b> /news\n"
                    "━━━━━━━━━━━━━━━\n"
                    "ℹ️ <i>Используйте команды выше, чтобы взаимодействовать с ботом.</i>",
                    parse_mode="HTML"
                )

        except Exception as ex:
            print("[INFO] Error while working:", ex)

        finally:
            connection.close()
            print("[INFO] PostgresSQL connection closed")