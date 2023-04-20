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
                                 get_historical_pure_price_mov, check_historical_pure_price_mov_data, clearning_str, handler_history_data, check_symbol

from keyboards import keyb_client, keyb_client_1, keyb_client_2, keyb_client_3
from models import SymbolCoinError


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
    subscribing = State()
    

@sin_disp.message_handler(commands=['start'], state='*')
async def start_handler (message: types.Message, state:FSMContext):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    async with state.proxy() as data:
        data['price']= {  
        'bitcoin_history':[],
        }
        data['active_coin'] = None
        await sin_bot.send_message(user_id, START_MESSAGE.format(user_name), reply_markup=keyb_client)


# обработка кастомной кнопки "Histoty". Получаем данные о ценовых движениях битка за прошедшую неделю:
@sin_disp.message_handler(commands=["history"], state="*")
async def history_handler(message, state:FSMContext):
    try:
        user_id = message.from_id
        user_name = message.from_user.full_name
        logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
        await check_actual_btc_history(state)
        async with state.proxy() as data:
            key_for_last_btc_price = (datetime.datetime.fromtimestamp(time.time()-84600).date()).strftime('%d-%m-%Y')
            last_btc_price = data['price']['bitcoin_history'][-1][key_for_last_btc_price]
            await check_actual_alt_state('bitcoin', state, last_btc_price)
            crud_data = data['price']['bitcoin_history']
            clear_data = handler_history_data(crud_data)
            await sin_bot.send_message(user_id, '<b>Bitcoin history:</b>', parse_mode='HTML')
            await sin_bot.send_message(user_id, clear_data)
            await sin_bot.send_message (user_id, "Specify the name of the coin for which you want to get information")
    # Меняем состояние, чтобы в случае повторных запросов брать историю из Хранилища.
            await Testing_state.get_btc_historical_data.set()
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
 

# Обработчик "кнопки кастомной клавиатуры "alt_subscribe", предлагает ввести количество часов:
@sin_disp.message_handler(commands=['alt_subscribe'], state=Testing_state.get_pure_alt_move)
async def handler_request_subscribe (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    await sin_bot.send_message(user_id, "Укажите c какой переиодичностью вы хотели бы получать информацию. От 60 до 880 минут", reply_markup=keyb_client_2)
    await Testing_state.request_subscribe.set()


@sin_disp.message_handler(commands=['home'], state=Testing_state.get_pure_alt_move)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    await Testing_state.get_btc_historical_data.set()
    await sin_bot.send_message(user_id, text='Вы вернулись на первоначальный экран', reply_markup=keyb_client)

@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.get_pure_alt_move)
async def st_handler_1 (message: types.Message, state:FSMContext):
    try:
        user_id = message.from_id
        await check_actual_btc_history(state)
        async with state.proxy() as data:
            coin = data['active_coin']
        result = await check_historical_pure_price_mov_data(coin, state)
        async with state.proxy() as data:
            if result == False:
                crud_data = data['price'][coin]['clean_price_movement']['history']
                clear_data = handler_history_data(crud_data)
                await sin_bot.send_message(user_id, f'<b>Pure price movement history of {coin}:</b>', parse_mode='HTML')
                await sin_bot.send_message(user_id, text=clear_data)
            else:
                [data['price'][coin]['clean_price_movement']['history'].append(value) for value in result]
                crud_data = data['price'][coin]['clean_price_movement']['history']
                clear_data = handler_history_data(crud_data)
                await sin_bot.send_message(user_id, f'<b>Pure price movement history of {coin}:</b>', parse_mode='HTML')
                await sin_bot.send_message(user_id, clear_data)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
 

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
        subscribe_response = clearning_str(subscribe_response)
        
        # my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        # await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
    except KeyError as e:
        await sin_bot.send_message(user_id, "Такая монета не поддерживается, проверьте правильность написания", 
                                   reply_markup=keyb_client)
    
# Обработчик "свобоного запроса" по активу после того, как недельные данные по 
# битку уже запрошены - не запрашивается вчерашняя цена битка:
@sin_disp.message_handler(state=Testing_state.get_btc_historical_data)
async def handler_get_alt_data_2 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        await check_actual_alt_state(coin, state)
        subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(subscribe_response)
        # my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        # await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 

# Обработчик "свобоного запроса" по активу после оформления подписки на данные по другому активу или просто после получения первичной инфы
# по другому активу:
@sin_disp.message_handler(state=Testing_state.get_pure_alt_move)
async def handler_get_alt_data_3 (message: types.Message, state:FSMContext):
    try:
        user_id = message.from_id
        coin = string_handling(message.text)
        await check_actual_alt_state(coin, state)
        subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(subscribe_response)
        # my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        # await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 
   
@sin_disp.message_handler(commands=['cancel'], state=Testing_state.subscribing)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['active_coin']
        data['price'][coin]['clean_price_movement']['active'] = False
    await Testing_state.get_btc_historical_data.set()
    await sin_bot.send_message(user_id, text='Подписка отменена. \
                                       Введите название актива, по которому вы хотите получить информацию', reply_markup=keyb_client)


# Обработчик "кнопки кастомной клавиатуры alt_history" во время действующей подписики:
@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.subscribing)
async def st_handler_1 (message: types.Message, state:FSMContext):
    try:
        user_id = message.from_id
        await check_actual_btc_history(state)
        async with state.proxy() as data:
            coin = data['active_coin']
        result = await check_historical_pure_price_mov_data(coin, state)
        async with state.proxy() as data:
            if result == False:
                global_history =data['price'][coin]['clean_price_movement']['history']   
                today_history = data['price'][coin]['clean_price_movement'] ['today_mov']
            else:
                [data['price'][coin]['clean_price_movement']['history'].append(value) for value in result]
                global_history = data['price'][coin]['clean_price_movement']['history']
                today_history = data['price'][coin]['clean_price_movement'] ['today_mov']
            clear_data_gl_history = handler_history_data(global_history)
            clear_data_today_data = ''
            today_mov_data = [clear_data_today_data+str(data)+'\n' for data in today_history]
            today_mov_response = handler_history_data(today_mov_data)
            await sin_bot.send_message(user_id, f"Недельная история чистового ценового движения {coin}:")
            await sin_bot.send_message(user_id, clear_data_gl_history)
            await sin_bot.send_message(user_id, f"История сегодняшних изменений чистового ценового движения{coin}:")
            await sin_bot.send_message(user_id, today_mov_response)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
  
        
# Обработчик "свобоного запроса" по активу после оформления подписки на данные по другому активу 
@sin_disp.message_handler(state=Testing_state.subscribing)
async def handler_get_alt_data_2 (message: types.Message, state:FSMContext):
    try:
        user_id = message.from_id
        coin = string_handling(message.text)
        await check_actual_alt_state(coin, state)
        subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(subscribe_response)
        # my_response = pandas.Series(subscribe_response, subscribe_response.keys())
        # await sin_bot.send_message(user_id, my_response, reply_markup=keyb_client_1)
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 
# Сбрасывает процедуру подписки:
@sin_disp.message_handler(state=Testing_state.request_subscribe, commands=['cancel'])
async def handler_subscribe (message: types.Message,  state:FSMContext):
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['active_coin']
        data['price'][coin]['clean_price_movement']['active'] = False
    await Testing_state.get_pure_alt_move.set()
    await sin_bot.send_message(user_id, "Подписка отменена!", reply_markup=keyb_client_1)


# Предоставляет данные по активу в рамках подписки через указанное время:
@sin_disp.message_handler(state=Testing_state.request_subscribe)
async def handler_subscribe (message: types.Message, state:FSMContext):
    #global price, today_pure_price_mov
    user_id = message.from_id
    current_date = datetime.datetime.now()
    try:
        value = int(message.text)
        if value > 880 or value < 60:
            await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от 60 до 880')
            
        else:
            async with state.proxy() as data:
                coin = data['active_coin']
                data['price'][coin]['clean_price_movement']['active'] = True
            await sin_bot.send_message(user_id,text='Подписка успешно оформлена. На данный момент вы можете запросить информацию\
                                       по иным альтам')
            await Testing_state.get_pure_alt_move.set()
            while (True):
                await asyncio.sleep(value)
                async with state.proxy() as data:
                    if data['price'][coin]['clean_price_movement']['active']==True:
                        data['active_coin'] = coin
                        await check_actual_price_mov_data(coin, state) 
                        subscribe_response = await subscribe_1(coin, state)
                        subscribe_response = clearning_str(subscribe_response)
                        await Testing_state.subscribing.set()
                        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
                        await sin_bot.send_message (user_id, text='Если хотите отменить подписку нажмите /cancel.', reply_markup=keyb_client_3)
                    else:
                        subscribe_response = await subscribe_1(coin, state)
                        subscribe_response = clearning_str(subscribe_response)
                        await Testing_state.get_btc_historical_data.set()
                        #await sin_bot.send_message(user_id, my_response)
                        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
                        await sin_bot.send_message (user_id, text='Подписка отменена', reply_markup=keyb_client_1)
                        break
    except ValueError as e:
        await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от 60 до 880')
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
 
    
    

if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=False,)     
