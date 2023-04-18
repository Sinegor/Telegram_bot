import datetime
import time
import pandas


class Responce_template():
        def __init__(self, alt, move_list:dict=None, **actual_data):
                self.crypto_asset = alt,
                self.yeterlay_date = datetime.date.fromtimestamp(time.time()-86400).strftime('%d-%m-%Y'),
                self.actual_btc_price = actual_data['bitcoin'],
                self.actual_alt_price = actual_data[f'{alt}'],
                self.actual_time = actual_data['date'],
                self.current_move_price_data = move_list
        def dict(self):
                return{
                        'Asset:': f"{self.crypto_asset}",
                        "Time:":  self.actual_time,
                        'Actual price': self.actual_alt_price,
                        'Actual price of BTC:':self.actual_btc_price,
                        'Bitcoin price movement:': f"{self.current_move_price_data['Bitcoin price movement']}%",
                        f'{self.crypto_asset} price movement:': f"{self.current_move_price_data['Current altcoin price movement']}",
                        'Asset price synchronization assets:' :f"{self.current_move_price_data['Price movement in one direction']}",
                        "independent movement of an asse:": f"{self.current_move_price_data['Pure price movement data']}"
                }
         


        

