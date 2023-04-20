import datetime
import time
import pandas


class Responce_template():

        def __init__(self, alt:str, move_list:dict=None, **actual_data):
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
                        'Actual price:': self.actual_alt_price,
                        'Actual price of BTC:':self.actual_btc_price,
                        'Bitcoin price movement:': f"{self.current_move_price_data['Bitcoin price movement']}%",
                        f'{self.crypto_asset} price movement:': f"{self.current_move_price_data['Current altcoin price movement']}%",
                        'Asset price synchronization assets:' :f"{self.current_move_price_data['Price movement in one direction']}",
                        "independent movement of an asse:": f"{self.current_move_price_data['Pure price movement data']}%"
                }
        def create_basic_responce(self):
                result_message = f"<b>{self.crypto_asset}</b>\n<b>Time: </b>{self.actual_time}\n<b>Actual price of {self.crypto_asset}:</b>\
        {self.actual_alt_price}$\n<b>Actual Btc prise:</b> {self.actual_btc_price}$\n<b>Bitcoin price movement:</b>\
                {self.current_move_price_data['Bitcoin price movement']}%\n<b>{self.crypto_asset} price movement:</b> {self.current_move_price_data['Current altcoin price movement']}%\n\
<b>Asset price synchronization assets:</b> {self.current_move_price_data['Price movement in one direction']}\n\
<b>independent movement of {self.crypto_asset}:</b> {self.current_move_price_data['Pure price movement data']}%"
                return result_message
        def create_history_mov_data(self):
                result_list = [
                        f"Актуальное время:{self.actual_time}",
                        f"Общее движение актива с прошедшей точки: {self.current_move_price_data['Current altcoin price movement']}",
                        f"Чистое движение актива: {self.current_move_price_data['Pure price movement data']}"
                ]
                return result_list
        
class SymbolCoinError(Exception):
        def __init__(self, *arg): 
                if arg:
                        self.message = arg[0]
                else:
                        self.message = None
        def __str__(self):
                if self.message != None:
                        return f"{self.message}"
                else:
                        return "Такой монеты нет, возможно вы неправильно указали название."

