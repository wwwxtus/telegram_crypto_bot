from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
from telebot import types

from conf_bd import host, user, password, db_name


def adding_alerts_db():
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
                """CREATE TABLE IF NOT EXISTS alerts(
                    alert_id serial PRIMARY KEY, 
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    symbol VARCHAR(50),
                    target_price numeric(20, 10),
                    direction VARCHAR(10) NOT NULL,
                    alerts_date TIMESTAMP,
                    number_repetitions INT DEFAULT 1);"""
            )
            print("[INFO] Table created successfully")

    except Exception as ex:
        print("[INFO] Error while working:", ex)

    finally:
        connection.close()
        print("[INFO] PostgresSQL connection closed")


def set_notification(bot):
    @bot.message_handler(commands=['alert'])
    def alerts(message):
        try:
            # Подключение к базе
            connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )

            connection.autocommit = True
            a = message.from_user.id
            with connection.cursor() as cursor:
                cursor.execute("SELECT language FROM users WHERE id_user = %s", (str(a),))
                language = cursor.fetchone()[0]

            command, *args = message.text.split()
            if len(args) == 0:
                if language == 'ru':
                    bot.send_message(message.chat.id,
                                     "Установите оповещения в виде /alert [криптовалюта] [цена срабатывания]")
                elif language == 'en':
                    bot.send_message(message.chat.id, "Set alerts as /alert [cryptocurrency] [alert trigger price]")

            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE id_user = %s", (str(a),))
                table_id_user = cursor.fetchone()[0]

            with connection.cursor() as cursor:
                cursor.execute("SELECT price FROM cryptocurrencies WHERE symbol = %s", (args[0],))
                current_price = cursor.fetchone()[0]

            if current_price > float(args[1]):
                direction = 'down'
            else:
                direction = 'up'

            print(args[0], args[1])

            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO alerts (user_id, symbol, target_price, direction, alerts_date, number_repetitions) 
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING alert_id;""",
                    (str(table_id_user), args[0], args[1], direction, datetime.now(), str(1))
                )
                alert_id = cursor.fetchone()[0]
                print("[INFO] Alerts inserted successfully")

            # Обновляем last_alert_id для пользователя
            with connection.cursor() as cursor:
                cursor.execute("""
                       UPDATE users
                       SET last_alert_id = %s
                       WHERE id_user = %s;
                   """, (alert_id, str(message.from_user.id)))

            # Создание кнопки на сообщении (Markup)
            markup = types.InlineKeyboardMarkup()

            # Добавление кнопки с callback_data
            button_1 = types.InlineKeyboardButton('⚙️ Настроить оповещение', callback_data='configure_alerts')
            # Добавляем кнопку в макет
            markup.row(button_1)

            # Отправка сообщения с кнопкой
            bot.reply_to(
                message,
                f"Вы установили оповещение на монете {args[0]}\n"
                f"Цена срабатывания {args[1]}\n"
                "Для настройки оповещения воспользуйтесь кнопкой \n⚙️ Настроить оповещение",
                reply_markup=markup
            )

        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при установке оповещения.")
            print(f"Error: {e}")
        finally:
            connection.close()
            print("[INFO] PostgresSQL connection closed")


def delete_expired_alerts():
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )

        # Удаление алертов с alert_count = 0
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM alerts WHERE number_repetitions = 0;")
            connection.commit()

        print("[INFO] Alerts with number_repetitions = 0 have been deleted.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        connection.close()
        print("[INFO] PostgreSQL connection closed")


def check_alerts(bot):
    # Подключение к базе
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )
    connection.autocommit = True

    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT a.alert_id, a.symbol, a.target_price, a.direction, a.user_id, a.number_repetitions, u.chat_id, p.price, p.last_updated
                FROM alerts a
                JOIN cryptocurrencies p ON a.symbol = p.symbol
                JOIN users u ON a.user_id = u.id
                WHERE (a.direction = 'down' AND p.price < a.target_price)
                OR (a.direction = 'up' AND p.price > a.target_price);
            """)
            triggered_alerts = cursor.fetchall()

        for alert in triggered_alerts:
            chat_id = alert['chat_id']
            symbol = alert['symbol']
            target_price = alert['target_price']
            current_price = alert['price']
            direction = "выше" if alert['direction'] == "up" else "ниже"

            if alert['number_repetitions'] > 0:
                bot.send_message(
                    int(chat_id),
                    f"🔔 <b>Оповещение о цене!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🪙 <b>Монета:</b> {symbol}\n"
                    f"💵 <b>Текущая цена:</b> ${current_price}\n"
                    f"📉 <b>Условие срабатывания:</b> Цена {direction} ${target_price}\n"
                    f"⏰ <b>Дата и время:</b> {alert['last_updated']}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📲 <i>Для настройки новых оповещений используйте меню</i>",
                    parse_mode="HTML"
                )

                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE alerts
                        SET number_repetitions = %s
                        WHERE alert_id = %s
                    """, (alert['number_repetitions'] - 1, alert['alert_id']))

        delete_expired_alerts()

    finally:
        connection.close()
