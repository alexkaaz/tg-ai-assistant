from yandex_cloud_ml_sdk import YCloudML
import telebot

bot = telebot.TeleBot(bot_key)

sdk = YCloudML(folder_id=folder_id, auth=yandex_key)

thread = sdk.threads.create(name="SimpleAssistant", ttl_days=5, expiration_policy="static")
text_model = sdk.models.completions("yandexgpt", model_version="rc")
assistant = sdk.assistants.create(text_model, ttl_days=4, expiration_policy="since_last_active", max_tokens=500)

image_model = sdk.models.image_generation("yandex-art")
image_model = image_model.configure(width_ratio=1, height_ratio=1, seed=1863)

user_states = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
            Привет! Я ИИ-ассистент. Выбери режим работы:
            /image_generator - буду ждать текст для генерации изображения.
            /text - перейду в режим обычного текстового общения.
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['image_generator'])
def set_image_mode(message):
    user_id = message.from_user.id
    user_states[user_id] = 'waiting_for_image_prompt'
    bot.reply_to(message, "Режим генерации изображений активирован. Отправь мне текстовое описание картинки.")


@bot.message_handler(commands=['text'])
def set_text_mode(message):
    user_id = message.from_user.id
    user_states[user_id] = 'text_mode'
    bot.reply_to(message, "Режим текстового ассистента активирован. Задавай свой вопрос.")

@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    user_id = message.from_user.id
    bot.send_chat_action(message.chat.id, 'typing')
    current_state = user_states.get(user_id, 'text_mode')  

    if current_state == 'waiting_for_image_prompt':
        user_prompt = message.text
        operation = image_model.run_deferred(user_prompt)
        result = operation.wait()
        bot.send_photo(message.chat.id, result.image_bytes)
    elif current_state == 'text_mode':
        user_input = message.text
        thread.write(user_input)
        text = assistant.run(thread)
        result = text.wait()
        bot.send_message(message.chat.id, text=result.parts)

print("Бот запущен...")
bot.infinity_polling()
