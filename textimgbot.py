from yandex_cloud_ml_sdk import YCloudML
import telebot
import os
import tempfile
from docx import Document
import PyPDF2
import pdfplumber

bot_key = os.getenv('bot_key')
folder_id = os.getenv('folder_id')
y_key = os.getenv('yandex_key')

bot = telebot.TeleBot(bot_key)

sdk = YCloudML(folder_id=folder_id,
               auth=y_key
)

thread = sdk.threads.create(name="SimpleAssistant", ttl_days=5, expiration_policy="static")
text_model = sdk.models.completions("yandexgpt", model_version="rc")
assistant = sdk.assistants.create(text_model, ttl_days=4, expiration_policy="since_last_active", max_tokens=500)

image_model = sdk.models.image_generation("yandex-art")
image_model = image_model.configure(width_ratio=1, height_ratio=1, seed=1863)

user_states = {}

def text_response(message):
    thread.write(message)
    text = assistant.run(thread)
    result = text.wait()
    return result.parts

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
    chat_id = message.chat.id
    bot.send_chat_action(message.chat.id, 'typing')
    current_state = user_states.get(user_id, 'text_mode')
    user_input = message.text

    if current_state == 'waiting_for_image_prompt':
        operation = image_model.run_deferred(user_input)
        result = operation.wait()
        bot.send_photo(chat_id, result.image_bytes)
    elif current_state == 'text_mode':
        response = text_response(user_input)
        bot.send_message(chat_id, text=response)

def read_file(file_path):
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.endswith('.pdf'):
            text = ''
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            return text
        elif file_path.endswith('.doc') or file_path.endswith('.docx'):
            doc = Document(file_path)
            text = ''
            for p in doc.paragraphs:
                if p.text.strip():
                    text += p.text + '\n'
            return text
    except Exception as e:
        return f"Ошибка чтения файла: {str(e)}"   

@bot.message_handler(content_types=['document'])
def handle_docs_photo(message):
    chat_id = message.chat.id

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = message.document.file_name;
    if not file_name:
        file_name = f'document_{message.document.file_id}'
    save_path = os.path.join('delete later', file_name)
    with open(save_path, 'wb') as new_file:
        new_file.write(downloaded_file)
    file_text = read_file(save_path)
    user_text = message.caption + ' ' + file_text
    response = text_response(user_text)
    os.remove(save_path)
    bot.send_message(chat_id, response)

print("Бот запущен...")
bot.infinity_polling()


























