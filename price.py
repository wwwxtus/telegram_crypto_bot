import psycopg2

from conf_bd import host, user, password, db_name


def format_number(num):
    if num >= 1000000000:
        return f"{num / 1000000000:.1f}B"
    elif num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    else:
        return str(num)


def check_price(bot):
    @bot.message_handler(commands=['price'])
    def price(message):
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
            # Получаем символ валюты из сообщения
            command, *args = message.text.split()
            if len(args) == 0:
                if language == 'ru':
                    bot.send_message(message.chat.id, "Укажите символ валюты после команды. Пример: /price BTC")
                elif language == 'en':
                    bot.send_message(message.chat.id,
                                     "Specify the currency symbol after the command. Example: /price BTC")
                return
            print(args[0])

            currency_symbol = args[0].upper()

            connection.autocommit = True
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            result = cursor.fetchone()[0]  # Получаем количество совпадений

            # Проверяем, есть ли символ валюты в базе данных
            if result == 0:
                if language == 'ru':
                    bot.send_message(message.chat.id,
                                     f"Не удалось найти информацию для {currency_symbol}. Проверьте символ валюты.")
                elif language == 'en':
                    bot.send_message(message.chat.id,
                                     f"Unable to find information for {currency_symbol}. "
                                     f"Please check your currency symbol.")
                return

            cursor.execute("SELECT price FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            price_record = cursor.fetchone()

            # Проверка на наличие результата
            if price_record is None:
                if language == 'ru':
                    bot.send_message(message.chat.id, "Цена не найдена.")
                elif language == 'en':
                    bot.send_message(message.chat.id, "Price not found.")
                return

            price = price_record[0]
            cursor.execute("SELECT name FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            crypto_name = cursor.fetchone()[0]
            cursor.execute("SELECT volume_24h FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            volume_24h = cursor.fetchone()[0]
            cursor.execute("SELECT market_cap FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            market_cap = cursor.fetchone()[0]
            cursor.execute("SELECT last_updated FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            last_update = cursor.fetchone()[0]
            cursor.execute("SELECT price_change_percentage_24h FROM cryptocurrencies WHERE symbol = %s", (currency_symbol,))
            price_change_24h = cursor.fetchone()[0]

            if language == 'ru':
                if int(price) >= 1000:
                    price_text = f"{int(price)} USD"  # Цена без дробной части, если >= 1000
                else:
                    price_text = f"{price} USD"  # Цена с дробной частью, если < 1000

                bot.send_message(
                    message.chat.id,
                    f"🪙 <b>{crypto_name}</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💲 <b>Цена:</b> {price_text}\n"
                    f"📊 <b>Объём за 24ч:</b> {format_number(int(volume_24h))}\n"
                    f"📈 <b>Изменение за 24ч:</b> {price_change_24h}%\n"
                    f"🏦 <b>Рыночная капитализация:</b> {format_number(int(market_cap))}\n"
                    f"⏰ <b>Обновлено:</b> {last_update}\n"
                    f"━━━━━━━━━━━━━━━",
                    parse_mode="HTML"
                )


            elif language == 'en':
                bot.send_message(message.chat.id, f'The current price of {currency_symbol} is ${price} USD.')
            cursor.close()

        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при получении данных.")
            print(f"Error: {e}")

        finally:
            connection.close()
            print("[INFO] PostgresSQL connection closed")
