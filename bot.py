from time import sleep
from requests import post, get
from datetime import datetime as dt, timedelta as td
from random import randint
from os import getcwd, listdir, environ
from os.path import isfile
import logging
import telebot as tb

bot = tb.TeleBot(open('.token').read().strip(), parse_mode='MARKDOWN')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, f'''Здарова, {message.from_user.username}''')

if __name__ == '__main__':
    bot.infinity_polling()
