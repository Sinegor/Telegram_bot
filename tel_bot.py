import time 
import logging
import os
import dotenv
import sched

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from main_sync_generator import main_generator,get_cur_list
from models import today_pure_price_mov, global_pure_price_mov, price
from messages import START_MESSAGE
load_dotenv()
TOKEN = os.getenv('TOKEN_BOT')
URL_DATA_FILE = os.getenv ('URL_DATA_FILE')
sin_bot = Bot(TOKEN)
sin_disp = Dispatcher(sin_bot)



@sin_disp.message_handler(commands=['start'])
async def start_handler (message: types.Message):
    user_id = message.from_id
    user_name = message.from_user.full_name
    logging.info(f'{time.asctime()}: start work whith user {user_id} {user_name}')
    await message.reply(START_MESSAGE.format(user_name))

@sin_disp.message_handler()
async def st_handler_1 (message: types.Message):
    user_id = message.from_id
    generator_response = '1'
    if message.text not in ['stop', 'Stop', 'stop ']:
        try:
            get_cur_list(message.text)
            data_generator = main_generator(message.text)
            first_reply = next(data_generator)
            await sin_bot.send_message(user_id, first_reply)
        except NameError as e:
            await sin_bot.send_message (user_id, f'NameError: {e}')
    else:
        generator_response = message.text  
        print (f"Если стоп:{generator_response}")
        data_generator.send(generator_response)
    for i in range(20):
        try:
            time.sleep(30)
            print (f"Gen:{generator_response}")
            print(f"Счётчик:{i}")
            gen_responce = data_generator.send(generator_response)
            await sin_bot.send_message(user_id, gen_responce)
        except StopIteration as e:
            await sin_bot.send_message (user_id, f'Вы закончили отслеживать данный актив')
            break





if __name__ == '__main__':
    executor.start_polling(sin_disp)
