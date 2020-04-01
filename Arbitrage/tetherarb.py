import ARB as c
import time
import csv
import pickle
import matplotlib.pyplot as plt
from decimal import *
from pprint import pprint
from dbmanager import DbManager
from scipy.stats import zscore
import numpy as np
import pandas as pd
from datetime import datetime
import dateutil.parser as dp
import json
import ast

'''
Simple Version:
If no open orders & price is lower than 1-fee-percent_gain, enter long position.
    If open long & price is higher than 1+fee+percent_gain, close position
If no open orders & price is higher than 1+fee+percent_gain, enter short position.
    If open short & price is lower than 1-fee-percent_gain, close position

Complex Version (w pyramiding):
Same as above, but if order(s) already in place, and price hits a further point
away from 1, enter another order. Deosn't have to close at the opposite further
point, but will likely increase profit from strategy.

TODO: make a class for an open position, would make things simpler overall
'''

_FEE_ = 0.0001
_PROFIT_ = 0.0001

decimal_precision = 1000000 # 6

openpos = False
postype = 'long'
posentry = 0
net = 0

manager = DbManager()
manager.connect('kraken.db')

pd.options.display.width = 0

def data_writer(data):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    f = open("tetherdata.txt", "a")
    f.write(current_time + ": "+data+"\n")

def margin_check():
    bid_ask = c.getBidAsk('USDTZUSD')
    bidmargin = bid_ask[0] - 1
    askmargin = bid_ask[2] - 1
    if bid_ask[0] > 1:
        return bidmargin
    elif bid_ask[2] < 1:
        return askmargin
    else: return 0

    global openpos,net,pos,lastbuy,lastsell,lastdate
    if (row['zscores'] > 3):
        data_writer(str(row))
    if (row['buy_or_sell'] == 'b'):
        lastbuy = row['price']
    else:
        lastsell = row['price']

    if (lastbuy is None or lastsell is None):
        return
    stdsize = Decimal(1000)
    if not openpos:
        if lastbuy-1 > (_FEE_ + _PROFIT_):
            #price above 1 enough,no positions,so enter short
            openpos = True
            pos = Position('short',lastbuy,stdsize)
            #print('opening short')
            data_writer("opening short")
        elif lastsell-1 < (0-(_FEE_+_PROFIT_)):
            #price below 1 enough, no positions, so enter long
            openpos = True
            pos = Position('long',lastsell,stdsize)
            #print('opening long')
            data_writer("opening long")
    if openpos:
        if lastbuy-1 > (_FEE_ + _PROFIT_) and pos.type == 'long':
            #price above 1 enough, in current long, so close position
            openpos = False
            pos.close = lastbuy
            data_writer("{} {} {} {} {}".format(row['time'], pos.open, pos.close, capital, net))
            net += (abs(pos.open-pos.close)-(2*_FEE_))*(capital+net)
            #print('closing long')
            data_writer("closing long, total profit: {}".format(net))
        elif lastsell-1 < (0-(_FEE_ + _PROFIT_)) and openpos and pos.type == 'short':
            #price below 1 enough, in current short, so close position
            openpos = False
            pos.close = lastsell
            net += (abs(pos.open-pos.close)-(2*_FEE_))*(capital+net)
            data_writer("{} {} {} {} {}".format(row['time'], pos.open, pos.close, capital, net))

            #print('closing short')
            data_writer("closing short, total profit: {}".format(net))


def read_csv():
    opens = []
    with open('PAXUSDT-1m-data.csv') as f:
        csvread = csv.reader(f, delimiter=',')
        line_count = 0
        for row in csvread:
            if line_count == 0:
                line_count += 1
                pass
            else: opens.append(row[1])
    return opens

def timestamp_as_datetime(timestamp):
    timestamp_length = len(str(timestamp))
    if (timestamp_length < 10):
        print("Timestamp has bad format: {}".format(timestamp))
    return str(datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'))[:-3]

def decimals_to_integers(decimals):
    precision = 0
    for d in decimals:
        significant_digits = -d.as_tuple().exponent
        if (significant_digits > precision):
            precision = significant_digits
    ints = []
    for d in decimals:
        ints.append(int(d*pow(10,precision)))
    return (ints, precision)

def complete_binance_trade_history():
    f = open('binance_PAXUSDT.txt', 'r')
    line = f.readline()
    to_insert = []
    i = 0
    while line:
        d = ast.literal_eval(line)
        timestamp = timestamp_as_datetime(float(str(d['time'])[:-3] + '.' + str(d['time'])[-3:]))
        decimals_as_integers = decimals_to_integers([Decimal(d['price']), Decimal(d['qty'])])
        buy_or_sell = "s" if (d['isBuyerMaker']) else "b"
        to_insert.append((
                "PAX",
                "USDT",
                "BINANCE",
                timestamp,
                decimals_as_integers[0][0],
                decimals_as_integers[0][1],
                decimals_as_integers[1],
                buy_or_sell))
        i += 1
        if (i % 10000 == 0):
            manager.insert_many_trade_records(to_insert)
            print(i)
            to_insert = []
        line = f.readline()

    manager.insert_many_trade_records(to_insert)

def complete_kraken_trade_history():
    df = manager.query("SELECT * FROM TRADE_HISTORY WHERE time = (SELECT MAX(time) FROM TRADE_HISTORY);")
    since = dp.parse(df.get('time').iloc[0]).strftime('%s')
    # since must be in nanoseconds 
    result = c.getHistoricalData("USDTZUSD", since * 1000000000)
    to_insert = []
    for trade in result:
        decimals_as_integers = decimals_to_integers([Decimal(trade[0]), Decimal(trade[1])])
        to_insert.append((
                "USDT",                             # base_currency
                "USD",                              # quote_currency
                "KRAKEN",                           # exchange
                timestamp_as_datetime(trade[2]),    # time
                decimals_as_integers[0][0],         # price
                decimals_as_integers[0][1],         # volume
                decimals_as_integers[1],            # precision
                trade[3]))                          # buy_or_sell
    manager.insert_many_trade_records(to_insert)


def main():

    df = manager.query("SELECT time,price,volume,precision,buy_or_sell FROM TRADE_HISTORY WHERE (base_currency='PAX')")
    df['price'] = df['price'].apply(Decimal)
    df['volume'] = df['volume'].apply(Decimal)
    df['price'] /= pow(10, df['precision'])
    df['volume'] /= pow(10, df['precision'])
    prices = df['price']
    df['zscores'] = zscore(prices.astype(float))
    #print(df.sort_values(by='zscores'))

    print("Starting papertrade")
    print(df)

    
    """
    to_insert = []
    for trade in tether_history_raw:
        decimals_as_integers = decimals_to_integers([Decimal(trade[0]), Decimal(trade[1])])
        to_insert.append((
                "USDT",                             # base_currency
                "USD",                              # quote_currency
                "KRAKEN",                           # exchange
                timestamp_as_datetime(trade[2]),    # time
                decimals_as_integers[0][0],         # price
                decimals_as_integers[0][1],         # volume
                decimals_as_integers[1],            # precision
                trade[3]))                          # buy_or_sell

        to_insert.append((fix_timestamp(trade[2]), int(Decimal(trade[0])*decimal_precision), int(Decimal(trade[1])*decimal_precision), trade[3], trade[4]))

"""
if __name__ == '__main__':
    #data = bin.get_all_binance("PAXUSDT","1m",save = True)
    main()
    print(net)
