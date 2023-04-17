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
                                 subscribe_1, get_yesterday_data_price, check_actual_price_mov_data, \
                                 check_actual_alt_state, check_actual_btc_history, get_last_week_coin_history, \
                                 get_historical_pure_price_mov, check_historical_pure_price_mov_data
from models import today_pure_price_mov, global_pure_price_mov, price
from keyboards import keyb_client, keyb_client_1, keyb_client_2, keyb_client_3


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
    

@sin_disp.message_handler(commands=['start'], state='*')
async def start_handler (message: types.Message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        data['price']= {
        'coins_last_prices':{
        },
        'bitcoin_history':[],
        'clean_price_movement':{}
        }
        data['active_coin'] = None
        await sin_bot.send_message(user_id, START_MESSAGE.format(user_name), reply_markup=keyb_client)


# обработка кастомной кнопки "Histoty". Получаем данные о ценовых движениях битка за прошедшую неделю:
@sin_disp.message_handler(commands=["history"], state="*")
async def history_handler(message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    await check_actual_btc_history(state)
    async with state.proxy() as data:
        key_for_last_btc_price = (datetime.datetime.fromtimestamp(time.time()-84600).date()).strftime('%d-%m-%Y')
        last_btc_price = data['price']['bitcoin_history'][-1][key_for_last_btc_price]
        await check_actual_alt_state('bitcoin', state, last_btc_price)
        response = pandas.Series(data['price']['bitcoin_history'])
        await sin_bot.send_message(user_id, response)
        await sin_bot.send_message (user_id, "Specify the name of the coin for which you want to get information")
# Меняем состояние, чтобы в случае повторных запросов брать историю из Хранилища.
        await Testing_state.get_btc_historical_data.set()


# Обработчик "кнопки кастомной клавиатуры "alt_subscribe", предлагает ввести количество часов:
@sin_disp.message_handler(commands=['alt_subscribe'], state=Testing_state.get_pure_alt_move)
async def handler_request_subscribe (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    await sin_bot.send_message(user_id, "Укажите через сколько часов вы хотите получить\
                                         свежую информацию", reply_markup=keyb_client_2)
    await Testing_state.request_subscribe.set()



@sin_disp.message_handler(commands=['home'], state=Testing_state.get_pure_alt_move)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    await Testing_state.get_btc_historical_data.set()
    await sin_bot.send_message(user_id, text='Вы вернулись на первоначальный экран', reply_markup=keyb_client)

@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.get_pure_alt_move)
async def st_handler_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    await check_actual_btc_history(state)
    async with state.proxy() as data:
        coin = data['active_coin']
        result = await check_historical_pure_price_mov_data(coin, state)
        if result == False:
            result_data = data['price']['clean_price_movement'][coin]['history']
            await sin_bot.send_message(user_id, result_data)
        else:
            [data['price']['clean_price_movement'][coin]['history'].append(value) for value in result]
            result_data = data['price']['clean_price_movement'][coin]['history']
            await sin_bot.send_message(user_id, result_data)


    
    # await sin_bot.send_message(user_id, "Укажите через сколько часов вы хотите получить свежую информацию", )
    # await Testing_state.request_subscribe.set()


# Обработчик первичного "свободного" запроса чистого движения альта. 

@sin_disp.message_handler(state=None)
async def handler_get_alt_data_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        yesterday_data = await set_starting_data(coin)
        await check_actual_alt_state(coin, state, yesterday_data['alt'])
        await check_actual_alt_state('bitcoin', state, yesterday_data['btc'])
        subscribe_response = await subscribe(coin, state)
        my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
          await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client_3)

 
# Обработчик "свобоного запроса" по активу после того, как недельные данные по 
# битку уже запрошены - не запрашивается вчерашняя цена битка:
@sin_disp.message_handler(state=Testing_state.get_btc_historical_data)
async def handler_get_alt_data_2 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
    # Может быть эти две строчки можно убрать:
        #yesterday_alt_price = await get_yesterday_data_price(coin)
        #await check_actual_alt_state(coin, state, yesterday_alt_price)
        await check_actual_alt_state(coin, state)
        subscribe_response = await subscribe(coin, state)
        my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")

# Обработчик "свобоного запроса" по активу после оформления подписки на данные по другому активу или просто после получения первичной инфы
# по другому активу:
@sin_disp.message_handler(state=Testing_state.get_pure_alt_move)
async def handler_get_alt_data_3 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        yesterday_alt_price = await get_yesterday_data_price(coin)
        type_of_request = await check_actual_alt_state(coin, state, yesterday_alt_price)
        await check_actual_alt_state('bitcoin', state,)
        if type_of_request == 'basic request':
            subscribe_response = await subscribe(coin, state)
            my_response = pandas.Series(subscribe_response, subscribe_response.keys())
            await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
            await Testing_state.get_pure_alt_move.set()
        elif type_of_request =='second request':
            subscribe_response = await subscribe_1(coin, state)
            my_response = pandas.Series(subscribe_response, subscribe_response.keys())
            await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
            await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания")

@sin_disp.message_handler(commands=['cancel'], state=Testing_state.request_subscribe)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    await Testing_state.get_alt_historical_data.set()
    await sin_bot.send_message(user_id, text='Подписка отменена. \
                                       Введите название актива, по которому вы хотите получить информацию', reply_markup=keyb_client)


# Обработчик "кнопки кастомной клавиатуры alt_history" во время действующей подписики:
@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.request_subscribe)
async def st_handler_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['active_coin']
        today_history = data['price']['clean_price_movement'][coin]  
    await sin_bot.send_message(user_id, today_history)
    # await sin_bot.send_message(user_id, "Укажите через сколько часов вы хотите получить свежую информацию", )
    # await Testing_state.request_subscribe.set()


# Предоставляет данные по активу в рамках подписки через указанное время:
@sin_disp.message_handler(state=Testing_state.request_subscribe)
async def handler_subscribe (message: types.Message, state:FSMContext):
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
            await check_actual_alt_state(coin, state)
            await check_actual_alt_state('bitcoin', state)
            subscribe_response = await subscribe_1(coin, state)
            my_response = pandas.Series(subscribe_response, subscribe_response.keys())
            await sin_bot.send_message(user_id, my_response)
            await Testing_state.request_subscribe.set()
            await sin_bot.send_message (user_id, text='Если хотите продолжить отслеживать актив` укажите количество часов, через которое \
                                        вы хотите получить информацию.', reply_markup=keyb_client_3)
    except ValueError as e:
        await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от одного до 24')
    
    

if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=False)     

