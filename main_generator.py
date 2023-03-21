
import requests
import json
import time
import sched
import pandas

price = {
        'last_price': {},
        'actual_price':{}
}

today_pure_price_mov = []
global_pure_price_mov = {}

def set_starting_data(altcoin, yesterday_date, fiat_c='usd'):
    global price
    get_previous_price(fiat_c, 'bitcoin', yesterday_date)
    get_previous_price(fiat_c, altcoin, yesterday_date)
    price['last_price']['date'] = yesterday_date


def get_crypto_price(*crypto_assets, fiat_coin='usd'):
    params_query = {
     'ids': ','.join(crypto_assets),
     'vs_currencies': fiat_coin
    }
    my_crypto_client = requests.get('https://api.coingecko.com/api/v3/simple/price', params=params_query)
    time_geting_data  = time.asctime()
    dict_response = json.loads(my_crypto_client.text)
    result_data = {}
    result_data['date'] = time_geting_data
    for crypto in crypto_assets:
        result_data[crypto]= dict_response[crypto][fiat_coin] 
    #print (f'Цена на данный момент: {result_data}')
    return result_data 
# template returning: {'date': 'Mon Mar 20 15:40:00 2023', 'bitcoin': 28403, 'ethereum': 1792.24}


# date template: "xx-xx-xxxx"
def get_previous_price(fiat_coin, crypto_asset, date):
    global price
    response = requests.get(f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history', params={'date':date})
    data_price = json.loads(response.text)['market_data']['current_price'][fiat_coin]
    price['last_price'][crypto_asset] = data_price
    

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
    result = (cur_price_accet-last_price_accet)/last_price_accet-(cur_price_btc-last_price_btc)/last_price_btc
    #print (result)
    result_obj['Price movement data'] = round(result, 4)
    #print (result_obj['Price movement data'])
    today_pure_price_mov.append(result_obj)
    return result_obj
#template of response: {'date': 'Mon Mar 20 15:50:05 2023', 'Price movement in one direction': True, 'Price movement data': 0.0074}


def modificated_data_to_next_day ():
    global time_begin, today_pure_price_mov, global_pure_price_mov
    interim_data=0
    for mov_price in today_pure_price_mov:
        interim_data+=mov_price['Price movement data']
    average_pure_price_mov = interim_data/len(today_pure_price_mov)
    global_pure_price_mov[f'{time.gmtime(time_begin).tm_mday}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}:']:round(average_pure_price_mov, 4)

    today_pure_price_mov.clear()
    time_begin = time.time()
    print (f'Время сброса:{time.gmtime(time.time())}')
    return (global_pure_price_mov)

def main_generator (crypto_asset, fiat_c='usd',):
    global price, today_pure_price_mov, global_pure_price_mov    
    time_begin = time.time()
    date_for_prev_price = f"{int(time.gmtime(time_begin).tm_mday)-1}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}"
    set_starting_data (crypto_asset, date_for_prev_price) 
    while True:
        current_pricies = get_crypto_price('bitcoin', crypto_asset)
# template returning: {'date': 'Mon Mar 20 15:40:00 2023', 'bitcoin': 28403, 'ethereum': 1792.24}
        price['actual_price']['bitcoin'], price['actual_price'][crypto_asset], price['actual_price']['date'] = \
                                                                                    current_pricies['bitcoin'],\
                                                                                    current_pricies[crypto_asset],\
                                                                                    current_pricies['date']
        current_move_price_data = get_current_pure_price_mov(price['last_price'][crypto_asset], 
                                                            price['actual_price'][crypto_asset],
                                                            price['last_price']['bitcoin'],
                                                            price['actual_price']['bitcoin'])
#template of response: {'date': 'Mon Mar 20 15:50:05 2023', 'Price movement in one direction': True, 'Price movement data': 0.0074}
        crud_data_for_response = {
            f"Last price of BTC on {price['last_price']['date']}:":price['last_price']['bitcoin'],
            'Actual price of BTC:': price['actual_price']['bitcoin'],
            f"Last price of {crypto_asset} on {price['last_price']['date']}:":price['last_price'][crypto_asset],
            f'Actual price of {crypto_asset}:': price['actual_price'][crypto_asset],
            'Asset price synchronization assets:': current_move_price_data['Price movement in one direction'],
            'Date:': current_move_price_data['date'],
            f'independent movement of an asset {crypto_asset}:': f"{current_move_price_data['Price movement data']*100}%"
        }
        my_response = pandas.Series(crud_data_for_response, crud_data_for_response.keys())
        price['last_price']['bitcoin'], price['last_price'][crypto_asset], price['last_price']['date'] = price['actual_price']['bitcoin'],\
                                                                                                         price['actual_price'][crypto_asset],\
                                                                                                         price['actual_price']['date']
        if time.gmtime(time.time()).tm_mday !=time.gmtime(time_begin).tm_mday:
            print (time.gmtime(time.time()))
            print ('Next day!')
            modificated_data_to_next_day()
            global_data = pandas.Series(global_pure_price_mov, global_pure_price_mov.keys())
            yield (global_data, my_response)
        else:
            yield (my_response)

# data_price_gen = main_generator('ethereum')
# print(next(data_price_gen))
# for i in range (4):
#     time.sleep(60)
#     print (next(data_price_gen))
    






    
    
    


