#!/home/tolord/cardholder-env/bin/python3
from time import sleep
from requests import post, get
from datetime import datetime as dt, timedelta as td
from random import randint
from os import getcwd, listdir, environ, getenv, makedirs
from os.path import isfile, join, exists
from models import create_user, add_shortcut, get_user, get_shortcuts, delete_shortcut, get_shortcut, is_admin, get_users_list, increase_chosen_result_counter
from random import sample
from traceback import print_exception, format_exc
from json import loads, JSONDecodeError
from dotenv import load_dotenv
import logging
import telebot as tb

# Load environment variables from .env file
load_dotenv()

# Set log directory
log_directory = getenv('LOGPATH') + f'/{dt.today().date().isoformat()}'
if not exists(log_directory):
    makedirs(log_directory)

# Set name of log-file
log_file_name = "error.log"

# Set full name of log-file
log_file_path = join(log_directory, log_file_name)

# Setting of logger
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

bot = tb.TeleBot(getenv('TGTOKEN').strip())

help_message = '''Here are methods you can use:
/help - send this message
/list - list all existing shortcuts
/add - add a new shortcut
/delete - delete an existing shortcut by its name

Send any feedback (questions, feature requests) to @tolord'''

error_msg = 'Sorry, something went wrong. If you see this message, text to my creator please: @tolord'

def get_first_or_obj(obj):
    """Returns first element of an object if it is a collection else the same object"""
    try:
        return obj[0]
    except Exception:
        return obj

def get_input_media_by_type(type_name: str) -> tb.types.InputMedia:
    """Gets a name of a media type, returns corresponding Telegram Object Class"""
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
    """Creates Telegram Object by Shortcut description"""
    content_class = get_input_media_by_type(shortcut.content_type)

    if shortcut.content_type not in ('text', 'location'):
        params = {
            f'''{shortcut.content_type if shortcut.content_type != 'animation' else 'mpeg4'}_file_id''': shortcut.content, 
            'parse_mode': '',
            'caption': shortcut.text,
            'description': shortcut.shortcut_name,
            'caption_entities': tb.types.Message.parse_entities(shortcut.entities or [])
        }
    elif shortcut.content_type == 'location':
        params = {**loads(shortcut.content)}
    else:
        params = {
            'input_message_content': tb.types.InputTextMessageContent(
                shortcut.text, 
                entities=tb.types.Message.parse_entities(shortcut.entities or []),
                parse_mode=''
            )
        }
    params['id'] = shortcut.id
    params['title'] = shortcut.shortcut_name
    
    return content_class(**params)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Send welcome-message when a user send a command at the first time else help-message with a list of available commands."""
    logging.info(f'''{message.from_user.username or message.from_user.id}: {message.text}''')
    if get_user(message.from_user.id):
        bot.reply_to(message=message, text=help_message)
    else:
        params = message.text.split(maxsplit=1)
        start_param = params[1] if len(params) > 1 else None
        create_user(telegram_id=message.from_user.id, username=message.from_user.username, start_param=start_param)
        bot.reply_to(message=message, text=f'''Hi, {message.from_user.first_name} {message.from_user.last_name}! I'm Shortcut Holder, and I will help you to quickly send any frequently used information (I call it Shortcut) to whoever you want very easy. I'll show you how to do it real quick. Just click here right now: /add''')


@bot.message_handler(commands=['add'])
def handle_add_shortcut(message):
    """Ask a content for a new Shortcut, then a name for it. Create a corresponding object in DB"""
    logging.info(f'''{message.from_user.username or message.from_user.id}: add''')
    msg = bot.reply_to(
        message=message, 
        text='''Send me any one message you want\. It can be a text and/or one of the following media types audio, document, video, voice message, location or poll\. Also, you can use formatting styles in your shortcuts: _italic_, *bold*, __underlined__, ~striked~, `code` and [links](https://core\.telegram\.org/api/entities)\.
To begin with, *you* can send me your _business_ card like this one:
```Name: Shortcut Holder
Position: Telegram Bot
Company: Shortcut Holder LLC
Email: i@t010rd\.ru```''',
        parse_mode='MarkdownV2'
    )
    bot.register_next_step_handler(msg, process_add_shortcut_content)

def process_add_shortcut_content(message):
    """Ask for a name for a new shortcut"""
    try:
        msg = bot.reply_to(message, f'''{sample(['Great', 'Magnificent', 'Fantastic', 'Wonderful'], k=1)[0]}! Now give me a short name for your shortcut:''')
        bot.register_next_step_handler(msg, process_add_shortcut_name(message))
    except Exception as e:
        print_exception(e)
        bot.reply_to(message=message, text=error_msg)

def process_add_shortcut_name(prev_message):
    """Parse message for a Shortcut parameters"""
    context = {
        'text': prev_message.text if prev_message.content_type == 'text' else prev_message.caption,
        'content_type': prev_message.content_type,
        'content': get_first_or_obj(getattr(prev_message, prev_message.content_type)).file_id if prev_message.content_type not in ('text', 'location') \
                    else prev_message.location.to_json() if prev_message.content_type == 'location' \
                    else None,
        'entities': [x.to_json() for x in prev_message.entities or []]
    }
    def inner(message):
        """Save a Shortcut to BD"""
        try:
            context['telegram_id'] = message.from_user.id
            context['shortcut_name'] = message.text
            add_shortcut(**context)
            bot.reply_to(message=message, text=f'Shortcut "{message.text}" was successfully saved!')
            logging.info(f'''{message.from_user.username or message.from_user.id}: added {context['content_type']} shortcut''')
        except Exception as e:
            print_exception(e)
            bot.reply_to(message=message, text=error_msg)
    return inner

@bot.message_handler(commands=['list'])
def list_shortcuts_handler(message):
    """List all stored Shortcuts of a user"""
    logging.info(f'''{message.from_user.username or message.from_user.id}: list''')
    shortcuts = get_shortcuts(message.from_user.id)
    if shortcuts:
        bot.reply_to(message=message, text=f'You have {len(shortcuts)} in total, here they are:')
        for i, shortcut in enumerate(shortcuts, start=1):
            prev_message = bot.send_message(chat_id=message.from_user.id, text=f'{i}. `{shortcut.shortcut_name}`:', parse_mode='Markdown')
            if shortcut.content_type == 'text':
                bot.reply_to(
                    message=prev_message, 
                    text=shortcut.text, 
                    parse_mode='', 
                    entities=prev_message.parse_entities(shortcut.entities or [])
                )
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
                        'chat_id': message.from_user.id,
                        'caption_entities': message.parse_entities(shortcut.entities or []),
                        'parse_mode': ''
                    }
                )
    else:
        bot.reply_to(message=message, text='''You don't have any shortcuts, but you can simply add one by clicking here: /add''')

@bot.message_handler(commands=['delete'])
def delete_shortcut_handler(message):
    """Ask which Shortcut from list of available Shortcuts to delete"""
    logging.info(f'''{message.from_user.username or message.from_user.id}: delete''')
    shortcuts = get_shortcuts(message.from_user.id)
    if shortcuts:
        kb = tb.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for i in range(0, len(shortcuts), 2):
            kb.add(*[f'"{x.shortcut_name}"' for x in shortcuts[i: i + 2]])
        kb.add('Cancel')
        msg = bot.reply_to(message=message, text='''Which shortcut do you want to delete?''', reply_markup=kb)
        bot.register_next_step_handler(msg, process_delete_shortcut)
    else:
        bot.reply_to(message=message, text='''You don't have any shortcuts, but you can simply add one by clicking here: /add''')

def process_delete_shortcut(msg):
    """Delete chosen Shortcut or cancel if 'Cancel' option was chosed"""
    shortcut = get_shortcut(telegram_id=msg.from_user.id, shortcut_name=msg.text[1:-1])
    if shortcut:
        delete_shortcut(shortcut.id)
        bot.reply_to(message=msg, text=f'''Shortcut `{shortcut.shortcut_name}` was successfully deleted!''', reply_markup=tb.types.ReplyKeyboardRemove())
    elif msg.text == 'Cancel':
        bot.reply_to(message=msg, text='Deletion was cancelled', reply_markup=tb.types.ReplyKeyboardRemove())
    else:
        bot.reply_to(message=msg, text='Please, use the Telegram keyboard')


@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    """List all shortcuts filtered by text and sorted by use"""
    logging.info(f'''{inline_query.from_user.username or inline_query.from_user.id}: inline ({inline_query.query})''')
    shortcuts = get_shortcuts(telegram_id=inline_query.from_user.id)
    found_shortcuts = [shortcut for shortcut in shortcuts if inline_query.query in shortcut.shortcut_name] or shortcuts
    results = []
    for shortcut in sorted(found_shortcuts, key=lambda shortcut: shortcut.num_of_uses)[::-1]:
        try:        
            r = get_input_content(shortcut)
        except JSONDecodeError as e:
            logging.error(shortcut.content_type)
            logging.error(shortcut.content)
            logging.error(format_exc())
        results.append(r)
    if not found_shortcuts:
        results.append(
            tb.types.InlineQueryResultArticle(
                id='1',
                title='Test shortcut',
                input_message_content=tb.types.InputTextMessageContent(
                    message_text='This is a test shortcut. It will disappear from your search results when you add your first own shortcut in direct messages of @shortcut_robot.'
                )
            )
        )
    bot.answer_inline_query(
        inline_query.id, 
        results, 
        cache_time=1, 
        is_personal=True,
        switch_pm_parameter='from_menu',
        switch_pm_text='Add a new shortcut' if found_shortcuts else 'Add your own shortcut'
    )

@bot.chosen_inline_handler(lambda query: True)
def handle_chosen_shortcut(chosen_result):
    """Increase number of uses of a Shortcut and update last use datetime"""
    increase_chosen_result_counter(chosen_result.result_id)
    

@bot.message_handler(commands=['get_users'])
def admin_get_users(message):
    """List all the users with reg dates, # of saved shortcuts and source of registration (only for admins)"""
    if is_admin(message.from_user.id):
        result = '\n'.join(
                [f'''`{str(values[0]).split(".")[0]}`: \t ({values[1]}) {("" if user_id[0].isdigit() else "@") + user_id} [{values[2] or ''}]''' for user_id, values in get_users_list().items()]
        ).replace('_', '\_')
        bot.reply_to(
            message=message, 
            text=result,
            parse_mode='markdown'
        )

if __name__ == '__main__':
    bot.infinity_polling()
