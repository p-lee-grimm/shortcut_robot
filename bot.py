#!/home/tolord/cardholder-env/bin/python3
from time import sleep
from requests import post, get
from datetime import datetime as dt, timedelta as td
from random import randint
from os import getcwd, listdir, environ
from os.path import isfile
from models import create_user, add_shortcut, get_user, get_shortcuts, delete_shortcut, get_shortcut
from random import sample
from traceback import print_exception
import logging
import telebot as tb

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
        'file_id': get_first_or_obj(getattr(prev_message, prev_message.content_type)).file_id if prev_message.content_type != 'text' else None
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
            else:
                getattr(bot, f'send_{shortcut.content_type}')(
                    **{
                        shortcut.content_type: shortcut.file_id, 
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
    print('wanna delete')
    shortcut = get_shortcut(telegram_id=msg.from_user.id, shortcut_name=msg.text)
    print(shortcut.id)
    if shortcut:
        delete_shortcut(shortcut.id)
        bot.reply_to(message=msg, text=f'''Shortcut `{shortcut.shortcut_name}` was successfully deleted!''', reply_markup=tb.types.ReplyKeyboardRemove())
    else:
        bot.reply_to(message=msg, text='Please, use the Telegram keyboard')

if __name__ == '__main__':
    bot.infinity_polling()
