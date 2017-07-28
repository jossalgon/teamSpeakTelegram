# -*- coding: utf-8 -*-
import pymysql
import ts3
from ts3.examples.viewer import ChannelTreeNode
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
import configparser
import logging
import uuid

from teamSpeakTelegram import _

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
                  `Ts_id` int(11) \
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; \
                CREATE TABLE IF NOT EXISTS `TsMentions` ( \
                  `Group_id` text NOT NULL, \
                  `User_id` int(11) NOT NULL \
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; \
                CREATE TABLE IF NOT EXISTS `Invitations` ( \
                  `token` text NOT NULL, \
                  `usedBy` int(11) \
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


def get_user_ids():
    res = ""
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT Telegram_id FROM TsUsers")
            res = [user_id[0] for user_id in cur.fetchall()]
    except Exception as exception:
        print(str(exception))
    finally:
        if con:
            con.close()
        return res


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


def ts_view(bot, update, message_id=None, chat_id=None):
    message = update.message
    if is_allow(update.effective_user.id):
        res = get_ts_view()

        keyboard = [[InlineKeyboardButton(_("Update"), callback_data='TS_UPDATE')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if message_id and chat_id:
            bot.edit_message_text(text=res, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup,
                                  parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, res, reply_to_message_id=message.message_id, reply_markup=reply_markup,
                             parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, _("You aren't allow to use this"), reply_to_message_id=message.message_id)


def get_ts_view():
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        channel_tree = ChannelTreeNode.build_tree(ts3conn, sid=1)
        res = channel_tree_to_str(channel_tree)
    return res


def channel_tree_to_str(channel_tree, indent=0):
    res = ""
    if channel_tree.is_root():
        res += " " * (indent * 3) + "👁‍🗨" + channel_tree.info["virtualserver_name"]
    else:
        res += "\n" + " " * (indent * 3) + "▫️" + channel_tree.info["channel_name"]
        for client in channel_tree.clients:
            # Ignore query clients
            if client["client_type"] == "1":
                continue
            res += "\n" + " " * (indent * 3 + 3) + "🔘 *" + client["client_nickname"] + "*"
    for child in channel_tree.childs:
        if len(child.clients) > 0:
            res += channel_tree_to_str(child, indent=indent + 1)
    return res


def ts_stats():
    try:
        ts_users = ts_connect()
        text = '👁‍🗨 ' + _('Users online:') + '\n'
        if len(ts_users) == 0:
            text = _('There is no one right now')
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
                return '✅ ' + _('Activated mentions')
            else:
                cur.execute('DELETE FROM TsMentions WHERE Group_id = %s and User_id = %s', (str(group_id), str(user_id)))
                return '❎ ' + _('Disabled mentions')
    except Exception:
        logger.error('Fatal error in mention_toggle', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()


def add_user(user_id, name):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("INSERT INTO TsUsers Values(%s, %s, 0)", (str(user_id), str(name)))
    except Exception:
        logger.error('Fatal error in add_user', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()


def generate_invitation():
    token = str(uuid.uuid4())
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("INSERT INTO Invitations(token) Values(%s)", (str(token),))
        return token
    except Exception:
        logger.error('Fatal error in add_user', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()


def validate_invitation_token(token, user_id, name):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM Invitations WHERE token=%s AND usedBy IS NULL LIMIT 1)", (str(token)))
            valid = bool(cur.fetchone()[0])
            if valid:
                cur.execute("UPDATE Invitations SET usedBy=%s WHERE token=%s", (str(user_id), str(token)))
                cur.execute("INSERT INTO TsUsers Values(%s, %s, 0)", (str(user_id), str(name)))
                return True
    except Exception:
        logger.error('Fatal error in mention_toggle', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()


def callback_query_handler(bot, update):
    query_data = update.callback_query.data
    if query_data.startswith('TS_UPDATE'):
        a = get_ts_view()
        if a == update.effective_message.text_markdown:
            bot.answer_callback_query(update.callback_query.id, _('No changes'))
        else:
            ts_view(bot, update, message_id=update.effective_message.message_id, chat_id=update.effective_chat.id)
            bot.answer_callback_query(update.callback_query.id, _('Successfully updated'))