import machinelearning as ml
import requests
import sys
sys.path.append('/Users/jackconsenstein/Desktop/MoneyMoves/Arbitrage/') # adding ARB
import ARB as order
import pandas as pd
import time
import numpy as np
import csv
#OHLCFT then same from GDAX

ML_percent = 0
actual_percent = 0
data = 0
currency = 'XXBTZUSD'
ordervol = order.krakenPrice(currency)/100
fees = .32

def hourly_price_historical(symbol, comparison_symbol, limit, aggregate, exchange=''):
    url = 'https://min-api.cryptocompare.com/data/histohour?fsym={}&tsym={}&limit={}&aggregate={}'\
            .format(symbol.upper(), comparison_symbol.upper(), limit, aggregate)
    if exchange:
        url += '&e={}'.format(exchange)
    page = requests.get(url)
    data = page.json()['Data']
    return data

def format_data():
    global actual_percent,data
    datasource = hourly_price_historical('BTC','USD',4,0,'Kraken')
    gdatasource = hourly_price_historical('BTC','USD',3,0,'GDAX')
    data = datasource[3]
    datalag1 = datasource[2]
    datalag2 = datasource[1]
    datalag3 = datasource[0]
    gdata = gdatasource[2]
    gdatalag1 = gdatasource[1]
    gdatalag2 = gdatasource[0]
    formatted = [data['open'],data['high'],data['low'],data['volumefrom'],
                 data['volumeto'],gdata['open'],gdata['high'],gdata['low'],
                 gdata['volumefrom'],gdata['volumeto'],datalag1['open'],
                 datalag2['open'],datalag3['open'],datalag1['volumeto'],
                 datalag2['volumeto'],datalag3['volumeto'],gdatalag1['open'],
                 gdatalag2['open']]
    return formatted

def trade(percentage):
    if percentage > fees:
        sign = np.sign(percentage)
        price = order.krakenPrice(currency)
        if sign == -1:
            closeprice = price - (price*percentage)
            order.trade(order._SELL_,price,ordervol,currency,limit)
            order.trade(order._BUY_,closeprice,ordervol,currency,limit)
        elif sign == 1:
            closeprice = price + (price*percentage)
            order.trade(order._BUY_,price,ordervol,currency,limit)
            order.trade(order._SELL_,closeprice,ordervol,currency,limit)
    else: return "What happened?"

def get_next_move(hourdata):
    global ML_percent
    ML_percent = ml.next_value('RandomForestRegressor.sav',[hourdata])
    return ML_percent

def main():
    global actual_percent
    get_next_move(format_data()) #populates ML_percent
    time.sleep(3480) #sleep for 58 minutes
    actual_percent = ((data['close']-data['open'])/data['open'])*100 #gets actual change
    with open('MLpercentages.csv', 'a') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',')
        datawriter.writerow([ML_percent,actual_percent]) #write them side by side
    return

if __name__ == '__main__':
    while True:
        get_next_move(format_data()) #populate ML_percent
        trade(ML_percent)
