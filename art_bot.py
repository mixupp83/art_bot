import telebot
from PIL import Image, ImageOps
import io
from telebot import types

TOKEN = 'MyToken'
bot = telebot.TeleBot(TOKEN)

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов по умолчанию
DEFAULT_ASCII_CHARS = '@%#*+=-:. '


def resize_image(image, new_width=100):
    """
    Изменяет размер изображения, сохраняя пропорции.

    :param image: Объект изображения PIL.
    :param new_width: Новая ширина изображения.
    :return: Объект изображения PIL с новым размером.
    """
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    """
    Преобразует изображение в оттенки серого.

    :param image: Объект изображения PIL.
    :return: Объект изображения PIL в оттенках серого.
    """
    return image.convert("L")


def image_to_ascii(image_stream, new_width=40, ascii_chars=DEFAULT_ASCII_CHARS):
    """
    Преобразует изображение в ASCII-арт.

    :param image_stream: Поток данных изображения.
    :param new_width: Новая ширина изображения.
    :param ascii_chars: Набор символов для ASCII-арта.
    :return: Строка с ASCII-артом.
    """
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized, ascii_chars)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image, ascii_chars):
    """
    Преобразует пиксели изображения в символы ASCII.

    :param image: Объект изображения PIL.
    :param ascii_chars: Набор символов для ASCII-арта.
    :return: Строка с символами ASCII.
    """
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ascii_chars[pixel * len(ascii_chars) // 256]
    return characters


def pixelate_image(image, pixel_size):
    """
    Пикселизирует изображение.

    :param image: Объект изображения PIL.
    :param pixel_size: Размер пикселя.
    :return: Объект изображения PIL с эффектом пикселизации.
    """
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


def invert_colors(image):
    """
    Инвертирует цвета изображения.

    :param image: Объект изображения PIL.
    :return: Объект изображения PIL с инвертированными цветами.
    """
    return ImageOps.invert(image)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """
    Обрабатывает команды /start и /help.

    :param message: Объект сообщения от пользователя.
    """
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """
    Обрабатывает полученное изображение и запрашивает набор символов для ASCII-арта.

    :param message: Объект сообщения от пользователя.
    """
    bot.reply_to(message, "I got your photo! Please send me the set of characters you'd like to use for ASCII art.")
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id, 'ascii_chars': None}


@bot.message_handler(func=lambda message: message.text and message.chat.id in user_states and user_states[message.chat.id]['ascii_chars'] is None)
def handle_ascii_chars(message):
    """
    Обрабатывает набор символов, предоставленный пользователем.

    :param message: Объект сообщения от пользователя.
    """
    ascii_chars = message.text
    user_states[message.chat.id]['ascii_chars'] = ascii_chars
    bot.reply_to(message, "Got it! Please choose what you'd like to do with your image.",
                 reply_markup=get_options_keyboard())


def get_options_keyboard():
    """
    Создает клавиатуру с опциями для обработки изображения.

    :return: Объект клавиатуры.
    """
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    invert_btn = types.InlineKeyboardButton("Invert Colors", callback_data="invert")
    keyboard.add(pixelate_btn, ascii_btn, invert_btn)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """
    Обрабатывает нажатия на кнопки клавиатуры.

    :param call: Объект callback-запроса.
    """
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Pixelating your image...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        ascii_and_send(call.message)
    elif call.data == "invert":
        bot.answer_callback_query(call.id, "Inverting colors of your image...")
        invert_and_send(call.message)


def pixelate_and_send(message):
    """
    Пикселизирует изображение и отправляет его пользователю.

    :param message: Объект сообщения от пользователя.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message):
    """
    Преобразует изображение в ASCII-арт и отправляет его пользователю.

    :param message: Объект сообщения от пользователя.
    """
    photo_id = user_states[message.chat.id]['photo']
    ascii_chars = user_states[message.chat.id]['ascii_chars']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream, ascii_chars=ascii_chars)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


def invert_and_send(message):
    """
    Инвертирует цвета изображения и отправляет его пользователю.

    :param message: Объект сообщения от пользователя.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    inverted = invert_colors(image)

    output_stream = io.BytesIO()
    inverted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


bot.polling(none_stop=True)