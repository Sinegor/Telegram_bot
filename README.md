# Telegram_bot
At the moment, the main functionality of the bot is to compare the price movement of bitcoin and the selected altcoin against the usd (pure price movement altcoin). 
Enter the name of the altcoin you want to know about. The bot returns about pure price coin for last day. You can then request a week’s worth of data on this coin and subscribe to receive information on it at any interval.
User requested information caching in Memory Storage to minimize the number of requests to Coin Geko
Memory Storage currently has four states: 
    - get_btc_historical_data (Got Historical Data on Bitcoin);
    - get_pure_alt_move (Requested daily data on pure price movement coin)
    - request_subscribe (Request sent for tracking of pure price movement coin)
    - subscribing (Ongoing tracking pure price movement coin)

At the moment bot works, but the code requires refactoring