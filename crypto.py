
import requests
import json
import time
import sched

price = {
    'last_price': {},
    'actual_price':{}
}
url_file = './data.txt'
today_pure_price_mov = []
global_pure_price_mov = {}
sched_object = sched.scheduler(time.time, time.sleep)

time_begin = time.time()
date_for_prev_price = f"{int(time.gmtime(time_begin).tm_mday)-1}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}"

def initial_data(altcoin, fiat_c, yesterday_date):
    price['last_price']['bitcoin'] = get_previous_price(fiat_c, 'bitcoin', yesterday_date)
    price['last_price'][altcoin] =   get_previous_price(fiat_c, altcoin, yesterday_date)

def modificated_data_to_next_day ():
    global time_begin, today_pure_price_mov, global_pure_price_mov
    interim_data=0
    for mov_price in today_pure_price_mov:
        interim_data+=mov_price['data']
    average_pure_price_mov = interim_data/len(today_pure_price_mov)
    global_pure_price_mov[f'{time.gmtime(time_begin).tm_mday}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}']=round(average_pure_price_mov, 4)
    with open(url_file, 'a') as file:
        file.write(f'{time.gmtime(time_begin).tm_mday}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}:{today_pure_price_mov}')    
    today_pure_price_mov.clear()
    time_begin = time.time()
    print (f'Время сброса:{time.gmtime(time.time())}')


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
    print (f'Цена на данный момент: {result_data}')
    return result_data 
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}



def get_current_pure_price_mov (last_price_accet,
                        cur_price_accet,
                        last_price_btc,
                        cur_price_btc):
    result_obj ={}
    if (cur_price_accet-last_price_accet)*(cur_price_btc-last_price_btc)>0:
        result_obj['Price movement in one direction'] = True
    else:
        result_obj['Price movement in one direction'] = False
    result = (cur_price_accet-last_price_accet)/last_price_accet-(cur_price_btc-last_price_btc)/last_price_btc
    print (f"Движение актива:{(cur_price_accet-last_price_accet)/last_price_accet} Движение битка: {(cur_price_btc-last_price_btc)/last_price_btc}")
    result_obj['data'] = round(result, 4)
    print (f'Цена актива двигается в одну сторону с битком: {result_obj["Price movement in one direction"]},\
            отклонение составляет: {round(result, 4)*100}% \n')
    return result_obj


# date templatr: "xx-xx-xxxx"
def get_previous_price(fiat_coin, crypto_asset, date):
    global price_for_prev_day
    response = requests.get(f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history', params={'date':date})
    data_price = json.loads(response.text)['market_data']['current_price'][fiat_coin]
    price['last_price'][crypto_asset] = data_price
    return data_price


def main(crypto_asset, fiat_c,):
    sched_object.enter(60, 1, main, kwargs={'crypto_asset':'ethereum','fiat_c':'usd' })
    print (time.gmtime(time.time()))
    global price
    current_pricies = get_crypto_price(fiat_c, 'bitcoin', crypto_asset)
    price['actual_price']['bitcoin'], price['actual_price'][crypto_asset] = current_pricies['bitcoin'], current_pricies[crypto_asset]
    #print (f"Last price: asset- {price['last_price'][crypto_asset]} btc -{price['last_price']['bitcoin']} \n")
    today_pure_price_mov.append(get_current_pure_price_mov(price['last_price'][crypto_asset], 
                                                           price['actual_price'][crypto_asset],
                                                           price['last_price']['bitcoin'],
                                                           price['actual_price']['bitcoin']))
    price['last_price']['bitcoin'], price['last_price'][crypto_asset] = price['actual_price']['bitcoin'], price['actual_price'][crypto_asset]
    if time.gmtime(time.time()).tm_mday !=time.gmtime(time_begin).tm_mday:
        print (time.gmtime(time.time()))
        print ('Next day!')
        modificated_data_to_next_day()
    sched_object.run()

if __name__ == '__main__':
    initial_data('ethereum', 'usd', date_for_prev_price)
    main('ethereum', 'usd')
    #sched_object.run()
    


# Пока время не Московское надо изменить.




