#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import ts3
import telebot
import configparser
import time
import sqlite3 as lite

import create_database

create_database
config = configparser.ConfigParser()
config.read('config.ini')
token_id = config['Telegram']['token_id']
ts_user = config['Telegram']['ts_user']
ts_pass = config['Telegram']['ts_pass']

bot = telebot.TeleBot(token_id)


def is_allow(user_id):
    try:
        path = 'data.db'
        con = lite.connect(path)
        with con:
            cur = con.cursor()
            allow = cur.execute("SELECT EXISTS(SELECT 1 FROM Users WHERE Telegram_id=? LIMIT 1)", (user_id,)).fetchone()[0]
            return bool(allow)
    except Exception as e:
        print(str(e))
        return False


def get_name(ts_id):
    try:
        path = 'data.db'
        con = lite.connect(path)
        with con:
            cur = con.cursor()
            name = cur.execute("SELECT Name FROM Users WHERE Ts_id=?", (ts_id,)).fetchone()[0]
            return name
    except Exception as e:
        print(str(e))

while True:
    try:
        def ts_connect():
            clients = []
            with ts3.query.TS3Connection("localhost") as ts3conn:
                # Note, that the client will wait for the response and raise a
                # **TS3QueryError** if the error id of the response is not 0.
                try:
                    ts3conn.login(
                        client_login_name=ts_user,
                        client_login_password=ts_pass
                    )
                except ts3.query.TS3QueryError as err:
                    print("Login failed:", err.resp.error["msg"])
                    exit(1)

                ts3conn.use(sid=1)
                resp = ts3conn.clientlist()
                for client in resp.parsed:
                    db_id = int(client['client_database_id'])
                    # ID 1 IS SERVERADMIN
                    if db_id != 1:
                        name = get_name(db_id)
                        if name is not None:
                            clients.append(name)
                        else:
                            clients.append(client['client_nickname'])
            return clients

        @bot.message_handler(commands=['start'])
        def start(message):
            bot.reply_to(message, 'Welcome!!')

        @bot.message_handler(commands=['ts'], func=lambda msg: is_allow(msg.from_user.id))
        def ts_stats(message):
            try:
                ts_users = ts_connect()
                text = '👁‍🗨 Conectados:\n'
                if len(ts_users) == 0:
                    text = 'No hay nadie ahora mismo'
                else:
                    for client in ts_users:
                        text += '%s\n' % client
                bot.reply_to(message, text)
            except Exception as e:
                print(str(e))

        bot.polling(none_stop=True)
    except Exception as e:
        print(str(e))
        time.sleep(10)
