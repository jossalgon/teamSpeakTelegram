# -*- coding: utf-8 -*-
import sqlite3 as lite
import ts3
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
ts_user = config['Telegram']['ts_user']
ts_pass = config['Telegram']['ts_pass']


class Utils:
    def create_database(self):
        path = 'data.db'
        con = lite.connect(path)
        with con:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS TsUsers(Telegram_id INTEGER NOT NULL, Name TEXT NOT NULL, Ts_id INTEGER NOT NULL)")

    def is_allow(self, user_id):
        try:
            path = 'data.db'
            con = lite.connect(path)
            with con:
                cur = con.cursor()
                allow = \
                cur.execute("SELECT EXISTS(SELECT 1 FROM TsUsers WHERE Telegram_id=? LIMIT 1)", (user_id,)).fetchone()[0]
                return bool(allow)
        except Exception as e:
            print(str(e))
            return False

    def get_name(self, ts_id):
        try:
            path = 'data.db'
            con = lite.connect(path)
            with con:
                cur = con.cursor()
                name = cur.execute("SELECT Name FROM TsUsers WHERE Ts_id=?", (ts_id,)).fetchone()
                name = name[0] if name is not None else None
                return name
        except Exception as e:
            print(str(e))

    def ts_connect(self):
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
                    name = self.get_name(db_id)
                    if name is not None:
                        clients.append(name)
                    else:
                        clients.append(client['client_nickname'])
        return clients

    def ts_stats(self):
        try:
            ts_users = self.ts_connect()
            text = '👁‍🗨 Conectados:\n'
            if len(ts_users) == 0:
                text = 'No hay nadie ahora mismo'
            else:
                for client in ts_users:
                    text += '%s\n' % client
            return text
        except Exception as e:
            return e
