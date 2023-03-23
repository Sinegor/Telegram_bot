import aiohttp
import json
import time
import sched
import asyncio
import datetime
import pandas

from models import price, today_pure_price_mov, global_pure_price_mov

async def set_starting_data (altcoin, yesterday_date, fiat_c='usd'):
    global price
    await get_previous_price('bitcoin', yesterday_date)
    await get_previous_price(altcoin, yesterday_date)
    price['last_price']['date'] = yesterday_date

def string_handling(str:str):
    return str.rstrip().lstrip().lower()



async def get_previous_price(crypto_asset, date, fiat_coin='usd',):
    """
arg date template: "xx-xx-xxxx"

    """
    global data_price
    async with aiohttp.ClientSession() as session:
        my_params = {'date':date}
        my_url = f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history'
        async with session.get(url=my_url,**{"params":my_params}) as response:
            response_data = await response.text()
            data_price= (json.loads(response_data)['market_data']['current_price'][fiat_coin])
            price['last_price'][crypto_asset] = data_price
            return data_price


async def get_crypto_price(*crypto_assets, fiat_coin='usd'):
    async with aiohttp.ClientSession() as session:
        params_query = {
        'ids': ','.join(crypto_assets),
        'vs_currencies': fiat_coin
        }
        my_url = 'https://api.coingecko.com/api/v3/simple/price'
        async with session.get(url=my_url, **{'params':params_query}) as response:
            response_data = await response.text()
            data_dict = json.loads(response_data)
            time_geting_data  = time.asctime()
            result_data = {}
            result_data['date'] = time_geting_data
            for crypto in crypto_assets:
                result_data[crypto]= data_dict[crypto][fiat_coin] 
            return result_data 
            
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}


def modificated_data_to_next_day ():
    global today_pure_price_mov, global_pure_price_mov, current_date
    interim_data=0
    for mov_price in today_pure_price_mov:
        interim_data+=mov_price['Pure price movement data']
    average_pure_price_mov = interim_data/len(today_pure_price_mov)
    global_pure_price_mov[f'{current_date}:']:round(average_pure_price_mov, 4)

    today_pure_price_mov.clear()
    current_date = datetime.datetime.now().date()
    print (f'Время сброса:{time.gmtime(time.time())}')
    return (global_pure_price_mov)



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

async def subscribe (crypto_asset, date):
    global price, today_pure_price_mov, global_pure_price_mov
    current_pricies = await get_crypto_price('bitcoin', crypto_asset)
    price['actual_price']['bitcoin'], price['actual_price'][crypto_asset], price['actual_price']['date'] = \
                                                                                current_pricies['bitcoin'],\
                                                                                current_pricies[crypto_asset],\
                                                                                current_pricies['date']

    today_pure_price_mov.append(get_current_pure_price_mov(price['last_price'][crypto_asset], 
                                                        price['actual_price'][crypto_asset],
                                                        price['last_price']['bitcoin'],
                                                        price['actual_price']['bitcoin']))
    current_move_price_data = get_current_pure_price_mov(price['last_price'][crypto_asset], 
                                                        price['actual_price'][crypto_asset],
                                                        price['last_price']['bitcoin'],
                                                        price['actual_price']['bitcoin'])

    crud_data_for_response = {
        f"Last price of BTC on {price['last_price']['date']}:":f"{round(price['last_price']['bitcoin'],2)}$",
        'Actual price of BTC:': f"{price['actual_price']['bitcoin']}$",
        'Bitcoin price movement': f"{current_move_price_data['Bitcoin price movement']}%",
        f"Last price of {crypto_asset} on {price['last_price']['date']}:":f"{round(price['last_price'][crypto_asset],2)}$",
        f'Actual price of {crypto_asset}:': f"{round(price['actual_price'][crypto_asset],2)}$",
        f'{crypto_asset} price movement:': f"{current_move_price_data['Current altcoin price movement']}%",
        'Asset price synchronization assets:': f"{current_move_price_data['Price movement in one direction']}",
        'Date:': current_move_price_data['date'],
        f'independent movement of an asset {crypto_asset}:': f"{current_move_price_data['Pure price movement data']}%"
    }
    my_response = pandas.Series(crud_data_for_response, crud_data_for_response.keys())
    price['last_price']['bitcoin'], price['last_price'][crypto_asset], price['last_price']['date'] = price['actual_price']['bitcoin'],\
                                                                                                        price['actual_price'][crypto_asset],\
                                                                                                        price['actual_price']['date']
    if  date != datetime.datetime.now().date():
        print ('Next day!')
        modificated_data_to_next_day()
        global_data = pandas.Series(global_pure_price_mov, global_pure_price_mov.keys())
        return (global_data, my_response)
    else:
        return my_response



# if __name__ == '__main__':
#     print(asyncio.run(main_handler('ethereum')))
    