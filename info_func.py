from telebot import types
import telebot

bot = telebot.TeleBot('7801057162:AAFeo2tmLBEcfOZj3FoYIB9QdZu8CpdMYgY')


# Обработка действия, если пользователь отправил фото
@bot.message_handler(content_types=['photo'])
def get_photo(message):
    # Создание кнопки на сообщении (Markup)
    markup = types.InlineKeyboardMarkup()

    # Добавление этой кнопки(1 параметр - Сообщение в этой кнопке, 2 параметр - ссылка на сайт например, или функция действия)
    button_1 = types.InlineKeyboardButton('Перейти на сайт', url='https://coinmarketcap.com')
    button_2 = types.InlineKeyboardButton('Удалить фото', callback_data='delete')
    button_3 = types.InlineKeyboardButton('Изменить текст', callback_data='edit')

    # Дизайн кнопок в плане расположения, каждая кнопка в своей строке
    markup.row(button_1)
    markup.row(button_2, button_3)

    bot.reply_to(message, 'Good', reply_markup=markup)

