# -*- coding: utf-8 -*-
import math
import pymysql
import ts3
from telegram import ForceReply
from telegram import TelegramError
from ts3.examples.viewer import ChannelTreeNode
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
import configparser
import logging
import uuid
from datetime import datetime

from teamSpeakTelegram import user_language, _

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

ADMIN_ID = config.getint('Telegram', 'admin_id') if config.has_option('Telegram', 'admin_id') else None


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
            cur.execute("SELECT Telegram_id FROM TsUsers WHERE Telegram_id != 0")
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


@user_language
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
            alias = get_name(client["client_database_id"])
            nickname = alias if alias is not None else client["client_nickname"]
            res += "\n" + " " * (indent * 3 + 3) + "🔘 *" + nickname + "*"
    for child in channel_tree.childs:
        if len(child.clients) > 0:
            res += channel_tree_to_str(child, indent=indent + 1)
    return res


@user_language
def ts_stats(bot, update):
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

    if is_allow(message.from_user.id):
        user_ids = get_mention_users_by_group(group_id)
        for user_id in user_ids:
            try:
                bot.forward_message(user_id, group_id, message.message_id)
            except:
                pass


@user_language
def mention_toggle(bot, update, group_id, user_id):
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


def add_user(user_id, name, ts_id=0):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            cur.execute("INSERT INTO TsUsers Values(%s, %s, %s)", (str(user_id), str(name), str(ts_id)))
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


def assign_name_tsid(telegram_id, name, ts_id):
    con = pymysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with con.cursor() as cur:
            if int(telegram_id) != 0:
                cur.execute("UPDATE TsUsers SET Name=%s, Ts_id=%s WHERE Telegram_id=%s",
                            (str(name), str(ts_id), str(telegram_id)))
                cur.execute("DELETE FROM TsUsers WHERE Telegram_id=0 AND Ts_id=%s", (str(ts_id),))
            else:
                cur.execute("UPDATE TsUsers SET Name=%s, Telegram_id=%s WHERE Ts_id=%s",
                            (str(name), str(telegram_id), str(ts_id)))
            return True
    except Exception:
        logger.error('Fatal error in assign_tsid', exc_info=True)
    finally:
        if con:
            con.commit()
            con.close()


def get_users_tsdb():
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        users = ts3conn.clientdblist(duration=100000000*999).parsed
        return users


def get_user_ts_info(cldbid):
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        res = ts3conn.clientdbinfo(cldbid=cldbid).parsed[0]

        return res


def check_user_banned(uid=None, ip=None, name=None):
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        banned_users = ts3conn.banlist().parsed
        ban_ids = list()

        for user in banned_users:
            if user['uid'] == uid or user['ip'] == ip or user['name'] == name:
                ban_ids.append(user['banid'])

        return ban_ids


def get_user_clid(cluid):
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        try:
            clid = ts3conn.clientgetids(cluid=cluid).parsed[0]['clid']
            return clid
        except ts3.query.TS3QueryError:
            pass


@user_language
def ban_ts_user(bot, update, chat_data, cldbid, ban_type):
    user = get_user_ts_info(cldbid)
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        if ban_type == 'ID':
            ts3conn.banadd(uid=user['client_unique_identifier'])
        elif ban_type == 'IP':
            ts3conn.banadd(ip=user['client_lastip'])
        else:
            ts3conn.banadd(name=user['client_nickname'])

    bot.answer_callback_query(update.callback_query.id, _('User banned successfully'))
    details_user_ts(bot, update, chat_data, cldbid=int(cldbid))


@user_language
def unban_ts_user(bot, update, chat_data, cldbid, banid):
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        ts3conn.bandel(banid=banid)

        bot.answer_callback_query(update.callback_query.id, _('User unbanned successfully'))
        if cldbid:
            details_user_ts(bot, update, chat_data, cldbid=cldbid)
        else:
            users_tsdb(bot, update, chat_data)


@user_language
def kick_ts_user(bot, update, cldbid, kick_type):
    with ts3.query.TS3Connection(ts_host) as ts3conn:
        try:
            ts3conn.login(
                client_login_name=ts_user,
                client_login_password=ts_pass
            )
        except ts3.query.TS3QueryError as err:
            print("Login failed:", err.resp.error["msg"])
            exit(1)

        ts3conn.use(sid=1)
        try:
            cluid = ts3conn.clientdbinfo(cldbid=cldbid).parsed[0]['client_unique_identifier']
            clid = ts3conn.clientgetids(cluid=cluid).parsed[0]['clid']

            ts3conn.clientkick(reasonid=kick_type, clid=clid, reasonmsg="Kicked from TeamSpeakBot")
            bot.answer_callback_query(update.callback_query.id, _('User kicked successfully'))
        except ts3.query.TS3QueryError:
            bot.answer_callback_query(update.callback_query.id, _('Something went wrong'))


@user_language
def markup_append_pagination(bot, update, items, markup, page, callback):
    pag_max = math.ceil(len(items) / 10)
    pag_button = InlineKeyboardButton(_('Page') + ' %s/%s' % (str(page), str(pag_max)),
                                      callback_data='%s_PG_NEXT' % callback)

    if len(items) >= 5:
        if page == 1:
            sig_button = InlineKeyboardButton(_('Page') + ' %s/%s ⏩' % (str(page), str(pag_max)),
                                              callback_data='%s_PG_NEXT' % callback)
            markup.append([sig_button])

        elif 1 < page < pag_max:
            ant_button = InlineKeyboardButton('⏪ ' + _('Prev'), callback_data='%s_PG_PREV' % callback)
            sig_button = InlineKeyboardButton('⏩ ' + _('Next'), callback_data='%s_PG_NEXT' % callback)
            markup.append([ant_button, pag_button, sig_button])
        elif page == pag_max:
            ant_button = InlineKeyboardButton(_('Page') + ' %s/%s ⏪' % (str(page), str(pag_max)),
                                              callback_data='%s_PG_PREV' % callback)
            markup.append([ant_button])

    return markup


@user_language
def assign_user_alias_step1(bot, update, chat_data, cldbid):
    chat_id = update.effective_chat.id
    text = '🙍‍♂️ ' + _('Ok, give me an *alias* for that user')
    message_sent = bot.send_message(chat_id, text, reply_markup=ForceReply(), parse_mode='Markdown')

    if 'alias_cldbid' not in chat_data:
        chat_data['alias_cldbid'] = dict()
    chat_data['alias_cldbid'][str(message_sent.message_id)] = '', cldbid
    chat_data['bot_update'] = bot, update


@user_language
def assign_user_alias_step2(bot, update, chat_data):
    message = update.effective_message
    chat_id = update.effective_chat.id
    markup = []

    first_message = bool(update.message)
    page = chat_data[message.message_id]['pages'] if not first_message else 1

    user_ids = get_user_ids()

    start = 10 * (page - 1) if page > 1 else 0
    end = start + 10 if start + 10 < len(user_ids) else len(user_ids)
    for i in range(start, end, 2):
        j = i + 1
        try:
            user1 = bot.get_chat_member(chat_id=user_ids[i], user_id=user_ids[i]).user
            username1 = '@' + user1.username if user1.username else user1.first_name
        except TelegramError:
            username1 = 'ID: ' + str(user_ids[i])
        row = [InlineKeyboardButton(username1, callback_data='USER_ALIAS_%s' % str(user_ids[i]))]
        if j < len(user_ids):
            try:
                user2 = bot.get_chat_member(chat_id=user_ids[j], user_id=user_ids[j]).user
                username2 = '@' + user2.username if user2.username else user2.first_name
            except TelegramError:
                username2 = 'ID: ' + str(user_ids[j])
            row.append(InlineKeyboardButton(username2, callback_data='USER_ALIAS_%s' % str(user_ids[j])))
        markup.append(row)

    markup = markup_append_pagination(bot, update, user_ids, markup, page, 'USER_ALIAS')
    markup.append([InlineKeyboardButton('🔜 ' + _('Skip'), callback_data='USER_ALIAS_%s' % str(0))])

    reply_markup = InlineKeyboardMarkup(markup)
    text = '👍 ' + _('Ok, is this user on Telegram?')

    if not first_message:
        msg = bot.edit_message_text(text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup,
                                    parse_mode='Markdown')
    elif len(user_ids) == 0:
        msg = bot.send_message(chat_id, _('No results'))
    else:
        msg = bot.send_message(chat_id, text, disable_notification=True, reply_markup=reply_markup,
                               parse_mode='Markdown')
        chat_data[msg.message_id] = dict()
        chat_data[msg.message_id]['pages'] = page

    if message.reply_to_message:
        cldbid = chat_data['alias_cldbid'][str(message.reply_to_message.message_id)][1]
        del chat_data['alias_cldbid'][str(message.reply_to_message.message_id)]
        bot.delete_message(chat_id=chat_id, message_id=message.reply_to_message.message_id)
        chat_data['alias_cldbid'][str(msg.message_id)] = message.text, cldbid


@user_language
def assign_user_alias_step3(bot, update, chat_data, telegram_id):
    message = update.effective_message
    alias, cldbid = chat_data['alias_cldbid'][str(message.message_id)]

    skip = bool(int(telegram_id) == 0)
    if skip:
        add_user(telegram_id, alias, cldbid)
    else:
        assign_name_tsid(telegram_id, name=alias, ts_id=cldbid)

    bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    bot.answer_callback_query(update.callback_query.id, _('Alias assigned successfully'), show_alert=True)

    menu_bot, menu_update = chat_data['bot_update']
    del chat_data['bot_update']
    users_tsdb(menu_bot, menu_update, chat_data)


@user_language
def users_tsdb(bot, update, chat_data):
    message = update.effective_message
    chat_id = message.chat_id
    markup = []
    users = get_users_tsdb()
    users = sorted(users, key=lambda user: user['client_lastconnected'], reverse=True)
    first_message = bool(update.message)

    page = chat_data[message.message_id]['pages'] if not first_message else 1

    start = 10 * (page-1) if page > 1 else 0
    end = start+10 if start+10 < len(users) else len(users)
    for i in range(start, end, 2):
        user1 = users[i]
        row = [InlineKeyboardButton(user1['client_nickname'], callback_data='USER_DETAIL_%s' % str(user1['cldbid']))]
        if i+1 < len(users):
            user2 = users[i+1]
            row.append(InlineKeyboardButton(user2['client_nickname'],
                                            callback_data='USER_DETAIL_%s' % str(user2['cldbid'])))
        markup.append(row)

    markup = markup_append_pagination(bot, update, users, markup, page, 'USER')

    reply_markup = InlineKeyboardMarkup(markup)
    text = '🎙 ' + _('*User list:*') + '\n\n' + _('Here is a list of all your TeamSpeak users, pressing any of them \
                                           will take you to his detail.')
    if not first_message:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup,
                              parse_mode='Markdown')
    elif len(users) == 0:
        bot.send_message(chat_id, _('No results'))
    else:
        msg = bot.send_message(chat_id, text, disable_notification=True, reply_markup=reply_markup,
                               parse_mode='Markdown')
        chat_data[msg.message_id] = dict()
        chat_data[msg.message_id]['pages'] = page


@user_language
def details_user_ts(bot, update, chat_data, cldbid):
    message = update.effective_message
    chat_id = message.chat_id
    user = get_user_ts_info(cldbid)
    user_clid = get_user_clid(user['client_unique_identifier'])
    markup = list()

    banid = check_user_banned(uid=user['client_unique_identifier'])
    text = ('🚫 ' + _('ID banned')) if banid else ('✅ ' + _('ID unbanned'))
    action = 'USER_BAN_ID_%s' % cldbid if not banid else 'USER_UNBAN_%s_%s' % (cldbid, banid[0])
    markup_banid = InlineKeyboardButton(text, callback_data=action)

    banid = check_user_banned(ip=user['client_lastip'])
    text = ('🚫 ' + _('IP banned')) if banid else ('✅ ' + _('IP unbanned'))
    action = 'USER_BAN_IP_%s' % cldbid if not banid else 'USER_UNBAN_%s_%s' % (cldbid, banid[0])
    markup_banip = InlineKeyboardButton(text, callback_data=action)

    markup.append([markup_banid, markup_banip])

    banid = check_user_banned(name=user['client_nickname'])
    text = ('🚫 ' + _('Name banned')) if banid else ('✅ ' + _('Name unbanned'))
    action = 'USER_BAN_NAME_%s' % cldbid if not banid else 'USER_UNBAN_%s_%s' % (cldbid, banid[0])
    markup.append([InlineKeyboardButton(text, callback_data=action)])

    if user_clid:
        channel_kick = InlineKeyboardButton(_('Channel kick'), callback_data='USER_KICK_%s_4' % cldbid)
        server_kick = InlineKeyboardButton(_('Server kick'), callback_data='USER_KICK_%s_5' % cldbid)
        markup.append([channel_kick, server_kick])

    markup.append([InlineKeyboardButton('🙍‍♂️ ' + _('Assign alias'), callback_data='USER_ALIAS_PRE_%s' % cldbid)])
    markup.append([InlineKeyboardButton(_('Back'), callback_data='USER_BACK')])

    reply_markup = InlineKeyboardMarkup(markup)
    connected = ' 👁‍🗨' if user_clid else ''
    last_connection = datetime.fromtimestamp(int(user['client_lastconnected'])).strftime('%d/%m/%Y %H:%M:%S')
    last_connection_text = last_connection if connected == '' else _('ONLINE') + ' ' + _('since') + ' ' + last_connection
    alias = '\n*Alias:* ' + get_name(cldbid) if get_name(cldbid) is not None else ''

    text = '🔎 ' + _('*User details:*') + '\n' + '\n' + _('*Name:*') + ' ' + user['client_nickname'] + connected \
           + alias \
           + '\n' + _('*Last connection:*') + ' ' + last_connection_text \
           + '\n' + _('*Last IP:*') + ' ' + user['client_lastip'] \
           + '\n' + _('*Client DB identifier:*') + ' ' + str(cldbid) \
           + '\n' + _('*Client Unique identifier:*') + ' ' + user['client_unique_identifier'] \
           + '\n\n' + _('*Date creation:*') + ' ' + \
           datetime.fromtimestamp(int(user['client_created'])).strftime('%d/%m/%Y %H:%M:%S') \
           + '\n' + _('*Total connections:*') + ' ' + user['client_totalconnections']

    bot.edit_message_text(text, chat_id=chat_id, message_id=message.message_id, reply_markup=reply_markup,
                          parse_mode='Markdown')


@user_language
def callback_query_handler(bot, update, chat_data):
    query_data = update.callback_query.data
    message = update.effective_message
    if query_data.startswith('TS_UPDATE'):
        a = get_ts_view()
        if a == message.text_markdown:
            bot.answer_callback_query(update.callback_query.id, _('No changes'))
        else:
            ts_view(bot, update, message_id=message.message_id, chat_id=update.effective_chat.id)
            bot.answer_callback_query(update.callback_query.id, _('Successfully updated'))

    elif query_data.startswith('USER'):
        no_chat_data = update.effective_user.id == ADMIN_ID and \
                       (message.message_id not in chat_data or 'pages' not in chat_data[message.message_id])
        if no_chat_data:
            chat_data[message.message_id] = dict()
            chat_data[message.message_id]['pages'] = 1

        if update.effective_user.id != ADMIN_ID:
            bot.answer_callback_query(update.callback_query.id, _('You must be admin'))

        elif query_data.startswith('USER_PG'):
            chat_data[message.message_id]['pages'] += 1 if query_data.startswith('USER_PG_NEXT') else -1
            users_tsdb(bot, update, chat_data)

        elif query_data.startswith('USER_BAN'):
            if query_data.startswith('USER_BAN_ID'):
                cldbid, ban_type = int(query_data.split('USER_BAN_ID_')[1]), 'ID'
            elif query_data.startswith('USER_BAN_IP'):
                cldbid, ban_type = int(query_data.split('USER_BAN_IP_')[1]), 'IP'
            else:
                cldbid, ban_type = int(query_data.split('USER_BAN_NAME_')[1]), 'NAME'
            ban_ts_user(bot, update, chat_data, cldbid=cldbid, ban_type=ban_type)

        elif query_data.startswith('USER_UNBAN'):
            cldbid, banid = query_data.split("USER_UNBAN_")[1].split("_")
            unban_ts_user(bot, update, chat_data, banid=int(banid), cldbid=int(cldbid))

        elif query_data.startswith('USER_DETAIL'):
            cldbid = query_data.split("USER_DETAIL_")[1]
            details_user_ts(bot, update, chat_data, cldbid=int(cldbid))

        elif query_data.startswith('USER_KICK'):
            uid, kick_type = query_data.split("USER_KICK_")[1].split("_")
            kick_ts_user(bot, update, int(uid), int(kick_type))

        elif query_data.startswith('USER_ALIAS'):
            if query_data.startswith('USER_ALIAS_PRE'):
                cldbid = query_data.split("USER_ALIAS_PRE_")[1]
                assign_user_alias_step1(bot, update, chat_data, cldbid)
            elif query_data.startswith('USER_ALIAS_PG'):
                chat_data[message.message_id]['pages'] += 1 if query_data.startswith('USER_ALIAS_PG_NEXT') else -1
                assign_user_alias_step2(bot, update, chat_data)
            elif query_data.startswith('USER_ALIAS'):
                telegram_id = query_data.split("USER_ALIAS_")[1]
                assign_user_alias_step3(bot, update, chat_data, telegram_id)

        elif query_data.startswith('USER_BACK'):
            users_tsdb(bot, update, chat_data)

