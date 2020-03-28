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

def paper_trade(row):
    margin = row['price']-1
    if (abs(row['zscores']) > 3):
            data_writer("##########################")
    global openpos,posentry,postype,net
    if margin > (_FEE_ + _PROFIT_) and not openpos:
        #price above 1 enough,no positions,so enter short
        openpos = True
        posentry = 1+margin
        postype = 'short'
        print('opening short')
        data_writer("opening short")
    elif margin < (0-(_FEE_+_PROFIT_)) and not openpos:
        #price below 1 enough, no positions, so enter long
        openpos = True
        posentry = 1+margin
        postype = 'long'
        print('opening long')
        data_writer("opening long")
    elif margin > (_FEE_ + _PROFIT_) and openpos and postype == 'long':
        #price above 1 enough, in current long, so close position
        openpos = False
        tradeprofit = (1+margin) - posentry - 2*_FEE_
        net += tradeprofit
        print('closing long')
        data_writer("closing long ({} --> {}) with profit {}, total profit: {}".format(posentry, 1+margin, tradeprofit, net))
    elif margin < (0-(_FEE_ + _PROFIT_)) and openpos and postype == 'short':
        #price below 1 enough, in current short, so close position
        openpos = False
        tradeprofit = posentry - (1+margin) - 2*_FEE_
        net += tradeprofit
        print('closing short')
        data_writer("closing short ({} --> {}) with profit {}, total profit: {}".format(posentry, 1+margin, tradeprofit, net))
    else:
        i = 3
    #else: print('not profitable to trade')

def complete_trade_history():
    df = manager.query("SELECT * FROM trade_history WHERE timestamp = (SELECT MAX(timestamp) FROM trade_history);")
    since = df.get('timestamp').iloc[0]
    # since must be in nanoseconds 
    result = c.getHistoricalData("USDTZUSD", since * 100000)
    to_insert = []
    for trade in result:
        to_insert.append((int(str(trade[2]).replace(".","")), int(Decimal(trade[0])*decimal_precision), int(Decimal(trade[1])*decimal_precision), trade[3], trade[4]))
    manager.insert_many_trade_records(to_insert)


def main():
    df = manager.query("SELECT * FROM trade_history")
    df['price'] = df['price'].astype(Decimal)
    df['volume'] = df['volume'].astype(Decimal)
    df['price'] /= decimal_precision
    df['volume'] /= decimal_precision
    prices = df['price']
    df['zscores'] = zscore(prices.astype(float))
    print(df[abs(df['zscores']) > 3])

    for index, row in df.iterrows():
        paper_trade(row)

    #complete_trade_history()
    """to_insert = []
    for d in tether_history_raw:
        t = (int(str(d[2]).replace(".","")), d[0], d[1], d[3], d[4])
        to_insert.append(t)
    
    manager.insert_many_trade_records(to_insert)"""
    """df = manager.query("SELECT * FROM trade_history")
    col = df[['price']].head(1000)
    print(col)
    print(list(col))"""

#    df_zscore = (col - col.mean())/col.std()

    

if __name__ == '__main__':
    main()
