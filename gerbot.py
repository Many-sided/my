import random
import json
from captcha.image import ImageCaptcha
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

# Шаги для диалога
FIRST_STEP, SECOND_STEP, THIRD_STEP, FIFTH_STEP = range(4)

# Админский ID
ADMIN_ID = 569723810  # Замените на свой ID в Telegram

# Генерация капчи с изображением
def generate_captcha():
    captcha_number = str(random.randint(1000, 9999))  # 4 цифры
    image = ImageCaptcha()  # Создаем объект ImageCaptcha
    image_data = image.generate(captcha_number)
    image_path = "captcha_image.png"
    image.write(captcha_number, image_path)
    return image_path, captcha_number

# Функция для сохранения данных
def save_user_data(user_data):
    try:
        with open("user_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    user_id = user_data['user_id']
    data[user_id] = user_data

    with open("user_data.json", "w") as f:
        json.dump(data, f, indent=4)

# Функция начала работы
async def start(update: Update, context):
    # Очищаем контекст перед началом нового цикла
    context.user_data.clear()

    # Кнопка для начала
    start_keyboard = [
        [KeyboardButton("Start")]
    ]
    start_markup = ReplyKeyboardMarkup(start_keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Отправляем сообщение с кнопкой "Старт"
    await update.message.reply_text(
        "Hallo! Klicken Sie auf „Start“, um mit dem Ausfüllen des Formulars zu beginnen. Nach dem Ausfüllen des Formulars wird sich unser Administrator innerhalb von 30 Minuten mit Ihnen in Verbindung setzen.",
        reply_markup=start_markup
    )

    return FIRST_STEP  # Переход к первому шагу

# Шаг 1: Начало анкеты (проверка кнопки)
async def first_step(update: Update, context):
    # Убираем клавиатуру с кнопкой после нажатия
    await update.message.reply_text("Die Formularausfüllung wurde gestartet. Bitte lösen Sie das Captcha!", reply_markup=ReplyKeyboardMarkup([]))

    # Генерация капчи с изображением
    image_path, captcha_answer = generate_captcha()

    # Сохранение капчи и ответа в контексте пользователя
    context.user_data['captcha_answer'] = captcha_answer
    context.user_data['attempts'] = 0  # Счетчик попыток
    context.user_data['user_id'] = update.message.from_user.id  # Сохраняем ID пользователя

    # Отправка капчи с изображением пользователю
    with open(image_path, 'rb') as img_file:
        await update.message.reply_photo(photo=img_file)

    return SECOND_STEP  # Переход к следующему шагу

# Шаг 2: Проверка капчи
async def check_captcha(update: Update, context):
    if 'captcha_answer' not in context.user_data:
        return

    user_input = update.message.text.strip()

    if user_input == context.user_data['captcha_answer']:
        # Капча пройдена успешно, переходим к вопросам
        await update.message.reply_text("Das Captcha wurde erfolgreich gelöst! Lassen Sie uns nun fortfahren.")

        # Переход к следующему шагу
        await update.message.reply_text("Welche Arten von Inhalten gefallen Ihnen am meisten? (z. B. Fotoshootings, Videos, tägliche Updates, Backstage-Momente usw.)")
        return THIRD_STEP
    else:
        context.user_data['attempts'] += 1
        if context.user_data['attempts'] >= 3:
            await update.message.reply_text("Sie haben die maximale Anzahl von Versuchen überschritten.")
            return ConversationHandler.END
        else:
            await update.message.reply_text(f"Falsche Antwort. Sie haben noch verbleibende Versuche. {3 - context.user_data['attempts']} попытки.")
            return SECOND_STEP

# Шаг 3: Вопрос о опыте
async def experience_step(update: Update, context):
    context.user_data['experience'] = update.message.text

    # Переход к следующему вопросу о времени
    await update.message.reply_text("Gibt es etwas Besonderes, das Sie gerne auf der Seite sehen würden? (z. B. bestimmte Themen, Looks, Interaktionen in Nachrichten)?")
    return FIFTH_STEP

# Шаг 5: Вопрос о времени
async def time_commitment_step(update: Update, context):
    context.user_data['time_commitment'] = update.message.text

    # Завершаем анкету и благодарим
    await update.message.reply_text("Vielen Dank für Ihre Registrierung! Alle Daten wurden gespeichert. Unser Administrator wird sich in Kürze mit Ihnen in Verbindung setzen.")

    # Отправка данных админу
    user_data = context.user_data
    message = f"Новый пользователь:\n" \
              f"ID: {user_data['user_id']}\n" \
              f"Имя: {update.message.from_user.username}\n" \
              f"Опыт: {user_data['experience']}\n" \
              f"Время: {user_data['time_commitment']}"

    await context.bot.send_message(ADMIN_ID, message)

    # Сохранение данных в файл
    save_user_data(user_data)

    # Сброс контекста
    context.user_data.clear()

    # После завершения анкеты возвращаем кнопку "Start", чтобы начать новый цикл
    start_keyboard = [
        [KeyboardButton("Старт")]  # Кнопка Старт снова для нового цикла
    ]
    start_markup = ReplyKeyboardMarkup(start_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Der Vorgang ist abgeschlossen. Klicken Sie auf „Start“, um einen neuen Zyklus zu beginnen.",
        reply_markup=start_markup
    )

    return FIRST_STEP  # Вернемся к началу, чтобы начать новый цикл

# Основная функция для настройки бота
def main():
    application = Application.builder().token("7735044850:AAFtQ7MEAA9gBffGS1nWyetWI7-VN9v2G5Y").build()

    # Обработчик сообщений
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_step)],  # Проверка кнопки Старт
            SECOND_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha)],  # Проверка капчи
            THIRD_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, experience_step)],  # Вопрос о опыте
            FIFTH_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_commitment_step)],  # Вопрос о времени
        },
        fallbacks=[],
    )

    application.add_handler(conversation_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
