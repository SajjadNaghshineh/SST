import os
os.system("cls")
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import datetime as dt
from utils import set_period
import info

symbol = "GBPUSD"
timeframe = "M1"
bars = 30000
# bars = 42000
min_rsi = 15
max_rsi = 85
rr = 2

def run_server(username, password, server, path):
    first_connection = mt5.initialize(
        path=path,
        login=username,
        password=password,
        server=server
    )

    second_connection = mt5.login(
        login=username,
        password=password,
        server=server
    )
    
    return first_connection, second_connection

def retrieve_data(symbol, timeframe, bars):
    time_frame = set_period(timeframe)
    candles = mt5.copy_rates_from_pos(symbol, time_frame, 1, bars)[["time", "open", "high", "low", "close", "tick_volume"]]
    df = pd.DataFrame(candles)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index("time", inplace=True)
    df = df.rename(columns={"tick_volume": "volume"})
    
    return df

def add_indicators(df):
    df['rsi'] = ta.rsi(df['close'])
    df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    df['atr'] = ta.atr(df['high'], df['low'], df['close'])
    adx = ta.adx(df['high'], df['low'], df['close'])
    df = pd.concat([df, adx['ADX_14'], adx['DMP_14'], adx['DMN_14']], axis=1)
    
    df.reset_index(inplace=True)
    
    return df

def find_positions(df, min_rsi, max_rsi):
    df['buy'] = np.where((df['rsi'] < min_rsi) & (df['close'] > df['vwap']) & (df["ADX_14"] > 25), 1, 0)
    df['sell'] = np.where((df['rsi'] > max_rsi) & (df['close'] < df['vwap']) & (df["ADX_14"] > 25), 1, 0)
    
    return df

def tp_sl_calculation(df, order_type, rr):
    last_candle = df.iloc[-1]
    
    if order_type == "buy":
        tp = last_candle['atr'] * rr + last_candle['close']
        sl = last_candle['close'] - last_candle['atr']
    elif order_type == "sell":
        tp = last_candle['close'] - (last_candle['atr'] * rr)
        sl = last_candle['close'] + last_candle['atr']
        
    return round(tp, 5), round(sl, 5)

def volume_calculation(df, symbol):
    user_info = mt5.account_info()
    balance = user_info[10]
    one_percent = int(balance / 100) * 0.2
    
    last_atr = df.iloc[-1]['atr']
    if 'JPY' in symbol:
        last_atr = last_atr * 1000
    else:
        last_atr = last_atr * 10000
        
    lot_size = one_percent / last_atr
    lot_size = lot_size / 10
    
    return round(lot_size, 2)

def place_order(symbol, order_type, tp, sl, volume):
    price = mt5.symbol_info_tick(symbol).ask
    
    if order_type == "sell":
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    elif order_type == "buy":
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": sl,
            "tp": tp,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
    result = mt5.order_send(request)
    order_status = result.retcode
    
    return order_status

print(connection := run_server(info.USERNAME, info.PASSWORD, info.SERVER, info.PATH))
if not connection[0] or not connection[1]:
    print(dt.datetime.now().replace(microsecond=0))
    raise ValueError("Couldn't connect to server")

while True:
    try:
        today = dt.datetime.today()
        if today.weekday() not in [5, 6]:
            df = retrieve_data(symbol, timeframe, bars)
            df = add_indicators(df)
            df = find_positions(df, min_rsi, max_rsi)
            
            if df.iloc[-1]['buy'] == 1:
                find_time = dt.datetime.now().replace(microsecond=0)
                print(f"Found a Buy position for {symbol} at {find_time}")
                
                tp, sl = tp_sl_calculation(df, 'buy', rr)
                volume = volume_calculation(df, symbol)
                order_status = place_order(symbol, "buy", tp, sl, volume)
                
                if order_status != mt5.TRADE_RETCODE_DONE:
                    error_time = dt.datetime.now().replace(microsecond=0)
                    print(f"Trade operation has an error: {order_status} at {error_time}")
                else:
                    trade_time = dt.datetime.now().replace(microsecond=0)
                    print(f"Buy for {symbol} at {trade_time}.")
            elif df.iloc[-1]['sell'] == 1:
                find_time = dt.datetime.now().replace(microsecond=0)
                print(f"Found a Sell position for {symbol} at {find_time}")
                
                tp, sl = tp_sl_calculation(df, 'sell', rr)
                volume = volume_calculation(df, symbol)
                order_status = place_order(symbol, "sell", tp, sl, volume)
                
                if order_status != mt5.TRADE_RETCODE_DONE:
                    error_time = dt.datetime.now().replace(microsecond=0)
                    print(f"Trade operation has an error: {order_status} at {error_time}")
                else:
                    trade_time = dt.datetime.now().replace(microsecond=0)
                    print(f"Sell for {symbol} at {trade_time}.")
        time.sleep(60)
    except Exception as e:
        now = dt.datetime.now().replace(microsecond=0)
        print(f"Error: {e} at {now}")
        