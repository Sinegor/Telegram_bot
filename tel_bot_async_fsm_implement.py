import time 
import logging
import os
import dotenv
import datetime
import asyncio
import pandas


from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext


from messages import START_MESSAGE
from async_script_fsm_implement import set_starting_data, subscribe, string_handling, \
                                get_previous_week_btc_data_price_1, set_starting_data_1
from models import today_pure_price_mov, global_pure_price_mov, price
from keyboards import keyb_client


load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
sin_bot = Bot(TOKEN)
my_storage = MemoryStorage()
sin_disp = Dispatcher(sin_bot, storage=my_storage,)

class Testing_state(StatesGroup):
    get_historical_data = State()
    get_current_data = State()
    day_modificate = State()




@sin_disp.message_handler(commands=['start'], state='*')
async def start_handler (message: types.Message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        data['price']= {
            'coins_last_prices':{
                                'bitcoin':{},
            },
            'bitcoin_history':{},
            'clean price movement':{}
        }
        await sin_bot.send_message(user_id, START_MESSAGE.format(user_name), reply_markup=keyb_client)


# Получаем данные о ценовых движениях битка за прошедшую неделю:
@sin_disp.message_handler(commands=["history"], state=None)
async def history_handler(message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        crud_responce_data = await get_previous_week_btc_data_price_1()
        data['price']['bitcoin_history'] = crud_responce_data
        yesterday_data = crud_responce_data[-1]
        key_date = (list(yesterday_data.keys()))[0]
        data['price']['coins_last_prices']['bitcoin']['yesterday_date'] = key_date
        data['price']['coins_last_prices']['bitcoin']['yesterday_price'] = list(yesterday_data.values())[0]  
        print (await state.get_state())
        response = pandas.Series(crud_responce_data)
        await sin_bot.send_message(user_id, response)
# Меняем состояние, чтобы в случае повторных запросов брать историю из Хранилища.
        await Testing_state.get_historical_data.set()

# В данном случае история не запрашивается заново, а берётся из хранилища:
@sin_disp.message_handler(commands=["history"], state=Testing_state.get_historical_data)
async def history_handler(message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        response = pandas.Series(data['price']['bitcoin_history'])
        print (await state.get_state())
        await sin_bot.send_message(user_id, response)



        
# Обработчик возвращает: 1. Информацию о чистом ценовом активе за прошедшую неделю. 2. Подписку на отслеживание цены данного актива
# и вычисление чистого движения. 3. По истечению суток мониторинга добавление новых данных в глобальные недельные сведения.

@sin_disp.message_handler(state=None)
async def st_handler_1 (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    current_date = datetime.datetime.now().date()
    coin = string_handling(message.text)
    try:
        yesterday_data = await set_starting_data(coin)
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")
    async with state.proxy() as data:
            data['price']['coins_last_prices'][coin] = {}
            data['price']['coins_last_prices'][coin]['yesterday_price'] = yesterday_data['alt']
            data['price']['coins_last_prices']['bitcoin']['yesterday_price'] = yesterday_data['btc']
            data['price']['coins_last_prices']['bitcoin']['yesterday_date'] = yesterday_data['time']
            data['price']['coins_last_prices'][coin]['yesterday_date'] = yesterday_data['time']
    subscribe_response = await subscribe(coin, current_date, state)
    await sin_bot.send_message(user_id, subscribe_response)
#    await Testing_state.get_current_data.set()


#  Делает то же самое, что и предыдущий обработчик, только данные по битку берёт из стейта
@sin_disp.message_handler(state=Testing_state.get_historical_data)
async def st_handler_1 (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    current_date = datetime.datetime.now().date()
    coin = string_handling(message.text)
    try:
        yesterday_alt_price = await set_starting_data_1(coin)
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")
    async with state.proxy() as data:
        data['price']['coins_last_prices'][coin] = {}
        data['price']['coins_last_prices'][coin]['yesterday_price'] = yesterday_alt_price
    subscribe_response = await subscribe(coin, current_date, state)
    await sin_bot.send_message(user_id, subscribe_response)
    #    await Testing_state.get_current_data.set()


if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=False)     

