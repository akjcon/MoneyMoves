import ARB as c
import time
import csv
import pickle
from decimal import Decimal
from pprint import pprint
from pos_class import Position
import numpy
import requests
import bitmex_and_binance as bin
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

_FEE_ = 0.001
_PROFIT_ = 0.001

openpos = False
pos = Position('null',-99,-99)
net = 0
capital = 1000
count = 0

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

def paper_trade(margin):
    global openpos,net,pos
    stdsize = 1000
    if not openpos:
        if margin > (_FEE_ + _PROFIT_):
            #price above 1 enough,no positions,so enter short
            openpos = True
            pos = Position('short',1+margin,stdsize)
            #print('opening short')
            data_writer("opening short")
        elif margin < (0-(_FEE_+_PROFIT_)):
            #price below 1 enough, no positions, so enter long
            openpos = True
            pos = Position('long',1+margin,stdsize)
            #print('opening long')
            data_writer("opening long")
    if openpos:
        if margin > (_FEE_ + _PROFIT_) and pos.type == 'long':
            #price above 1 enough, in current long, so close position
            openpos = False
            pos.close = 1+margin
            net += (abs(pos.open-pos.close)-(2*_FEE_))*(capital+net)
            #print('closing long')
            data_writer("closing long, total profit: {}".format(net))
        elif margin < (0-(_FEE_ + _PROFIT_)) and openpos and pos.type == 'short':
            #price below 1 enough, in current short, so close position
            openpos = False
            pos.close = 1+margin
            net += (abs(pos.open-pos.close)-(2*_FEE_))*(capital+net)
            #print('closing short')
            data_writer("closing short, total profit: {}".format(net))
    else:
        return
    #else: print('not profitable to trade')

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




def main():
    #global _PROFIT_,net
    #tether_history_raw = pickle.load(open('HistoricalData.txt', 'rb'))
    #tether_history = []

    #for d in tether_history_raw:
    #    tether_history.append(1-float(d[0]))

#    arr = numpy.linspace(0.0001,0.001,num=10)
#    for num in arr:
#        _PROFIT_ = num
#        print(_PROFIT_)
    for d in read_csv():
        paper_trade(1-float(d))
    print(net)
if __name__ == '__main__':
    #data = bin.get_all_binance("PAXUSDT","1m",save = True)
    main()
    print(net)
