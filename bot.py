#!/home/tolord/cardholder-env/bin/python3
from time import sleep
from requests import post, get
from datetime import datetime as dt, timedelta as td
from random import randint
from os import getcwd, listdir, environ, getenv, makedirs
from os.path import isfile, join, exists
from models import create_user, add_shortcut, get_user, get_shortcuts, delete_shortcut, get_shortcut
from random import sample
from traceback import print_exception, format_exc
from json import loads, JSONDecodeError
from dotenv import load_dotenv
import logging
import telebot as tb

load_dotenv()

log_directory = getenv('LOGPATH') + f'/{dt.today().date().isoformat()}'
if not exists(log_directory):
    makedirs(log_directory)

# Имя лог-файла
log_file_name = "error.log"

# Полный путь к файлу
log_file_path = join(log_directory, log_file_name)

# Настройка логгера
logging.basicConfig(
    level=logging.ERROR,  # Уровень логгирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
    datefmt='%Y-%m-%d %H:%M:%S',  # Формат времени
    handlers=[
        logging.FileHandler(log_file_path),  # Обработчик для записи в файл
        logging.StreamHandler()  # Также можно настроить вывод в консоль
    ]
)

bot = tb.TeleBot(environ.get('TGTOKEN').strip())

help_message = f'''Here are methods you can use:
/help - send this message
/list - list all existing shortcuts
/add - add a new shortcut
/update - update an existing shortcut
/delete - delete an existing shortcut by its name

Send any feedback (questions, feature requests) to @tolord'''

error_msg = 'Sorry, something went wrong. If you see this message, text to my creator please: @tolord'

def get_first_or_obj(obj):
    try:
        return obj[0]
    except Exception:
        return obj

def get_input_media_by_type(type_name: str) -> tb.types.InputMedia:
    return {
        'photo': tb.types.InlineQueryResultCachedPhoto,
        'video': tb.types.InlineQueryResultCachedVideo,
        'animation': tb.types.InlineQueryResultCachedMpeg4Gif,
        'document': tb.types.InlineQueryResultCachedDocument,
        'audio': tb.types.InlineQueryResultCachedAudio,
        'location': tb.types.InlineQueryResultLocation,
        'text': tb.types.InlineQueryResultArticle
    }.get(type_name)

def get_input_content(shortcut):
    content_class = get_input_media_by_type(shortcut.content_type)
    params = {
        f'''{shortcut.content_type if shortcut.content_type != 'animation' else 'mpeg4'}_file_id''': shortcut.content, 
        'caption': shortcut.text,
        'description': shortcut.shortcut_name
    } if shortcut.content_type not in ('text', 'location') \
    else {**loads(shortcut.content)} if shortcut.content_type == 'location' \
    else {'input_message_content': tb.types.InputTextMessageContent(shortcut.text)}
    params['id'] = shortcut.id
    params['title'] = shortcut.shortcut_name
    
    return content_class(**params)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if get_user(message.from_user.id):
        bot.reply_to(message=message, text=help_message)
    else:
        create_user(telegram_id=message.from_user.id, username=message.from_user.username)
        bot.reply_to(message=message, text=f'''Hi, {message.from_user.first_name} {message.from_user.last_name}! I'm Shortcut Holder, and I will help you to quickly send any frequently used information (I call it Shortcut) to whoever you want very easy. I'll show you how to do it real quick. Just click here right now: /add_shortcut''')


@bot.message_handler(commands=['add'])
def handle_add_shortcut(message):
    msg = bot.reply_to(
        message=message, 
        text='''Send me any one message you want. It can be a text and/or one of the following media types audio, document, video, voice message, location or poll. E.g. you can send me your __business__ card like this one:
```Name: Shortcut Holder
Position: Telegram Bot
Company: Shortcut Holder LLC
Email: i@t010rd.ru```''',
        parse_mode='markdown'
    )
    bot.register_next_step_handler(msg, process_add_shortcut_content)

def process_add_shortcut_content(message):
    try:
        msg = bot.reply_to(message, f'''{sample(['Great', 'Magnificent', 'Fantastic', 'Wonderful'], k=1)[0]}! Now give me a short name for your shortcut:''')
        bot.register_next_step_handler(msg, process_add_shortcut_name(message))
    except Exception as e:
        print_exception(e)
        bot.reply_to(message=message, text=error_msg)

def process_add_shortcut_name(prev_message):
    context = {
        'text': prev_message.text if prev_message.content_type == 'text' else prev_message.caption,
        'content_type': prev_message.content_type,
        'content': get_first_or_obj(getattr(prev_message, prev_message.content_type)).file_id if prev_message.content_type not in ('text', 'location') else prev_message.location.to_json() if prev_message.content_type == 'location' else None
    }
    def inner(message):
        try:
            context['telegram_id'] = message.from_user.id
            context['shortcut_name'] = message.text
            add_shortcut(**context)
            bot.reply_to(message=message, text=f'Shortcut "{message.text}" was successfully saved!')
        except Exception as e:
            print_exception(e)
            bot.reply_to(message=message, text=error_msg)
    return inner

@bot.message_handler(commands=['list'])
def list_shortcuts_handler(message):
    shortcuts = get_shortcuts(message.from_user.id)
    if shortcuts:
        bot.reply_to(message=message, text=f'You have {len(shortcuts)} in total, here they are:')
        for i, shortcut in enumerate(shortcuts, start=1):
            prev_message = bot.send_message(chat_id=message.from_user.id, text=f'{i}. `{shortcut.shortcut_name}`:', parse_mode='markdown')
            if shortcut.content_type == 'text':
                bot.reply_to(message=prev_message, text=shortcut.text)
            elif shortcut.content_type == 'location':
                try:
                    bot.send_location(
                        reply_to_message_id=prev_message.id,
                        chat_id=message.from_user.id,
                        **loads(shortcut.content)
                    )
                except JSONDecodeError as e:
                    logging.error(shortcut.content_type)
                    logging.error(shortcut.content)
                    logging.error(format_exc(), exc_info=True)
            else:
                getattr(bot, f'send_{shortcut.content_type}')(
                    **{
                        shortcut.content_type: shortcut.content, 
                        'caption': shortcut.text, 
                        'reply_to_message_id': prev_message.id,
                        'chat_id': message.from_user.id
                    }
                )
    else:
        bot.reply_to(message=message, text='''You don't have any shortcuts, but you can simply add one by clicking here: /add''')

@bot.message_handler(commands=['delete'])
def delete_shortcut_handler(message):
    shortcuts = get_shortcuts(message.from_user.id)
    if shortcuts:
        kb = tb.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for i in range(0, len(shortcuts), 2):
            kb.add(*[x.shortcut_name for x in shortcuts[i: i + 2]])
        msg = bot.reply_to(message=message, text='''Which shortcut do you want to delete?''', reply_markup=kb)
        bot.register_next_step_handler(msg, process_delete_shortcut)
    else:
        bot.reply_to(message=message, text='''You don't have any shortcuts, but you can simply add one by clicking here: /add''')

def process_delete_shortcut(msg):
    shortcut = get_shortcut(telegram_id=msg.from_user.id, shortcut_name=msg.text)
    if shortcut:
        delete_shortcut(shortcut.id)
        bot.reply_to(message=msg, text=f'''Shortcut `{shortcut.shortcut_name}` was successfully deleted!''', reply_markup=tb.types.ReplyKeyboardRemove())
    else:
        bot.reply_to(message=msg, text='Please, use the Telegram keyboard')


@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    shortcuts = get_shortcuts(telegram_id=inline_query.from_user.id)
    found_shortcuts = [shortcut for shortcut in shortcuts if inline_query.query in shortcut.shortcut_name] or shortcuts
    results = []
    for i, shortcut in enumerate(found_shortcuts):
        logging.info(shortcut.content)
        try:        
            r = get_input_content(shortcut)
        except JSONDecodeError as e:
            logging.error(shortcut.content_type)
            logging.error(shortcut.content)
            logging.error(format_exc())
        results.append(r)
    bot.answer_inline_query(inline_query.id, results, cache_time=1, is_personal=True)


if __name__ == '__main__':
    bot.infinity_polling()
