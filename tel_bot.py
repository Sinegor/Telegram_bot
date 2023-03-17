import time 
import logging
import os
import dotenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from crypto  import main, initial_data
from models import today_pure_price_mov, global_pure_price_mov
from messages import START_MESSAGE
load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
URL_DATA_FILE = os.getenv ('URL_DATA_FILE')
sin_bot = Bot(TOKEN)
sin_disp = Dispatcher(sin_bot)

@sin_disp.message_handler(commands=['start'])
async def start_handler (message: types.Message):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    await message.reply(START_MESSAGE.format(user_name))

@sin_disp.message_handler(commands=['ethereum'])
async def eth_handler (message: types.Message):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: request fot subscribing ethereum from {user_id} {user_name}')
    

