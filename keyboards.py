from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
keyb_client = ReplyKeyboardMarkup(resize_keyboard=True)
k_1 = KeyboardButton('/history')
keyb_client.add(k_1)

keyb_client_1 = ReplyKeyboardMarkup(resize_keyboard=True)
k_alt_hist = KeyboardButton('/alt_history')
k_alt_sub = KeyboardButton ('/alt_subscribe')
k_home = KeyboardButton ('/home')
keyb_client_1.add(k_alt_hist).add(k_alt_sub).add(k_home)

keyb_client_2 = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
k_cancel = KeyboardButton('/cancel')
keyb_client_2.add(k_cancel)

keyb_client_3 = ReplyKeyboardMarkup(resize_keyboard=True)
keyb_client_3.add(k_cancel).add(k_alt_hist)


