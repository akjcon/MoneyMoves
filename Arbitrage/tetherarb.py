import ARB as c
import time
import csv
import pickle
from decimal import Decimal
from pprint import pprint

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

openpos = False
postype = 'long'
posentry = 0
net = 0

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
        tradeprofit = (1+margin) - posentry
        net += tradeprofit
        print('closing long')
        data_writer("closing long, total profit: {}".format(net))
    elif margin < (0-(_FEE_ + _PROFIT_)) and openpos and postype == 'short':
        #price below 1 enough, in current short, so close position
        openpos = False
        tradeprofit = posentry - (1+margin)
        net += tradeprofit
        print('closing short')
        data_writer("closing short, total profit: {}".format(net))
    else:
        i = 3
    #else: print('not profitable to trade')

def main():
    tether_history_raw = pickle.load(open('HistoricalData.txt', 'rb'))
    tether_history = []

    for d in tether_history_raw:
        tether_history.append(1-Decimal(d[0]))
    
    for d in tether_history:
        paper_trade(d)

if __name__ == '__main__':
    main()
