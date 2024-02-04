import MetaTrader5 as mt5

def format_number(number):
    for num in number:
        if num == ".":
            number = number.replace(num, "")
    else:
        if len(number) < 6:
            number += "0"
            number = int(number)
        elif len(number) > 6:
            number = number[:6]
            number = int(number)
        elif len(number) == 6:
            number = int(number)
            
    return number

def set_period(period):
    if period == "M1":
        timeframe = mt5.TIMEFRAME_M1
    elif period == "M3":
        timeframe = mt5.TIMEFRAME_M3
    elif period == "M5":
        timeframe = mt5.TIMEFRAME_M5
    elif period == "M15":
        timeframe = mt5.TIMEFRAME_M15
    elif period == "M30":
        timeframe = mt5.TIMEFRAME_M30
    elif period == "H1":
        timeframe = mt5.TIMEFRAME_H1
    elif period == "H2":
        timeframe = mt5.TIMEFRAME_H2
    elif period == "H4":
        timeframe = mt5.TIMEFRAME_H4
    elif period == "D1":
        timeframe = mt5.TIMEFRAME_D1

    return timeframe
