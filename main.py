import configparser
import asyncio
import os

from bot import CookiesConvertorBot
from user_storage import UserStorage


async def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    api_token = config['bot']['token']
    temp_dir = config['bot']['temp_dir']
    db_file = config['bot']['user_database']

    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    # if not os.path.isfile(db_file):
    #     open(db_file, 'w').close()

    storage = UserStorage(db_file)
    bot = CookiesConvertorBot(api_token, temp_dir, storage)

    await storage.start_db()
    await bot.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
