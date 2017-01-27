# TeamSpeakTelegram
TeamSpeakTelegram is a telegram bot that tells you who is connected to the teamspeak server to know when your friends are online. It can be used both in private and in a group chat.

## Installation
1. Create a config.ini file with:

  ```
  [Telegram]
  token_id = YOUR_TELEGRAM_BOT_TOKEN
  
  [TS]
  ts_host = YOUR_TS_HOST
  ts_user = serveradmin (OR YOUR TS USERNAME AS ADMIN)
  ts_pass = YOUR_TS_PASSWORD
  
  [Database]
  DB_HOST = YOUR_MYSQL_HOST
  DB_USER = YOUR_MYSQL_USER
  DB_PASS = YOUR_MYSQL_PASS
  DB_NAME = YOUR_MYSQL_DB_NAME
  ```

2. Install requirements
  ```
  sudo pip install -r requirements.txt
  ```

3. Run the bot
  ```
  python3 teamspeak.py &
  ```

4. Populate your database

  Create a entry for each user that you want to use the bot, with Telegram_id, the name you want to show and de TeamSpeak database ID.

## Commands
Command | Uses
------- | -----
/start | Reply with a welcome message
/ts | Reply with the connected users

![Example bot](http://imgur.com/lkx8Mqn.jpg)
