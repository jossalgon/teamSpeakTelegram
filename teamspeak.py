#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import telebot
import configparser
import time

from src.utils import Utils

utils = Utils()

config = configparser.ConfigParser()
config.read('config.ini')
token_id = config['Telegram']['token_id']

utils.create_database()

bot = telebot.TeleBot(token_id)


while True:
    try:
        @bot.message_handler(commands=['start'])
        def start(message):
            bot.reply_to(message, 'Welcome!!')

        @bot.message_handler(commands=['ts'], func=lambda msg: utils.is_allow(msg.from_user.id))
        def ts_stats(message):
            stats = utils.ts_stats()
            bot.reply_to(message, stats)

        bot.polling(none_stop=True)
    except Exception as e:
        print(str(e))
        time.sleep(10)
