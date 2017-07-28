import os
from functools import wraps

import gettext

import sys
from telegram.ext import Filters


# Config the translations
try:
    path = os.path.join(os.path.dirname(sys.modules['teamSpeakTelegram'].__file__), "locale")
    lang_es = gettext.translation("teamspeak", localedir=path, languages=["es"])
except OSError:
    lang_es = gettext

_lang = gettext.gettext


def _(msg): return _lang(msg)


def user_language(func):
    @wraps(func)
    def wrapper(bot, update, *args, **kwargs):
        global _lang

        if (Filters.language('es'))(update.message):
            # If language is es_ES, translates
            _lang = lang_es.gettext
        else:
            _lang = gettext.gettext

        result = func(bot, update, *args, **kwargs)
        return result
    return wrapper
