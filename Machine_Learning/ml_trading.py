import machinelearning as ml
import requests
import sys
sys.path.append('/Users/jackconsenstein/Desktop/MoneyMoves/Arbitrage/') # adding ARB
import ARB as order
import pandas as pd
import time
import numpy as np
import csv
import datetime
import itertools, sys #for spinner
#OHLCFT then same from GDAX
# add in percent profit calculator after 58 minute sleep



ML_percent = 0
actual_percent = 0
data = 0
currency = 'XXBTZUSD'
capital = 500
ordervol = 500/order.krakenPrice(currency)
fees = 0

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
    # need to add stop losses to each order case
    if np.abs(percentage) > .5:
        sign = np.sign(percentage)
        if sign == -1:
            price = round(order.krakenPrice(currency),1)
            print(order.trade(order._SELL_,price,ordervol,currency,order._LIMIT_))
            print('sleeping for 58 mins until time to close order...')
            time.sleep(3420)
            print(order.trade(order._BUY_,price,ordervol,currency,order._MARKET_))
            # closing order enters orderbooks 58 minutes after opening order does
            return "Made trade"
        elif sign == 1:
            price = round(order.krakenPrice(currency),1)
            print(order.trade(order._BUY_,price,ordervol,currency,order._LIMIT_))
            print('sleeping for 58 mins until time to close order...')
            time.sleep(3420)
            print(order.trade(order._SELL_,price,ordervol,currency,order._MARKET_))
            # closing order enters orderbooks 58 minutes after opening order does
            return "Made trade"
    else: return "Prediction not confident enough to trade" + str(percentage)

def timer():
    minute = datetime.datetime.now().strftime("%M") #returns minute in numerical formmat (00-59)
    return str(minute)

def get_next_move(hourdata):
    global ML_percent
    ML_percent = ml.next_value('RandomForestRegressor.sav',[hourdata])
    return ML_percent

def data_writer(): #depreciated, doesn't work accurately past 4 or 5 hours
    global actual_percent
    get_next_move(format_data()) #populates ML_percent
    time.sleep(3480) #sleep for 58 minutes
    actual_percent = ((data['close']-data['open'])/data['open'])*100 #gets actual change
    with open('MLpercentages.csv', 'a') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',')
        datawriter.writerow([ML_percent,actual_percent]) #write them side by side
    return

def main():
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    triggered = False
    while True:
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.2)
        sys.stdout.write('\b')
        if timer() == '01' and triggered == False: #if beginning of the hour and no trade
            print("trade triggered")
            print(get_next_move(format_data()))
            print(trade(ML_percent)) #get prediction and trade
            triggered = True
        if timer() == '00': triggered = False

if __name__ == '__main__':
        main()