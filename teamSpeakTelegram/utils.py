# -*- coding: utf-8 -*-
import pymysql
import ts3
import configparser
import logging

config = configparser.ConfigParser()
config.read('config.ini')
ts_host = config['TS']['ts_host']
ts_user = config['TS']['ts_user']
ts_pass = config['TS']['ts_pass']
DB_HOST = config['Database']['DB_HOST']
DB_USER = config['Database']['DB_USER']
DB_PASS = config['Database']['DB_PASS']
DB_NAME = config['Database']['DB_NAME']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def create_database():
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS `TsUsers` ( \
                  `Telegram_id` int(11) NOT NULL, \
                  `Name` text NOT NULL, \
                  `Ts_id` int(11) NOT NULL \
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; \
                CREATE TABLE IF NOT EXISTS `TsMentions` ( \
                  `Group_id` text NOT NULL, \
                  `User_id` int(11) NOT NULL \
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
    except Exception as exception:
        print(str(exception))
    finally:
        if con:
            con.commit()
            con.close()


def is_allow(user_id):
    allow = False
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM TsUsers WHERE Telegram_id=%s LIMIT 1)", (str(user_id),))
            allow = bool(cur.fetchone()[0])
    except Exception as exception:
        print(str(exception))
    finally:
        if con:
            con.close()
        return allow


def get_name(ts_id):
    name = None
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT Name FROM TsUsers WHERE Ts_id=%s", (str(ts_id),))
            name = cur.fetchone()
            name = name[0] if name is not None else None

    except Exception as exception:
        print(str(exception))
    finally:
        if con:
            con.close()
        return name


def ts_connect():
    clients = []
    with ts3.query.TS3Connection(ts_host) as ts3conn:
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


def ts_stats():
    try:
        ts_users = ts_connect()
        text = '👁‍🗨 Conectados:\n'
        if len(ts_users) == 0:
            text = 'No hay nadie ahora mismo'
        else:
            for client in ts_users:
                text += '%s\n' % client
        return text
    except Exception as exception:
        return exception


def get_mention_users_by_group(group_id):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    mention_users = list()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT User_id FROM TsMentions WHERE Group_id = %s", (str(group_id),))
            rows = cur.fetchall()
            for row in rows:
                mention_users.append(row[0])
    except Exception as exception:
        print(exception)
    finally:
        if con:
            con.close()
        return mention_users


def mention_forwarder(bot, update):
    message = update.message
    group_id = message.chat_id
    user_ids = get_mention_users_by_group(group_id)
    for user_id in user_ids:
        try:
            bot.forward_message(user_id, group_id, message.message_id)
        except:
            pass


def mention_toggle(group_id, user_id):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM TsMentions WHERE Group_id=%s and User_id=%s LIMIT 1)",
                        (str(group_id), str(user_id)))
            mention = bool(cur.fetchone()[0])
            if not mention:
                cur.execute("INSERT INTO TsMentions VALUES (%s, %s)", (str(group_id), str(user_id)))
                return '✅ Menciones activadas'
            else:
                cur.execute('DELETE FROM TsMentions WHERE Group_id = %s and User_id = %s', (str(group_id), str(user_id)))
                return '❎ Menciones desactivadas'
    except Exception:
        logger.error('Fatal error in mention_toggle', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()
