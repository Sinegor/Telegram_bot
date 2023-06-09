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
from models import SymbolCoinError, Responce_template


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
#Formation of Memory Storage structure for new user:
    async with state.proxy() as data:
        data['price']= {  
        'bitcoin_history':[],
        }   
        data['active_coin'] = None
        await sin_bot.send_message(user_id, START_MESSAGE.format(user_name), reply_markup=keyb_client)



@sin_disp.message_handler(commands=["history"], state="*")
async def history_handler(message, state:FSMContext):
    """
    Custom button processing "Histoty". 
    We get data about price movements of the bitcoin for the last week
    """
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
    # Caching Bitcoin Data to Retrieve History from Memory Storage if Repeated Requests:
            await Testing_state.get_btc_historical_data.set()
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")



@sin_disp.message_handler(commands=['alt_subscribe'], state=Testing_state.get_pure_alt_move)
async def handler_request_subscribe (message: types.Message, state:FSMContext):
    """
    Handler "custom keyboard button "alt_subscribe", suggests to specify the interval 
    through which the user will receive new data
    """
    user_id = message.from_id
    await sin_bot.send_message(user_id, "Укажите c какой переиодичностью вы хотели бы получать информацию. От 30 до 300 минут", reply_markup=keyb_client_2)
    await Testing_state.request_subscribe.set()


@sin_disp.message_handler(commands=['home'], state=Testing_state.get_pure_alt_move)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    """
    State of Memory Storage reset to 'get_btc_historical_data'
    """
    user_id = message.from_id
    await Testing_state.get_btc_historical_data.set()
    await sin_bot.send_message(user_id, text='Вы вернулись на первоначальный экран', reply_markup=keyb_client)


@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.get_pure_alt_move)
async def st_handler_1 (message: types.Message, state:FSMContext):
    """
    Handler "custom keyboard button "alt_history". We receive data for a week on net price movement altcoin. 
    In the event that coin lags far behind Bitcoin or is far ahead of it, emojis are added. 
    """
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
                last_data:str = crud_data[-1][f'{datetime.datetime.fromtimestamp(time.time()-86400).strftime("%d-%m-%Y")}']
                data_float = float(last_data[0:-1])
                await sin_bot.send_message(user_id, f'<b>Pure price movement history of {coin}:</b>', parse_mode='HTML')
                await sin_bot.send_message(user_id, text=clear_data)
                if data_float >3:
                   await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
                elif data_float <-3:
                    await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
            else:
                [data['price'][coin]['clean_price_movement']['history'].append(value) for value in result]
                crud_data = data['price'][coin]['clean_price_movement']['history']
                clear_data = handler_history_data(crud_data)
                last_data:str = crud_data[-1][f'{datetime.datetime.fromtimestamp(time.time()-86400).strftime("%d-%m-%Y")}']
                data_float = float(last_data[0:-1])
                await sin_bot.send_message(user_id, f'<b>Pure price movement history of {coin}:</b>', parse_mode='HTML')
                await sin_bot.send_message(user_id, clear_data)
                if data_float >3:
                   await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
                elif data_float <-3:
                    await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')


@sin_disp.message_handler(state=None)
async def handler_get_alt_data_1 (message: types.Message, state:FSMContext):
    """
    Request a pure price movement aitcoin for last day from the state "None". Primary.
    """
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        yesterday_data = await set_starting_data(coin)
        await check_actual_alt_state(coin, state, yesterday_data['alt'])
        await check_actual_alt_state('bitcoin', state, yesterday_data['btc'])
        crud_subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(crud_subscribe_response.create_basic_responce())
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
        if crud_subscribe_response.current_move_price_data['Pure price movement data']>3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
        elif crud_subscribe_response.current_move_price_data['Pure price movement data']<-3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
    except KeyError as e:
        await sin_bot.send_message(user_id, "Такая монета не поддерживается, проверьте правильность написания", 
                                   reply_markup=keyb_client)
    

@sin_disp.message_handler(state=Testing_state.get_btc_historical_data)
async def handler_get_alt_data_2 (message: types.Message, state:FSMContext):
    """
    Request a pure price movement aitcoin for last day from the state "get_btc_historical_data".
    """
    user_id = message.from_id
    coin = string_handling(message.text)
    try:
        await check_actual_alt_state(coin, state)
        crud_subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(crud_subscribe_response.create_basic_responce())
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
        if crud_subscribe_response.current_move_price_data['Pure price movement data']>3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
        elif crud_subscribe_response.current_move_price_data['Pure price movement data']<-3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 


@sin_disp.message_handler(state=Testing_state.get_pure_alt_move)
async def handler_get_alt_data_3 (message: types.Message, state:FSMContext):
    """
    Request a pure price movement aitcoin for last day from the state "get_pure_alt_move"
    """
    try:
        user_id = message.from_id
        coin = string_handling(message.text)
        await check_actual_alt_state(coin, state)
        crud_subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(crud_subscribe_response.create_basic_responce())
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        await Testing_state.get_pure_alt_move.set()
        if crud_subscribe_response.current_move_price_data['Pure price movement data']>3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
        elif crud_subscribe_response.current_move_price_data['Pure price movement data']<-3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 
   
@sin_disp.message_handler(commands=['cancel'], state=Testing_state.subscribing)
async def handler_cancel_1 (message: types.Message, state:FSMContext):
    """
    Unsubscribe from Coin tracking
    """
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['active_coin']
        data['price'][coin]['clean_price_movement']['active'] = False
    await Testing_state.get_btc_historical_data.set()
    await sin_bot.send_message(user_id, text='Подписка отменена. \
                                       Введите название актива, по которому вы хотите получить информацию', reply_markup=keyb_client)



@sin_disp.message_handler(commands=['alt_history'], state=Testing_state.subscribing)
async def st_handler_1 (message: types.Message, state:FSMContext):
    """
    Getting information on the coin last week from the state "subscribing"
    """
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
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML') 
        

@sin_disp.message_handler(state=Testing_state.subscribing)
async def handler_get_alt_data_2 (message: types.Message, state:FSMContext):
    """
    Getting the coin data for the previous day from the state "subscribing"(when another coin is tracked)
    """

    try:
        user_id = message.from_id
        coin = string_handling(message.text)
        await check_actual_alt_state(coin, state)
        crud_subscribe_response = await subscribe(coin, state)
        subscribe_response = clearning_str(crud_subscribe_response.create_basic_responce())
        await Testing_state.get_pure_alt_move.set()
        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
        if crud_subscribe_response.current_move_price_data['Pure price movement data']>3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
        elif crud_subscribe_response.current_move_price_data['Pure price movement data']<-3:
            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
    except KeyError as e:
        await message.reply("Такая монета не поддерживается, проверьте правильность написания", reply_markup=keyb_client)
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")
    except SymbolCoinError as e:
        my_message = f' Попробуйте следующее название/ия:\n<b>{e}</b>'
        await sin_bot.send_message(user_id, my_message, reply_markup=keyb_client, parse_mode='HTML')
 

@sin_disp.message_handler(state=Testing_state.request_subscribe, commands=['cancel'])
async def handler_subscribe (message: types.Message,  state:FSMContext):
    """
    Reset subscription procedure from "request_subscribe" status (subscription not yet established)
    """
    user_id = message.from_id
    async with state.proxy() as data:
        coin = data['active_coin']
        data['price'][coin]['clean_price_movement']['active'] = False
    await Testing_state.get_pure_alt_move.set()
    await sin_bot.send_message(user_id, "Подписка отменена!", reply_markup=keyb_client_1)



@sin_disp.message_handler(state=Testing_state.request_subscribe)
async def handler_subscribe (message: types.Message, state:FSMContext):
    """
    Getting a subscription time interval from the user and its design
    """
    user_id = message.from_id
    current_date = datetime.datetime.now()
    try:
        value = int(message.text)
        if value > 300 or value < 30:
            await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от 30 до 300')
            
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
                        
                        response_inst = await subscribe_1(coin, state)
                        crud_data_for_response = response_inst.create_basic_responce()
                        subscribe_response = clearning_str(crud_data_for_response)
                        await Testing_state.subscribing.set()
                        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
                        if response_inst.current_move_price_data['Pure price movement data']>3:
                            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
                        elif response_inst.current_move_price_data['Pure price movement data']<-3:
                            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
                        await sin_bot.send_message (user_id, text='Если хотите отменить подписку нажмите /cancel.', reply_markup=keyb_client_3)
                    else:
                        response_inst = await subscribe_1(coin, state)
                        crud_data_for_response = response_inst.create_basic_responce()
                        subscribe_response = clearning_str(crud_data_for_response)
                        await Testing_state.get_btc_historical_data.set()        
                        await sin_bot.send_message(user_id, subscribe_response, parse_mode="HTML", reply_markup=keyb_client_1)
                        if response_inst.current_move_price_data['Pure price movement data']>3:
                            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqItkQYwRYaRvKyla92ymdZWPCaJEhAAC3AsAAt8K6Uo-ZVuZEObjpC8E')
                        elif response_inst.current_move_price_data['Pure price movement data']<-3:
                            await sin_bot.send_sticker(user_id, 'CAACAgIAAxkBAAEIqH1kQYuBMBnCMxkG3TbC9gdz9mADGAACKwADspiaDvxK5u_xtoLRLwQ')
                        await sin_bot.send_message (user_id, text='Подписка отменена', reply_markup=keyb_client_1)
                        break
    except ValueError as e:
        await sin_bot.send_message(user_id, 'Вы ввели некорректные данные. Введите цифру от 30 до 300')
    except TimeoutError as e:
        await sin_bot.send_message(user_id, f"Повторите запрос через {e.args[0]} секунд")


if __name__ == '__main__':
    executor.start_polling(sin_disp,timeout=200, skip_updates=False,)     
