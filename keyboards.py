from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
k_1 = KeyboardButton('/history')
keyb_client = ReplyKeyboardMarkup(resize_keyboard=True)
keyb_client.add(k_1)
