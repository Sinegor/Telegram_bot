import aiohttp
import json
import time
import asyncio
import datetime
import pandas

from models import price, today_pure_price_mov, global_pure_price_mov
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext


def string_handling(str:str):
    return str.rstrip().lstrip().lower()


# Функция для свободной команды, используется в set_starting_data. Получает данные об изменениях цены актива за прошедшую неделю:
async def get_previous_data_price(crypto_asset, fiat_coin='usd'):
    connector = aiohttp.TCPConnector(limit=50, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        my_url = f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history'
        time_stamp = time.time()-86400
        date_request = datetime.datetime.fromtimestamp(time_stamp).date()
        date_param = f'{date_request.day}-{date_request.month}-{date_request.year}'
        my_params = {'date':date_param}
        response_data = await make_connection(session, my_url, my_params)
        data_price= (json.loads(response_data)['market_data']['current_price'][fiat_coin])                        
        return data_price

# Базовая функция направления get-запроса, в которую передаётся объект сессии + параметры запроса.
async def make_connection(session, url, params):
    async with session.get(url, params=params,) as response:
        response =  await response.text()
        return response

# Функция для обработки команды "History": цена за неделю по дням.
async def get_previous_week_btc_data_price_1(fiat_coin='usd'):
    """ Get stock price data for the past seven days """
    #price_btc_data = {}
    price_btc_data = []

    day_ago = 7
    async with aiohttp.ClientSession() as session:
            while day_ago>=1:
                try:
                    my_url = f'https://api.coingecko.com/api/v3/coins/bitcoin/history'
                    time_stamp = time.time()-86400*day_ago
                    date_request = datetime.datetime.fromtimestamp(time_stamp).date()
                    date_param = f'{date_request.day}-{date_request.month}-{date_request.year}'
                    my_params = {'date':date_param}
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= (json.loads(crud_data)['market_data']['current_price'][fiat_coin])
                    crud_dict = {f'{date_param}':data_price}
                    price_btc_data.append(crud_dict)
                    #price_btc_data[f'{date_param}:'] = data_price
                    day_ago-=1 
                except aiohttp.ServerDisconnectedError as e:
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= (json.loads(crud_data)['market_data']['current_price'][fiat_coin])
                    price_btc_data[date_param] = data_price
                    print (e, e.message)
                    day_ago-=1 
                    continue
                except aiohttp.ServerTimeoutError as e:
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= (json.loads(crud_data)['market_data']['current_price'][fiat_coin])
                    price_btc_data[date_param] = data_price
                    print (e, e.message)
                    day_ago-=1 
                    continue
                except json.decoder.JSONDecodeError as e:
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= (json.loads(crud_data)['market_data']['current_price'][fiat_coin])
                    price_btc_data[date_param] = data_price
                    print (e, e.message)
                    day_ago-=1 
                    continue
            
            return price_btc_data
        

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
    connector = aiohttp.TCPConnector(limit=50, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        params_query = {
        'ids': ','.join(crypto_assets),
        'vs_currencies': fiat_coin
        }
        my_url = 'https://api.coingecko.com/api/v3/simple/price'
        response_data = await make_connection(session, my_url, params_query)
        data_dict = json.loads(response_data)
        time_geting_data  = time.asctime()
        result_data = {}
        result_data['date'] = time_geting_data
        for crypto in crypto_assets:
            result_data[crypto]= data_dict[crypto][fiat_coin] 
        return result_data 
        
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}

# Функция для свободной команды - расчитывает текущее свободное ценовое движение актива (с момента последней отсечки)
def get_current_pure_price_mov (last_price_accet,
                        cur_price_accet,
                        last_price_btc,
                        cur_price_btc):
    global today_pure_price_mov
    result_obj ={}
    result_obj['date'] = time.asctime() 
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
    #global price
    alt_previous_price = await get_previous_data_price(altcoin)
    btc_previous_price = await get_previous_data_price('bitcoin')
    yesterday_time = datetime.datetime.fromtimestamp(time.time()-86400).date()
    return {"alt":alt_previous_price,'btc': btc_previous_price, 'time': yesterday_time}
    #price['last_price']['date'] = datetime.datetime.fromtimestamp(time.time()-86400).date()

# Функция для состояния, когда стартовые данные по битку уже получены:
async def set_starting_data_1 (altcoin):
    return await get_previous_data_price(altcoin)
    #btc_previous_price = await get_previous_data_price('bitcoin')
    
    #price['last_price'][altcoin] = alt_previous_price
    #price['last_price']['bitcoin'] = btc_previous_price
    #price['last_price']['date'] = datetime.datetime.fromtimestamp(time.time()-86400).date()


# Функция для "свободной команды": Сборная функция:
async def subscribe (crypto_asset, date, state:FSMContext):
    #global price, today_pure_price_mov
    current_pricies = await get_crypto_price('bitcoin', crypto_asset)
    actual_btc_price, actual_alt_price, actual_date  = current_pricies['bitcoin'], current_pricies[crypto_asset],current_pricies['date']
    async with state.proxy() as data:
        btc_last_data = data['price']['coins_last_prices']['bitcoin']['yesterday_price']
        alt_last_data = data['price']['coins_last_prices'][crypto_asset]['yesterday_price']
        yesterday_date =  data['price']['coins_last_prices']['bitcoin']['yesterday_date']
    current_move_price_data = get_current_pure_price_mov(alt_last_data, actual_alt_price, btc_last_data, actual_btc_price)
    crud_data_for_response = {
        f"Last price of BTC on {yesterday_date}:":f"{round(btc_last_data,2)}$",
        'Actual price of BTC:': f"{actual_btc_price}$",
        'Bitcoin price movement': f"{current_move_price_data['Bitcoin price movement']}%",
        f"Last price of {crypto_asset} on {yesterday_date}:":f"{round(alt_last_data,2)}$",
        f'Actual price of {crypto_asset}:': f"{round(actual_alt_price,2)}$",
        f'{crypto_asset} price movement:': f"{current_move_price_data['Current altcoin price movement']}%",
        'Asset price synchronization assets:': f"{current_move_price_data['Price movement in one direction']}",
        'Date:': current_move_price_data['date'],
        f'independent movement of an asset {crypto_asset}:': f"{current_move_price_data['Pure price movement data']}%"
    }
    my_response = pandas.Series(crud_data_for_response, crud_data_for_response.keys())
    # price['last_price']['bitcoin'], price['last_price'][crypto_asset], price['last_price']['date'] = price['actual_price']['bitcoin'],\
    #                                                                                                     price['actual_price'][crypto_asset],\
    #                                                                                                     price['actual_price']['date']
    
    return my_response


