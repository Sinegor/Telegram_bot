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
                                get_last_week_btc_history, subscribe_1,\
                                get_previous_data_price
from models import today_pure_price_mov, global_pure_price_mov, price
from keyboards import keyb_client, keyb_client_1, keyb_client_2


load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
sin_bot = Bot(TOKEN)
my_storage = MemoryStorage()
sin_disp = Dispatcher(sin_bot, storage=my_storage,)

class Testing_state(StatesGroup):
    get_btc_historical_data = State()
    get_alt_historical_data = State()
    get_pure_alt_move = State()
    request_subscribe = State()
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
        'clean_price_movement':{}
        }
        data['active_coin'] = None
        await sin_bot.send_message(user_id, START_MESSAGE.format(user_name), reply_markup=keyb_client)


# Получаем данные о ценовых движениях битка за прошедшую неделю:
@sin_disp.message_handler(commands=["history"], state=None)
async def history_handler(message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
            crud_responce_data = await get_last_week_btc_history()
            data['price']['bitcoin_history'] = crud_responce_data
            yesterday_data = crud_responce_data[-1]
            key_date = (list(yesterday_data.keys()))[0]
            data['price']['coins_last_prices']['bitcoin']['yesterday_date'] = key_date
            data['price']['coins_last_prices']['bitcoin']['yesterday_price'] = list(yesterday_data.values())[0]  
            response = pandas.Series(crud_responce_data)
            await sin_bot.send_message(user_id, response)
            await sin_bot.send_message (user_id, "Specify the name of the coin for which you want to get information")
    # Меняем состояние, чтобы в случае повторных запросов брать историю из Хранилища.
            await Testing_state.get_btc_historical_data.set()

# Повторный запрос недельной истории битка. Данные берутся не с сервера, а из хранидища:
@sin_disp.message_handler(commands=["history"], state=Testing_state.get_btc_historical_data)
async def history_handler_1(message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        response = pandas.Series(data['price']['bitcoin_history'])
    print (await state.get_state())
    await sin_bot.send_message(user_id, response)
    await sin_bot.send_message (user_id, "Specify the name of the coin for which you want to get information")


# Обработчик "кнопки кастомной клавиатуры "alt_subscribe", предлагает ввести количество часов:
@sin_disp.message_handler(commands=['alt_subscribe'], state=Testing_state.get_pure_alt_move)
async def st_handler_1 (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    await sin_bot.send_message(user_id, "Укажите через сколько часов вы хотите получить\
                                         свежую информацию", reply_markup=keyb_client_2)
    await Testing_state.request_subscribe.set()



# Обработчик "кнопки кастомной клавиатуры alt_history"
@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.get_pure_alt_move)
async def st_handler_1 (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['actixe coin']
        
    await sin_bot.send_message(user_id, "Укажите через сколько часов вы хотите получить свежую информацию", )
    await Testing_state.request_subscribe.set()


        
# Обработчик первичного "свободного" запроса чистого движения альта. 

@sin_disp.message_handler(state=None)
async def st_handler_2 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        yesterday_data = await set_starting_data(coin)
        async with state.proxy() as data:
            data['price']['coins_last_prices'][coin] = {}
            data['price']['coins_last_prices'][coin]['yesterday_price'] = yesterday_data['alt']
            data['price']['coins_last_prices']['bitcoin']['yesterday_price'] = yesterday_data['btc']
            data['price']['coins_last_prices']['bitcoin']['yesterday_date'] = yesterday_data['time']
            data['price']['coins_last_prices'][coin]['yesterday_date'] = yesterday_data['time']
        subscribe_response = await subscribe(coin, state)
        my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
     

 
# Обработчик "свобоного запроса" по активу после того, как недельные данные по 
# битку уже запрошены - не запрашивается вчерашняя цена битка:
@sin_disp.message_handler(state=Testing_state.get_btc_historical_data)
async def st_handler_3 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        yesterday_alt_price = await get_previous_data_price(coin)
        async with state.proxy() as data:
            data['price']['coins_last_prices'][coin] = {}
            data['price']['coins_last_prices'][coin]['yesterday_price'] = yesterday_alt_price
        subscribe_response = await subscribe(coin, state)
        my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")

# Обработчик "свобоного запроса" по активу после оформления подписки на данные по другому активу или просто после получения первичной инфы
# по другому активу:
@sin_disp.message_handler(state=Testing_state.get_pure_alt_move)
async def st_handler_4 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    async with state.proxy() as data:
        alt_list = data['price']['coins_last_prices'].keys()
    if coin not in alt_list:
        try:
            yesterday_alt_price = await get_previous_data_price(coin)
            async with state.proxy() as data:
                data['price']['coins_last_prices'][coin] = {}
                data['price']['coins_last_prices'][coin]['yesterday_price'] = yesterday_alt_price
            subscribe_response = await subscribe(coin, state)
            my_response = pandas.Series(subscribe_response, subscribe_response.keys())
            await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
            await Testing_state.get_pure_alt_move.set()
        except KeyError as e:
            await message.reply("Такая монета не поддерживается, проверьте правильность написания")
    else:
        subscribe_response = await subscribe_1(coin, state)
        my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        await Testing_state.request_subscribe.set()
        await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        

@sin_disp.message_handler(commands=['cancel'], state=Testing_state.request_subscribe)
async def st_handler_5_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    await Testing_state.get_pure_alt_move.set()
    await sin_bot.send_message(user_id, text='Подписка отменена. \
                                       Введите название актива, по которому вы хотите получить информацию')


# Предоставляет данные по активу в рамках подписки через указанное время:
@sin_disp.message_handler(state=Testing_state.request_subscribe)
async def st_handler_5 (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    current_date = datetime.datetime.now()
    try:
        value = int(message.text)
        if value > 24 or value < 0:
            await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от одного до 24')
            
        else:
            async with state.proxy() as data:
                coin = data['active_coin']
            await sin_bot.send_message(user_id,text='Подписка успешно оформлена. На данный момент вы можете запросить информацию\
                                       по иным альтам')
            await Testing_state.get_pure_alt_move.set()
            await asyncio.sleep(value*60)
            subscribe_response = await subscribe_1(coin, state)
            my_response = pandas.Series(subscribe_response, subscribe_response.keys())
            await sin_bot.send_message(user_id, my_response)
            await Testing_state.request_subscribe.set()
            await sin_bot.send_message (user_id, text='Если хотите продолжить отслеживать актив` укажите количество часов, через которое \
                                        вы хотите получить информацию.', reply_markup=keyb_client_2)
    except ValueError as e:
        await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от одного до 24')
    
    
    
    

if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=False)     

