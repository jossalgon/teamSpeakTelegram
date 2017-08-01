# -*- encoding: utf-8 -*-
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram.ext import Updater, CommandHandler, RegexHandler
import logging
import configparser

from teamSpeakTelegram import utils, user_language, _

config = configparser.ConfigParser()
config.read('config.ini')

TOKEN_ID = config.get('Telegram', 'token_id') if config.has_option('Telegram', 'token_id') else None
ADMIN_ID = config.getint('Telegram', 'admin_id') if config.has_option('Telegram', 'admin_id') else None


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)


@user_language
def start(bot, update, args):
    message = update.message
    user = message.from_user
    res = False
    if args:
        res = utils.validate_invitation_token(token=args[0], user_id=user.id, name=user.first_name)

    if res:
        text = _("Welcome %s you're now activated, using /who or /ts you can check who's in teamspeak.") % \
               user.first_name
    elif utils.is_allow(user.id):
        text = _("Hello %s, using /who or /ts you can check who's in teamspeak.") % user.first_name
    else:
        text = _("Welcome, ask admin to generate an invitation link via /generate")
    bot.sendMessage(message.chat_id, text, reply_to_message_id=message.message_id)


@user_language
def ts_stats(bot, update):
    message = update.message
    if utils.is_allow(message.from_user.id):
        stats = utils.ts_stats()
    else:
        stats = _("You aren't allow to use this")
    bot.send_message(message.chat.id, stats, reply_to_message_id=message.message_id)


@user_language
def generate_invitation(bot, update):
    message = update.message
    token = utils.generate_invitation()
    link = 'https://telegram.me/%s?start=%s' % (bot.username, token)
    share_link = 'https://telegram.me/share/url?url={0}&text=Click%20the%20link%20to%20join%20the%20teamspeak%20bot'.format(link)
    keyboard = [[InlineKeyboardButton(_('Join'), url=link)],
                [InlineKeyboardButton(_('Share link'), url=share_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(message.chat_id, '🎈 ' + _('Welcome to TeamSpeak bot') + ' 🎈\n\n' +
                    _('This is an invitation to use the TeamSpeak bot'),
                    reply_markup=reply_markup)


@user_language
def mention_toggle(bot, update):
    message = update.message
    if message.chat.type == 'private':
        text = _('Use this command in the group where you want to activate/disable the notifications')
    else:
        text = utils.mention_toggle(message.chat_id, message.from_user.id)
    bot.sendMessage(message.chat_id, text, reply_to_message_id=message.message_id)


def get_id(bot, update):
    message = update.message
    bot.sendMessage(message.chat_id, message.from_user.id, reply_to_message_id=message.message_id)


def notify(bot, update, args):
    text = ' '.join(args)
    text = text.replace('\\n', '\n')
    if text:
        for user_id in utils.get_user_ids():
            try:
                bot.send_message(user_id, text, parse_mode='Markdown')
            except:
                pass


def log_error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


@user_language
def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=_("Sorry, I didn't understand that command."))


def main():
    utils.create_database()

    updater = Updater(token=TOKEN_ID)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler('start', start, pass_args=True))
    dp.add_handler(CommandHandler('help', start))
    dp.add_handler(CommandHandler('who', ts_stats))
    dp.add_handler(CommandHandler('ts', utils.ts_view))
    dp.add_handler(CommandHandler('mention', mention_toggle))
    dp.add_handler(CommandHandler('generate', generate_invitation, Filters.user(user_id=ADMIN_ID)))
    dp.add_handler(CommandHandler('notify', notify, Filters.user(user_id=ADMIN_ID), pass_args=True))
    dp.add_handler(CommandHandler('id', get_id))
    dp.add_handler(RegexHandler(r'(?i).*\@flandas\b', utils.mention_forwarder))
    dp.add_handler(CallbackQueryHandler(utils.callback_query_handler, pass_chat_data=True))
    dp.add_handler(CommandHandler('users', utils.users_tsdb, Filters.user(user_id=ADMIN_ID), pass_chat_data=True))
    # dp.add_handler(CommandHandler('pl', utils.get_permision_list))


    # log all errors
    dp.add_error_handler(log_error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
