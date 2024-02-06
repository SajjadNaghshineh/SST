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

symbol = "EURUSD"
timeframe = "M3"
bars = 30000
# bars = 42000
min_rsi = 30
max_rsi = 70
rr = 2
balance = 10000
risk = 0.3

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

def stop_loss_condition(df, symbol):
    last_atr = df.iloc[-1]['atr']
    
    if symbol == "XAUUSD":
        if last_atr < 0.2:
            allowed = False
        else:
            allowed = True
    elif "JPY" in symbol:
        if last_atr < 0.002:
            allowed = False
        else:
            allowed = True
    else:
        if last_atr < 0.0002:
            allowed = False
        else:
            allowed = True
            
    return allowed

def tp_sl_calculation(df, order_type, rr):
    last_candle = df.iloc[-1]
    
    if order_type == "buy":
        tp = last_candle['atr'] * rr + last_candle['close']
        sl = last_candle['close'] - last_candle['atr']
    elif order_type == "sell":
        tp = last_candle['close'] - (last_candle['atr'] * rr)
        sl = last_candle['close'] + last_candle['atr']
        
    return round(tp, 5), round(sl, 5)

def volume_calculation(df, symbol, balance, risk):
    one_percent = int(balance / 100) * risk
    
    last_atr = df.iloc[-1]['atr']
    if 'JPY' in symbol:
        last_atr = last_atr * 1000
    elif symbol == "XAUUSD":
        last_atr = last_atr * 100
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
    
    return order_status, price

print(connection := run_server(info.USERNAME, info.PASSWORD, info.SERVER, info.PATH))
if not connection[0] or not connection[1]:
    print(dt.datetime.now().replace(microsecond=0))
    raise ValueError("Couldn't connect to server")

while True:
    try:
        today = dt.datetime.today()
        current_time = dt.datetime.now().time()
        if today.weekday() not in [5, 6]:
            if current_time >= dt.time(0, 0) and current_time >= dt.time(4, 30):
                connection = run_server(info.USERNAME, info.PASSWORD, info.SERVER, info.PATH)
                if not connection[0] or not connection[1]:
                    print(dt.datetime.now().replace(microsecond=0))
                    raise ValueError("Couldn't connect to server")
                
                df = retrieve_data(symbol, timeframe, bars)
                df = add_indicators(df)
                df = find_positions(df, min_rsi, max_rsi)
                
                if df.iloc[-1]['buy'] == 1:
                    allowed = stop_loss_condition(df, symbol)
                    if allowed:
                        find_time = dt.datetime.now().replace(microsecond=0)
                        print(f"Found a Buy position for {symbol} at {find_time}")
                        
                        tp, sl = tp_sl_calculation(df, 'buy', rr)
                        volume = volume_calculation(df, symbol, balance, risk)
                        order_status, price = place_order(symbol, "buy", tp, sl, volume)
                        
                        if order_status != mt5.TRADE_RETCODE_DONE:
                            error_time = dt.datetime.now().replace(microsecond=0)
                            print(f"Trade operation has an error: {order_status} at {error_time}")
                        else:
                            trade_time = dt.datetime.now().replace(microsecond=0)
                            print(f"Buy for {symbol} at {trade_time}, sl:{sl}, calc entry: {df.iloc[-1]['close']}, real entry: {price}, tp: {tp}")
                elif df.iloc[-1]['sell'] == 1:
                    allowed = stop_loss_condition(df, symbol)
                    if allowed:
                        find_time = dt.datetime.now().replace(microsecond=0)
                        print(f"Found a Sell position for {symbol} at {find_time}")
                        
                        tp, sl = tp_sl_calculation(df, 'sell', rr)
                        volume = volume_calculation(df, symbol, balance, risk)
                        order_status, price = place_order(symbol, "sell", tp, sl, volume)
                        
                        if order_status != mt5.TRADE_RETCODE_DONE:
                            error_time = dt.datetime.now().replace(microsecond=0)
                            print(f"Trade operation has an error: {order_status} at {error_time}")
                        else:
                            trade_time = dt.datetime.now().replace(microsecond=0)
                            print(f"Sell for {symbol} at {trade_time}, sl:{sl}, calc entry: {df.iloc[-1]['close']}, real entry: {price}, tp: {tp}")
        time.sleep(60)
    except Exception as e:
        now = dt.datetime.now().replace(microsecond=0)
        print(f"Error: {e} at {now}")
        break
