from setuptools import setup

setup(name='teamSpeakTelegram',
      version='0.2.2',
      description='A telegram bot that tells you who is connected to the teamspeak server to know when your friends are online.',
      url='https://github.com/jossalgon/teamSpeakTelegram',
      author='Jose Luis Salazar Gonzalez',
      author_email='joseluis25sg@gmail.com',
      packages=['teamSpeakTelegram'],
      install_requires=[
          "python-telegram-bot",
          "ts3",
          "pymysql"
      ],
      zip_safe=False)
