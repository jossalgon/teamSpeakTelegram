# -*- encoding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, RegexHandler
import logging
import configparser

from teamSpeakTelegram import utils

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)


def start(bot, update):
    message = update.message
    bot.sendMessage(chat_id=message.chat_id, text='Welcome', reply_to_message_id=message.message_id)


def ts_stats(bot, update):
    message = update.message
    if utils.is_allow(message.from_user.id):
        stats = utils.ts_stats()
    else:
        stats = "You aren't allow to use this"
    bot.sendMessage(chat_id=message.chat_id, text=stats, reply_to_message_id=message.message_id)


def mention_toggle(bot, update):
    message = update.message
    if message.chat.type == 'private':
        text = 'Usa este comando en el grupo que quieras activar/desactivar las menciones'
    else:
        text = utils.mention_toggle(message.chat_id, message.from_user.id)
    bot.sendMessage(message.chat_id, text, reply_to=message.message_id)


def log_error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def main():
    utils.create_database()
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Create the EventHandler and pass it your bot's token.
    token_id = config['Telegram']['token_id']
    updater = Updater(token=token_id)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', start))
    dp.add_handler(CommandHandler('ts', ts_stats))
    dp.add_handler(CommandHandler('mention', mention_toggle))
    dp.add_handler(RegexHandler(r'(?i).*\@flandas\b', utils.mention_forwarder))

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
