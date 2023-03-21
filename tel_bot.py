import time 
import logging
import os
import dotenv
import sched

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from main_generator import main_generator
from models import today_pure_price_mov, global_pure_price_mov, price
from messages import START_MESSAGE
load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
URL_DATA_FILE = os.getenv ('URL_DATA_FILE')
sin_bot = Bot(TOKEN)
sin_disp = Dispatcher(sin_bot)

# @sin_disp.message_handler(commands=['start'])
# async def start_handler (message: types.Message):
#     user_id = message.from_id
#     user_name = message.from_user.full_name
#     logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
#     await message.reply(START_MESSAGE.format(user_name))

@sin_disp.message_handler(commands=['start'])
async def st_handler (message: types.Message):
    user_id = message.from_id
    data_generator = main_generator('ethereum')
    first_reply = next(data_generator)
    await message.reply(first_reply)
    for i in range(10):
        time.sleep(2000)
        await sin_bot.send_message(user_id, next(data_generator))  


if __name__ == '__main__':
    executor.start_polling(sin_disp)
