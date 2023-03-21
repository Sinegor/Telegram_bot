import aiohttp
import json
import time
import sched
import asyncio


price = {
    'last_price': {},
    'actual_price':{}
}
url_file = './data.txt'
today_pure_price_mov = []
global_pure_price_mov = {}
sched_object = sched.scheduler(time.time, time.sleep)
time_begin = time.time()


async def main_handler(alt):
    sched_object.enter(60, 1, main_handler, kwargs={'alt':'ethereum'})
    global today_pure_price_mov, global_pure_price_mov, price
    date_for_prev_price = f"{int(time.gmtime(time_begin).tm_mday)-1}-{time.gmtime(time_begin).tm_mon}-{time.gmtime(time_begin).tm_year}"
    await get_previous_price(alt, date_for_prev_price)
    await get_previous_price('bitcoin', date_for_prev_price)
    current_pricies = await get_crypto_price(alt)
    price['actual_price']['bitcoin'], price['actual_price'][alt] = current_pricies['bitcoin'], current_pricies[alt]
    today_pure_price_mov.append(get_current_pure_price_mov(price['last_price'][alt], 
                                                           price['actual_price'][alt],
                                                           price['last_price']['bitcoin'],
                                                           price['actual_price']['bitcoin']))
    price['last_price']['bitcoin'], price['last_price'][alt] = price['actual_price']['bitcoin'], price['actual_price'][alt]
    if time.gmtime(time.time()).tm_mday !=time.gmtime(time_begin).tm_mday:
        print (time.gmtime(time.time()))
        print ('Next day!')
        modificated_data_to_next_day()
    sched_object.run()



async def get_previous_price(crypto_asset, date, fiat_coin='usd',):
    """
arg date template: "xx-xx-xxxx"

    """
    global data_price
    async with aiohttp.ClientSession() as session:
        my_params = {'date':date}
        async with session.get(f'https://api.coingecko.com/api/v3/coins/{crypto_asset}/history',**{"params":my_params}) as response:
            response_data = await response.text()
            data_price= (json.loads(response_data)['market_data']['current_price'][fiat_coin])
            price['last_price'][crypto_asset] = data_price
            return data_price


async def get_crypto_price(crypto_asset, fiat_coin='usd'):
    async with aiohttp.ClientSession() as session:
        params_query = {
        'ids': f'{crypto_asset},bitcoin',
        'vs_currencies': fiat_coin
        }
        async with session.get('https://api.coingecko.com/api/v3/simple/price', **{'params':params_query}) as response:
            response_data = await response.text()
            data_dict = json.loads(response_data)
            result_data = {
                'bitcoin':data_dict['bitcoin'][fiat_coin],
                crypto_asset: data_dict[crypto_asset][fiat_coin]

            }
            print (f'Цена на данный момент: {result_data}')
            return result_data 
# template returning: {'bitcoin': 24531, 'ethereum': 1673.37}



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

if __name__ == '__main__':
    asyncio.run(main_handler('ethereum'))
    