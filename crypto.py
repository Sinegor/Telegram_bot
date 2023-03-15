
import requests
import json
import time
import sched

price_for_prev_day={}
day_pure_price_mov = {}
previous_pure_price_mov = {}

sched_object = sched.scheduler(time.time, time.sleep)


def get_crypto_price(fiat_coin, *crypto_assets):
    params_query = {
     'ids': ','.join(crypto_assets),
     'vs_currencies': fiat_coin
    }
    my_crypto_client = requests.get('https://api.coingecko.com/api/v3/simple/price', params=params_query)
    dict_response = json.loads(my_crypto_client.text)
    result_data = {}
    for crypto in crypto_assets:
        result_data[crypto]= dict_response[crypto][fiat_coin] 
    return result_data 
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}



def get_current_pure_price_mov (last_price_accet,
                        cur_price_accet,
                        last_price_btc,
                        cur_price_btc):
    return (cur_price_accet-last_price_accet)/last_price_accet-(cur_price_btc-last_price_btc)/last_price_btc

def get_compare_btc(alt, fiat):
    data_price=get_crypto_price(fiat, crypto_assets=('bitcoin',alt))
    pass

# date templatr: "xx-xx-xxxx"
def get_previous_price(fiat_coin, crypto_asset, date):
    response = requests.get(f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history', params={'date':date})
    data_price = json.loads(response.text)['market_data']['current_price'][fiat_coin]
    return data_price




def main(altcoin, fiat_c,):
    time_begin = time.time()
    date_for_prev_price = f"{time.gmtime(time_begin).tm_mday}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}"
    price_for_prev_day['bitcoin'] = get_previous_price(fiat_c, 'bitcoin', date_for_prev_price)
    price_for_prev_day[altcoin] = get_crypto_price(fiat_c, altcoin, date_for_prev_price)


    

def monitoring_pure_price_asset(crypto_asset, period, time_unit):
    sched_object.enter(30, 1, monitoring_pure_price_asset, kwargs={'crypto_asset':'ethereum', })



    







