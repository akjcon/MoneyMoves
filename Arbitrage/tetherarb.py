import ARB as c
import time
import csv
import pickle
import matplotlib.pyplot as plt
from decimal import *
from pprint import pprint
from pos_class import Position
import requests
from dbmanager import DbManager
from scipy.stats import zscore
import numpy as np
import pandas as pd
from datetime import datetime
import ast
from tqdm import tqdm

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

_FEE_ = Decimal(0.001)
_PROFIT_ = Decimal(0.001)

decimal_precision = 1000000 # 6

openpos = False
pos = Position('null',-99,-99)
net = Decimal(0)
capital = Decimal(1000)
count = 0

lastdate = None

lastbuy = None
lastsell = None

manager = DbManager()
manager.connect('kraken.db')

pd.options.display.width = 0

def data_writer(data):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    f = open("tetherdata.txt", "a")
    f.write(data+"\n")

def margin_check():
    bid_ask = c.getBidAsk('USDTZUSD')
    bidmargin = bid_ask[0] - 1
    askmargin = bid_ask[2] - 1
    if bid_ask[0] > 1:
        return bidmargin
    elif bid_ask[2] < 1:
        return askmargin
    else: return 0

def paper_trade(row):
    global openpos,net,pos,lastbuy,lastsell,lastdate

    if (row['isBuyerMaker'] == False):
        lastbuy = Decimal(row['price'])
    else:
        lastsell = Decimal(row['price'])

    if (lastbuy is None or lastsell is None):
        return
    stdsize = Decimal(1000)
    #time = datetime.utcfromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
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

def fix_timestamp(timestamp):
    timestamp = str(timestamp).replace(".","")
    for i in range(0, 14-len(timestamp)):
        timestamp += "0"
    return int(timestamp)

def complete_trade_history():
    df = manager.query("SELECT * FROM trade_history WHERE timestamp = (SELECT MAX(timestamp) FROM trade_history);")
    since = df.get('timestamp').iloc[0]
    # since must be in nanoseconds
    result = c.getHistoricalData("USDTZUSD", since * 100000)
    to_insert = []
    for trade in result:
        to_insert.append((fix_timestamp(trade[2]), int(Decimal(trade[0])*decimal_precision), int(Decimal(trade[1])*decimal_precision), trade[3], trade[4]))
    manager.insert_many_trade_records(to_insert)


def main():
    df = manager.query("SELECT * FROM trade_history")
    df['price'] = df['price'].apply(Decimal)
    df['volume'] = df['volume'].apply(Decimal)
    df['price'] /= decimal_precision
    df['volume'] /= decimal_precision
    prices = df['price']
    df['zscores'] = zscore(prices.astype(float))
    #print(df[abs(df['zscores']) > 3])

    print("Starting papertrade")

    lastlen = 0
    tether_history_raw = pickle.load(open('HistoricalData.txt', 'rb'))
    for index, row in df.iterrows():
        paper_trade(row)

    #complete_trade_history()
    """tether_history_raw = pickle.load(open('HistoricalData.txt', 'rb'))
    to_insert = []
    for trade in tether_history_raw:
        to_insert.append((fix_timestamp(trade[2]), int(Decimal(trade[0])*decimal_precision), int(Decimal(trade[1])*decimal_precision), trade[3], trade[4]))


    manager.insert_many_trade_records(to_insert)"""
    """
    df = manager.query("SELECT * FROM trade_history")
    col = df[['price']].head(1000)
    print(col)
    print(list(col))"""

#    df_zscore = (col - col.mean())/col.std()
    #for d in read_csv():
    #    paper_trade(1-float(d))
    #print(net)

def main1():
    with open('binance_PAXUSDT.txt','r') as f:
        for line in tqdm(f,total=3958000):
            nextline = next(f)[:-1]
            paper_trade(ast.literal_eval(nextline))

if __name__ == '__main__':
    #data = bin.get_all_binance("PAXUSDT","1m",save = True)
    main1()
    print(net)
