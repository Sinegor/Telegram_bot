import aiohttp
import json
import time
import asyncio
import datetime
import pandas
import datetime

from models import Responce_template, SymbolCoinError
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiohttp import ClientSession


def string_handling(str:str):
    """
    Removes random capital letters and spaces in the coin names,
    recieved from user
    """
    return str.rstrip().lstrip().lower()


async def make_connection(session:ClientSession, url, params=None):
    """ 
    Universal function to direct asynchronous get request to any API 
resource Coin Geko.  Takes into account the peculiarity of free Coin Geko API
 - periodically not to accept requests for some time
    """
    async with session.get(url, params=params,) as response:
           if response.status == 429:
               time_delta = int(response.headers['Retry-After'])
               raise TimeoutError(time_delta)
           elif response.reason == 'Not Found':
               raise SymbolCoinError
           else:
                return await response.text()

async def check_symbol(symbol:str):
    """
    The bot works only with the full name of the coins, if the user passed the symbol coin, 
    this function will return the possible name of the coin.
    """
    async with aiohttp.ClientSession() as session:
        url = 'https://api.coingecko.com/api/v3/coins/list?include_platform=false'
        crud_crypto_list:list = await make_connection(session, url)
        crypto_list = json.loads(crud_crypto_list)
        possible_coin = []
        [possible_coin.append(crypto['id']) for crypto in crypto_list if crypto['symbol']==symbol]
        if possible_coin != []:
            return [possible_coin]
        else:
            raise KeyError ('Указанной вами монеты не существует или она не поддерживается!')


async def check_actual_alt_state(alt, 
                                 my_state:FSMContext, 
                                 init_alt_price=None):
    """
    Check the validity of the information in Memory Storage on the selected coin: 
    the price at the time of yesterday and today (['price'][alt]['coins_last_prices'])
    If necessary, the data is updated. 
    """
    today_date = datetime.date.today().strftime('%d-%m-%Y')
    async with my_state.proxy() as data:
        if alt not in data['price'].keys():
            if init_alt_price == None:
                init_alt_price = await get_yesterday_data_price(alt)
            data['price'][alt] = {'coins_last_prices':{
                                    "today":today_date, "yesterday_price": init_alt_price, \
                                   "last_today_price": {'value': init_alt_price, 'date':None}
                                                        },
                                   'clean_price_movement':{ "active":False,
						                                   "today": None,
						                                    'history': [],
						                                    'today_mov':[]
                                                            }                        
                                    }
            return "basic request"
        elif today_date != data['price'][alt]['coins_last_prices']['today']:   
            last_alt_price = await get_yesterday_data_price(alt)
            data['price'][alt]['coins_last_prices']['yesterday_price'] = last_alt_price
            data['price'][alt]['coins_last_prices']['today_date'] = today_date
            if data['price'][alt]['coins_last_prices']['last_today_price']['date'] != None:
                data['price'][alt]['coins_last_prices']['last_today_price']['date'] =datetime.datetime.fromtimestamp(time.time()-84600).date().strftime('%d-%m-%Y')
        return 'second request' 
    

async def check_actual_price_mov_data(coin, state:FSMContext):
    """
    Check the validity of the information in Memory Storage on the selected coin: 
    today clean price movement ['price'][alt]['clean_price_movement']
    If necessary, the data is updated. 
    """
    today_date = datetime.datetime.today().date()
    async with state.proxy() as data:
        if data['price'][coin]['clean_price_movement']['today'] == None:
            data['price'][coin]['clean_price_movement']['today'] = today_date
        elif data['price'][coin]['clean_price_movement']['today'] != today_date:
            await check_actual_btc_history(state)
            await check_actual_price_mov_data(coin, state)
            data['price'][coin]['clean_price_movement']['today'] = today_date
            data['price'][coin]['clean_price_movement']['today_mov'] = []
            return 'second request'


async def check_actual_btc_history(state:FSMContext):
    """
    Check the validity of the information in Memory Storage 
    'bitcoin_history' (last seven days)
    """
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
                data['price']['bitcoin_history'] = data['price']['bitcoin_history'][day_delta:]


async def check_historical_pure_price_mov_data(alt:str, state:FSMContext):
    """
    Check the validity of the information in Memory Storage on the selected coin: 
    historical clean price movement
    """
    yesterday = datetime.datetime.fromtimestamp(time.time()-86400)
    async with state.proxy() as data:
        checking_data = data['price'][alt]['clean_price_movement']['history']
        if checking_data ==[]:
            crud_data= await get_last_week_coin_history(alt)
            coin_data = crud_data[(-6):]
            btc_data = data['price']['bitcoin_history'][(-6):]
            data['price'][alt]['clean_price_movement']['history'] = get_historical_pure_price_mov(coin_data, btc_data)
            return False
        else:
            last_date_str = list(checking_data[-1].keys())[0]
            last_date = datetime.datetime.strptime(last_date_str, '%d-%m-%Y')
            time_delta = (yesterday-last_date).days
            if time_delta !=0:
                crud_data= await get_last_week_coin_history(alt)
                coin_data = crud_data[(-6):]
                btc_data = data['price']['bitcoin_history'][(-6):]
                return get_historical_pure_price_mov(coin_data, btc_data)
            else:
                return False
            


def get_historical_pure_price_mov(alt_data, btc_data):
    """
    Calculating the net price movement of altcoin
    """
    alt_clear_mov_history = []
    for i in range(6):
        key = list(btc_data[i].keys())[0]
        clear_mov = f"{round((float(alt_data[i]['changes'][:-1]) - float (btc_data[i]['changes'][:-1])),2)}%"
        crud_dict = {key:clear_mov}
        alt_clear_mov_history.append(crud_dict)
    return alt_clear_mov_history
        
# Функция для свободной команды, используется в set_starting_data. Получает данные об изменениях цены актива за прошедшую неделю:
async def get_yesterday_data_price(crypto_asset, fiat_coin='usd'):
        """
        Obtaining data on the crypto asset price for the yesterday
        """
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
        except SymbolCoinError as e:
            possible_coins_list = await check_symbol(crypto_asset)
            possible_coins_str = clearning_str(str(possible_coins_list), *',')
            raise SymbolCoinError(possible_coins_str)
            

async def get_last_week_coin_history(coin, fiat_coin='usd'):
    """
        Obtaining data on the crypto asset price for the last week
    """
    price_coin_data = []
    day_ago = 7
    async with aiohttp.ClientSession() as session:
            while day_ago>=1:
                try:    
                    my_url = f'https://api.coingecko.com/api/v3/coins/{coin}/history'
                    time_stamp = time.time()-86400*day_ago
                    date_request = datetime.datetime.fromtimestamp(time_stamp).date()
                    date_param = date_request.strftime('%d-%m-%Y')
                    my_params = {'date':date_param}
                    crud_data = await make_connection(session, my_url, my_params)
                    data_price= round(json.loads(crud_data)['market_data']['current_price'][fiat_coin],2)
                    crud_dict = {f'{date_param}':data_price}
# Starting with the second element of the array, we add a percentage 
# change of the price to the dictionary elements in addition to the price:
                    if day_ago<7:
                        previous_price = price_coin_data[-1][list(price_coin_data[-1].keys())[0]]
                        crud_dict['changes'] = f'{round((data_price-previous_price)*100/previous_price,2)}%' 
                        
                    price_coin_data.append(crud_dict)
                    day_ago-=1 
                except KeyError as e:
                    continue
            return price_coin_data
    

async def get_extra_coin_history(coin:str, period:int, last_value, fiat_coin:str ='usd'):
    """
    Update of the weekly asset price history if the cache is out of date
    """
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
# Starting with the second element of the array, we add a percentage 
# change of the price to the dictionary elements in addition to the price:
                    if type(last_value) == float or int:
                        if price_coin_data ==[]:
                            previous_price = last_value    
                        crud_dict['changes'] = f'{round((data_price-previous_price)*100/previous_price,2)}%' 
                        price_coin_data.append(crud_dict)
                        previous_price = data_price
                        day_ago-=1         
                    else: 
                        if price_coin_data ==[]:
                            previous_data = last_value
                        crud_dict['changes'] = f''  
            return price_coin_data

        


def get_previous_week_pure_price_mov(alt_price_list, btc_price_list):
    """ Based on the weekly price change of altcoin and bitcoin calculates 
        the last week’s pure altcoin price movement.
    """
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



async def get_crypto_price(*crypto_assets, fiat_coin='usd'):
    """
    Get the current price of the crypto assets requested by the user
    """
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
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}:
            return result_data 
    except KeyError as e:
        print(e)


def get_current_pure_price_mov (last_price_accet,
                        cur_price_accet,
                        last_price_btc,
                        cur_price_btc):
    """
    Calculates the free price movement of the crypto asset inside the day. The interval is specified by the user.
    """
    result_obj ={}
    if (cur_price_accet-last_price_accet)*(cur_price_btc-last_price_btc)>0:
        result_obj['Price movement in one direction'] = True
    else:
        result_obj['Price movement in one direction'] = False
    result_obj['Bitcoin price movement'] = round((cur_price_btc-last_price_btc)/last_price_btc*100,2)
    result_obj['Current altcoin price movement'] = round((cur_price_accet-last_price_accet)/last_price_accet*100,2)
    result_obj['Pure price movement data'] = round(result_obj['Current altcoin price movement']-result_obj['Bitcoin price movement'],2)
    return result_obj


async def set_starting_data (altcoin):
    try:
        alt_previous_price = await get_yesterday_data_price(altcoin)
        btc_previous_price = await get_yesterday_data_price('bitcoin')
        yesterday_time = datetime.datetime.fromtimestamp(time.time()-86400).date().strftime('%d-%m-%Y')
        return {"alt":alt_previous_price,'btc': btc_previous_price, 'time': yesterday_time}
    except KeyError:
        raise KeyError


def clearning_str(str, *mark_ignor):
    """
    The Coin Geko Response Cleanup feature removes extra characters from the line.
    There is a list of default characters that you want to exclude from the - clear_list string. 
    If necessary, you can remove something from this list - mark_ignor. As a result, 
    we replace the specified characters with None in the function string

    """
    clear_list = ["'", '"', "(", ")", '{', '}', ',', '[',']']
    if mark_ignor !=():
        [clear_list.remove(value) for value in mark_ignor]
        return str.translate({ord(i): None for i in clear_list })
    else:
        return str.translate({ord(i): None for i in clear_list })


def handler_history_data(list):
    """
    Function for cleaning the received historical data 
    """

    result_str =''
    for i in range(len(list)):
        crud_str= clearning_str(str(list[i]))
        result_str = result_str+crud_str+'\n'+'\n'
    return result_str


async def subscribe (crypto_asset, state:FSMContext):
    """
    The function to subscribe for tracking the net price movement of the first crypto asset.
    """
    current_pricies = await get_crypto_price('bitcoin', crypto_asset)
    actual_btc_price, actual_alt_price, actual_btc_time, actual_alt_time = current_pricies['bitcoin'], current_pricies[crypto_asset],\
    current_pricies['date'], current_pricies['date']
    async with state.proxy() as data:
        data['active_coin'] = crypto_asset
        data['price'][crypto_asset]['coins_last_prices']['last_today_price']['value'] = actual_alt_price
        data['price'][crypto_asset]['coins_last_prices']['last_today_price']['date'] = actual_alt_time
        data['price']['bitcoin']['coins_last_prices']['last_today_price']['value'] = actual_btc_price
        data['price']['bitcoin']['coins_last_prices']['last_today_price']['date'] = actual_alt_time
        
        btc_last_data = data['price']['bitcoin']['coins_last_prices']['yesterday_price']
        alt_last_data = data['price'][crypto_asset]['coins_last_prices']['yesterday_price']
    current_move_price_data = get_current_pure_price_mov(alt_last_data, actual_alt_price, btc_last_data, actual_btc_price)      
    response_inst = Responce_template(crypto_asset,
                                            current_move_price_data, 
                                          **current_pricies)
    crud_data_for_response = response_inst.create_basic_responce()
    return response_inst
        
        
async def subscribe_1(crypto_asset, state:FSMContext):
        """
        Feature to subscribe for tracking a net price crypto asset if there is a subscription to another crypto asset
        """
        current_pricies = await get_crypto_price('bitcoin', crypto_asset)
        actual_btc_price, actual_alt_price, actual_alt_time = current_pricies['bitcoin'], current_pricies[crypto_asset], current_pricies['date']
        async with state.proxy() as data:
            btc_last_price = data['price']['bitcoin']['coins_last_prices']['last_today_price']['value']
            btc_last_time = data['price']['bitcoin']['coins_last_prices']['last_today_price']['date']
            alt_last_price = data['price'][crypto_asset]['coins_last_prices']['last_today_price']['value']
            alt_last_time = data['price'][crypto_asset]['coins_last_prices']['last_today_price']['date']
         
        current_move_price_data = get_current_pure_price_mov(alt_last_price, actual_alt_price, btc_last_price, actual_btc_price)      
        response_inst = Responce_template(crypto_asset,
                                            current_move_price_data, 
                                          **current_pricies)
        history_data = response_inst.create_history_mov_data()
        async with state.proxy() as data:
                data['price']['bitcoin']['coins_last_prices']['last_today_price']['value'] = actual_btc_price
                data['price'][crypto_asset]['coins_last_prices']['last_today_price']['value'] = actual_alt_price
                data['price'][crypto_asset]['coins_last_prices']['last_today_price']['date'] = actual_alt_time
                data['price']['bitcoin']['coins_last_prices']['last_today_price']['date'] =  actual_alt_time
                data['price'][crypto_asset]['clean_price_movement']['today_mov'].append(history_data)
                

        return response_inst
