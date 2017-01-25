#!/usr/bin/python
# -*- coding: utf-8 -*-
import sqlite3 as lite

path = 'data.db'

con = lite.connect(path)

with con:

    cur = con.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS Users(Telegram_id INTEGER NOT NULL, Name TEXT NOT NULL, Ts_id INTEGER NOT NULL)")
