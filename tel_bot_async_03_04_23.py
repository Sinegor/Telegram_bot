import time 
import logging
import os
import dotenv
import datetime
import asyncio



from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext

from messages import START_MESSAGE
from async_script_03_04_23 import set_starting_data, subscribe, string_handling, get_previous_week_btc_data_price_1
from models import today_pure_price_mov, price
from keyboards import keyb_client


load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
sin_bot = Bot(TOKEN)
sin_disp = Dispatcher(sin_bot)



@sin_disp.message_handler(commands=['start'])
async def start_handler (message: types.Message):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    await message.reply(START_MESSAGE.format(user_name), reply_markup=keyb_client)

# Получаем данные о ценовых движениях битка за прошедшую неделю:
@sin_disp.message_handler(commands=["history"])
async def history_handler(message):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    responce_data = await get_previous_week_btc_data_price_1()
    await sin_bot.send_message(user_id, responce_data)

# Обработчик возвращает: 1. Информацию о чистом ценовом активе за прошедшую неделю. 2. Подписку на отслеживание цены данного актива
# и вычисление чистого движения. 3. По истечению суток мониторинга добавление новых данных в глобальные недельные сведения.

@sin_disp.message_handler()
async def st_handler_1 (message: types.Message):
    global price, today_pure_price_mov
    user_id = message.from_id
    current_date = datetime.datetime.now().date()
    coin = string_handling(message.text)
    try:
        await set_starting_data(coin)
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")
    subscribe_response = await subscribe(coin, current_date)
    await message.reply(subscribe_response)




if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=True)     
