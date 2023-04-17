import aiohttp
import json
import time
import asyncio
import datetime
import pandas
import datetime

from models import price, today_pure_price_mov, global_pure_price_mov
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiohttp import ClientSession


def string_handling(str:str):
    return str.rstrip().lstrip().lower()
# Проверка актуальности раздела ['price']['coins_last_prices'][alt] в MemoryStorage
async def check_actual_alt_state(alt, 
                                 my_state:FSMContext, 
                                 init_alt_price=None):
    today_date = datetime.date.today().strftime('%d-%m-%Y')
    async with my_state.proxy() as data:
        if alt not in data['price']['coins_last_prices'].keys():
            if init_alt_price == None:
                init_alt_price = await get_yesterday_data_price(alt)
            data['price']['coins_last_prices'][alt] = {"today_date":today_date, "yesterday_price": init_alt_price, \
                                                       "last_today_price": {'value': init_alt_price, 'date':{datetime.date.fromtimestamp(time.time()-86400)}} }
            return "basic request"
        elif today_date != data['price']['coins_last_prices'][alt]['today_date']:   
            last_alt_price = await get_yesterday_data_price(alt)
            data['price']['coins_last_prices'][alt]['last_today_price']['value'] = last_alt_price
            data['price']['coins_last_prices'][alt]['last_today_price']['date'] = data['price']['coins_last_prices'][alt]['today_date']
            data['price']['coins_last_prices'][alt]['yesterday_price'] = last_alt_price
            data['price']['coins_last_prices'][alt]['today_date'] = today_date
        return 'second request'
    
async def check_actual_price_mov_data(coin, state:FSMContext):
    today_date = datetime.date.today().strftime('%d-%m-%Y')
    async with state.proxy() as data:
        if coin not in data['price']['clean_price_movement'].keys():
            data['price']['clean_price_movement'][coin] = {
                'today': today_date,
                'today_mov':{},
                'history':[]
            }
            return 'basic request'
# необходимо продумать функционал в этой частиЖ
        elif data['price']['clean_price_movement'][coin]['today'] != today_date:
            data['price']['clean_price_movement'][coin]['histoty'] = data['price']['clean_price_movement'][coin]['today_mov']
            data['price']['clean_price_movement'][coin]['today_mov'] = {}
            return 'second request'

# Проверка актуальности раздела bitcoin_history
async def check_actual_btc_history(state:FSMContext):
    yesterday = datetime.datetime.fromtimestamp(time.time()-86400)
    async with state.proxy() as data:
        bitcoin_history = data['price']['bitcoin_history']
        if len(bitcoin_history) == 0:
            data['price']['bitcoin_history'] = await get_last_week_coin_history('bitcoin')
        else:    
            history_last_str_key = list(bitcoin_history[-1].keys())[0]
            last_key_date = datetime.datetime.strptime(history_last_str_key, '%d-%m-%Y')
            day_delta = (yesterday-last_key_date).days
            if day_delta !=0:
                last_coin_price = bitcoin_history[-1][history_last_str_key]
                extra_history = await get_extra_coin_history('bitcoin',day_delta, last_coin_price )
                [data['price']['bitcoin_history'].append(new_result) for new_result in extra_history]

async def check_historical_pure_price_mov_data(alt:str, state:FSMContext):
    yesterday = datetime.datetime.fromtimestamp(time.time()-86400)
    async with state.proxy() as data:
        checking_data = data['price']['clean_price_movement'][alt]['history']
        if checking_data ==[]:
            crud_data= await get_last_week_coin_history(alt)
            coin_data = crud_data[(-6):]
            btc_data = data['price']['bitcoin_history'][(-6):]
            return get_historical_pure_price_mov(coin_data, btc_data)
        else:
            last_date_str = list(checking_data[-1].keys())[0]
            last_date = datetime.datetime.strptime(last_date_str, '%d-%m-%Y')
            time_delta = (yesterday-last_date).days()
            if time_delta !=0:
                last_coin_price= checking_data[-1][last_date_str]
                extra_history:list = await get_extra_coin_history(alt,time_delta, last_coin_price )
                await check_actual_btc_history()
                extra_btc_data:list = data['price']['bitcoin_history'][-time_delta:]
                extra_result = get_historical_pure_price_mov(extra_history, extra_btc_data)
                return extra_result
            else:
                return False
            

def get_historical_pure_price_mov(alt_data, btc_data):
    alt_clear_mov_history = []
    for i in range(6):
        key = list(btc_data[i].keys())[0]
        clear_mov = f"{round((float(alt_data[i]['changes'][:-1]) - float (btc_data[i]['changes'][:-1])),2)}%"
        crud_dict = {key:clear_mov}
        alt_clear_mov_history.append(crud_dict)
    return alt_clear_mov_history
        
# Функция для свободной команды, используется в set_starting_data. Получает данные об изменениях цены актива за прошедшую неделю:
async def get_yesterday_data_price(crypto_asset, fiat_coin='usd'):
        try:
            connector = aiohttp.TCPConnector(limit=50, force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                my_url = f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history'
                time_stamp = time.time()-86400
                date_request = datetime.datetime.fromtimestamp(time_stamp).date()
                date_param = f'{date_request.strftime("%d-%m-%Y")}'
                my_params = {'date':date_param}
                response_data = await make_connection(session, my_url, my_params)
                data_price= (json.loads(response_data)['market_data']['current_price'][fiat_coin])                        
                
                return data_price
        except KeyError as e:
            raise KeyError

# Базовая функция направления get-запроса, в которую передаётся объект сессии + параметры запроса.
async def make_connection(session:ClientSession, url, params):
       async with session.get(url, params=params,) as response:
           if response.status == 429:
               time_delta = int(response.headers['Retry-After'])
               print(time_delta)
               await asyncio.sleep(time_delta)
               return await make_connection(session, url, params)
           if response.reason == 'Not Found':
               raise KeyError

           return await response.text()

# Функция для обработки команды "History": цена за неделю по дням.
# Необходимо добавить обработчик ошибок
async def get_last_week_coin_history(coin, fiat_coin='usd'):
    """ Get stock price data for the past seven days """
    price_coin_data = []
    day_ago = 7
    async with aiohttp.ClientSession() as session:
            while day_ago>=1:
                try:    
                    my_url = f'https://api.coingecko.com/api/v3/coins/{coin}/history'
                    time_stamp = time.time()-86400*day_ago
                    date_request = datetime.datetime.fromtimestamp(time_stamp).date()
                    date_param = date_request.strftime('%d-%m-%Y')
                    #date_param = f'{date_request.day}-{date_request.month}-{date_request.year}'
                    my_params = {'date':date_param}
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= round(json.loads(crud_data)['market_data']['current_price'][fiat_coin],2)
                    crud_dict = {f'{date_param}':data_price}
# Начиная со второго элемента массива мы добавляем в элементы-словари помимо цены процент изменения:
                    if day_ago<7:
                        previous_price = price_coin_data[-1][list(price_coin_data[-1].keys())[0]]
                        crud_dict['changes'] = f'{round((data_price-previous_price)*100/previous_price,2)}%' 
                        
                    price_coin_data.append(crud_dict)
                    day_ago-=1 
                except KeyError as e:
                    print ('Ошибка при получении истории. 145')
                    continue
            return price_coin_data

async def get_extra_coin_history(coin:str, period:int, last_value, fiat_coin:str ='usd'):
    price_coin_data = []
    day_ago = period
    async with aiohttp.ClientSession() as session:
            while day_ago>=period:
                    my_url = f'https://api.coingecko.com/api/v3/coins/{coin}/history'
                    time_stamp = time.time()-86400*day_ago
                    date_request = datetime.datetime.fromtimestamp(time_stamp).date()
                    date_param = date_request.strftime('%d-%m-%Y')
                    my_params = {'date':date_param}
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= round(json.loads(crud_data)['market_data']['current_price'][fiat_coin],2)
                    crud_dict = {f'{date_param}':data_price}
# Начиная со второго элемента массива мы добавляем в элементы-словари помимо цены процент изменения:
                    if price_coin_data ==[]:
                        previous_price = last_value
                    crud_dict['changes'] = f'{round((data_price-previous_price)*100/previous_price,2)}%' 
                    price_coin_data.append(crud_dict)
                    previous_price = data_price
                    day_ago-=1 
            return price_coin_data

        

# Функция для свободной команды. Используется в set_starting_data. На основании передаваемых данных о недельном изменении цены альта
# и битка производит расчёт чистового ценового движения альта за прошлую неделю.
def get_previous_week_pure_price_mov(alt_price_list, btc_price_list):
    """ Net asset price movement for the past six days less Bitcoin price movement """
    global global_pure_price_mov
    alt_mov = [((alt_price_list[i]-alt_price_list[i-1])/alt_price_list[i-1]*100) for i in range(1,7)]
    btc_mov = [((btc_price_list[i]-btc_price_list[i-1])/btc_price_list[i-1]*100) for i in range(1,7)]
    for i in range(6):
        cur_time_stamp = time.time()-86400*(6-i)
        date = str(datetime.datetime.fromtimestamp(cur_time_stamp).date())
        global_pure_price_mov[date]= f"{round((alt_mov[i] - btc_mov[i]),2)} %"
    my_response = pandas.Series(global_pure_price_mov, global_pure_price_mov.keys())
    return my_response
# template response: {'2023-03-18': -0.7900000000000009, '2023-03-19': -3.1, '2023-03-20': -1.5, '2023-03-21': -5.06, '2023-03-22': 3.4799999999999995, '2023-03-23': -2.0}


# Функция для свободной команды, получает текущую цену переданных криптоактивов.
async def get_crypto_price(*crypto_assets, fiat_coin='usd'):
    # while (True):
    try:
        connector = aiohttp.TCPConnector(limit=50, force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            params_query = {
            'ids': ','.join(crypto_assets),
            'vs_currencies': fiat_coin
            }
            my_url = 'https://api.coingecko.com/api/v3/simple/price'
            response_data = await make_connection(session, my_url, params_query)
            data_dict = json.loads(response_data)
            time_geting_data  = datetime.datetime.now().strftime('%d.%m %H:%M')
            result_data = {}
            result_data['date'] = time_geting_data
            for crypto in crypto_assets:
                result_data[crypto]= data_dict[crypto][fiat_coin] 
            return result_data 
    except KeyError as e:
        print(e)
        # continue 
    
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}

# Функция для свободной команды - расчитывает текущее свободное ценовое движение актива (с момента последней отсечки)
def get_current_pure_price_mov (last_price_accet,
                        cur_price_accet,
                        last_price_btc,
                        cur_price_btc):
    result_obj ={}
    if (cur_price_accet-last_price_accet)*(cur_price_btc-last_price_btc)>0:
        result_obj['Price movement in one direction'] = True
    else:
        result_obj['Price movement in one direction'] = False
    result_obj['Bitcoin price movement'] = round((cur_price_btc-last_price_btc)/last_price_btc*100,2)
    result_obj['Current altcoin price movement'] = round((cur_price_accet-last_price_accet)/last_price_accet*100,2)
    #print (result)
    result_obj['Pure price movement data'] = round(result_obj['Current altcoin price movement']-result_obj['Bitcoin price movement'],2)
    #print (result_obj['Price movement data'])
    today_pure_price_mov.append(result_obj)
    return result_obj
#template of response: {'date': 'Mon Mar 20 15:50:05 2023', 'Price movement in one direction': True, 'Price movement data': 0.0074}

# Функция для "свободной команды": Сборная функция:  1. получает данные о недельном ценовом движении битка + выбранного альта. 2. Определяет начальное 
# прошлое ценовое движение для битка и альта. 3. Возвращает данные о чистом ценовом движении актива за прошедшую неделю:
async def set_starting_data (altcoin):
    try:
        alt_previous_price = await get_yesterday_data_price(altcoin)
        btc_previous_price = await get_yesterday_data_price('bitcoin')
        yesterday_time = datetime.datetime.fromtimestamp(time.time()-86400).date().strftime('%d-%m-%Y')
        return {"alt":alt_previous_price,'btc': btc_previous_price, 'time': yesterday_time}
    except KeyError:
        raise KeyError


# Функция для для получения первичной информации по чистому движению актива:
async def subscribe (crypto_asset, state:FSMContext):
    current_pricies = await get_crypto_price('bitcoin', crypto_asset)
    actual_btc_price, actual_alt_price, actual_btc_time, actual_alt_time = current_pricies['bitcoin'], current_pricies[crypto_asset],\
    current_pricies['date'], current_pricies['date']
    yesterday_date = datetime.date.fromtimestamp(time.time()-86400).strftime('%d-%m-%Y')
    await check_actual_price_mov_data(crypto_asset, state)
    async with state.proxy() as data:
        data['active_coin'] = crypto_asset
        btc_last_data = data['price']['coins_last_prices']['bitcoin']['yesterday_price']
        alt_last_data = data['price']['coins_last_prices'][crypto_asset]['yesterday_price']
    current_move_price_data = get_current_pure_price_mov(alt_last_data, actual_alt_price, btc_last_data, actual_btc_price)
    async with state.proxy() as data:
        data['price']['coins_last_prices']['bitcoin']['last_today_price']['value'] = actual_btc_price
        data['price']['coins_last_prices'][crypto_asset]['last_today_price']['value'] = actual_alt_price
        data['price']['coins_last_prices'][crypto_asset]['last_today_price']['date'] = actual_alt_time
        data['price']['coins_last_prices']['bitcoin']['last_today_price']['date'] = actual_btc_time
        data['price']['clean_price_movement'][crypto_asset]['today_mov'][f'{yesterday_date[:-5:1]}:{current_pricies["date"]}'] = current_move_price_data
    crud_data_for_response = {
        'Asset': crypto_asset,
        f"Last price of BTC on {yesterday_date}:":f"{round(btc_last_data,2)}$",
        'Actual price of BTC:': f"{actual_btc_price}$",
        'Bitcoin price movement': f"{current_move_price_data['Bitcoin price movement']}%",
        f"Last price of {crypto_asset} on {yesterday_date}:":f"{round(alt_last_data,2)}$",
        f'Actual price of {crypto_asset}:': f"{round(actual_alt_price,2)}$",
        f'{crypto_asset} price movement:': f"{current_move_price_data['Current altcoin price movement']}%",
        'Asset price synchronization assets:': f"{current_move_price_data['Price movement in one direction']}",
        f'independent movement of an asset {crypto_asset}:': f"{current_move_price_data['Pure price movement data']}%"
    }

    return crud_data_for_response

# Функция для получения повторной информации по активу спустя указанное пользователем время.
async def subscribe_1(crypto_asset, state:FSMContext):
        current_pricies = await get_crypto_price('bitcoin', crypto_asset)
        actual_btc_price, actual_alt_price, actual_alt_time = current_pricies['bitcoin'], current_pricies[crypto_asset], current_pricies['date']
        async with state.proxy() as data:
            data['active_coin'] = crypto_asset
            btc_last_data = data['price']['coins_last_prices']['bitcoin']['last_today_price']['value']
            btc_last_time = data['price']['coins_last_prices']['bitcoin']['last_today_price']['date']
            alt_last_data = data['price']['coins_last_prices'][crypto_asset]['last_today_price']['value']
            alt_last_time = data['price']['coins_last_prices'][crypto_asset]['last_today_price']['date']
# А надо ли, если эта функция применяется для повторного запроса
        await check_actual_price_mov_data(crypto_asset, state)    
        current_move_price_data = get_current_pure_price_mov(alt_last_data, actual_alt_price, btc_last_data, actual_btc_price)
        async with state.proxy() as data:
            data['price']['coins_last_prices']['bitcoin']['last_today_price']['value'] = actual_btc_price
            data['price']['coins_last_prices'][crypto_asset]['last_today_price']['value'] = actual_alt_price
            data['price']['clean_price_movement'][crypto_asset]['today_mov'][f'{actual_alt_time}'] = current_move_price_data
        crud_data_for_response = {
            'Asset': f"{crypto_asset}:",
            'Bitcoin price movement': f"from {alt_last_time}: {current_move_price_data['Bitcoin price movement']}%",
            f'Actual price of {crypto_asset}:': f"{round(actual_alt_price,2)}$",
            f'{crypto_asset} price movement:': f"from {alt_last_time}: {current_move_price_data['Current altcoin price movement']}%",
            'Asset price synchronization assets:': f"{current_move_price_data['Price movement in one direction']}",
            f'independent movement of an asset {crypto_asset}:': f"{current_move_price_data['Pure price movement data']}%"
        }
        return crud_data_for_response


