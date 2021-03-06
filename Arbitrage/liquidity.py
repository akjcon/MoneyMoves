import ARB as crypto
import time
from forex_python.converter import CurrencyRates

'''
How this bot works:
When it sees that the Bid/Ask spread is greater than a specified percentage, say .5%, it closes the spread by
a set percentage (var spreadclose). People want to sell at a higher price and buy at a lower price, so this works
in theory. Problems with liquidity arise though. Also, sometimes spread will move away from wherever orders were placed
and leave one order unfilled, ending in a losing trade. A way to fix this would be to figure out if the price is moving up
or down right before the trade happens, but this is imprecise. Better to know where the price will be in the next minute,
hence the Machine Learning side of all of this.
'''

#for forex
c = CurrencyRates()

currency = "XETHZEUR"
ordervol = .1
mainTXID = '' #calling it mainTXID for now to make ordersClosed() work
askTXID = ''
orderbid = 0
orderask = 0
tradethreshold = .2  #percent spread to trigger trades
cumulprofit = 0  #profit counter (doesn't include rebalance but that should be negligible)
spreadclose = .00018  #percent to close the spread by
stoplosspercent = .005  #percent above/below orders to trigger stop loss
price1 = 0
movedirection = ''
moveamount = 0
tradedirection = ''
tradeclosed = True
tradeongoing = False

# BUG: right now i'm using if statements to crudely predict price movements in the next few seconds
#I need to create a basic neural net that's passed previous prices and gives likely next price movement

# BUG: getBidAsk needs to be updated so you can pass it a volume requirement //low priority//

import numpy as np

def spreadPercent(ticker): #API call count: 0
    global price1,movedirection,moveamount
    bidask = crypto.getBidAsk(ticker)
    bid = bidask[0]
    ask = bidask[1]
    moveamount = ((bid+ask)/2) - price1
    if price1 > ((bid+ask)/2):
        movedirection = 'neg'
    if price1 < ((bid+ask)/2):
        movedirection = 'pos'
    if abs(moveamount) < .1:
        movedirection = 'flat'
    price1 = (bid+ask)/2
    return ((ask - bid)/bid*100)

def tradeTrigger(ticker,spread): #API call count: 1
    global tradeclosed
    tradeclosed = ordersClosed()
    if spread > tradethreshold and tradeclosed:
        print("Triggered")
        return makeTrades(ticker)

def profitCalc(bid,ask): #API call count: 0
    if ask != 0 and bid != 0:
        return (ask-bid)*ordervol

def ordersClosed(): #API call count: 1
    while True:
        try:
            opens = crypto.k.query_private(crypto._OPEN_ORDERS_)
            if crypto._RESULT_ in opens:
                return len(opens[crypto._RESULT_][crypto._OPEN_]) == 0
            elif crypto._RATE_LIMIT_ERROR_ in opens[crypto._ERROR_]:
                print("Rate Limit Hit. Waiting for 17 Minutes to Reset...")
                time.sleep(1000)
            else: return opens
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")

def makeTrades(ticker): #API call count: 0, if triggered and cancelled 1
    global orderbid, orderask, mainTXID, askTXID, cumulprofit,tradeongoing
    bidask = crypto.getBidAsk(ticker)
    bid = bidask[0]
    ask = bidask[1]
    orderbid = round((bid + bid*spreadclose),2)
    orderask = round((ask - ask*spreadclose),2)
    print("Making Trades..")
    print("Best Bid: " + str(bid) + " Order Bid: " + str(orderbid))
    print("Best Ask: " + str(ask) + " Order Ask: " + str(orderask))
    if (((orderask-orderbid)/orderbid)*100) < .12: #ensures trade will have profit
        print("Missed Trade :(")
        return
    if movedirection == 'pos':
        mainTXID = crypto.trade(crypto._BUY_,orderbid,ordervol,currency)
        print(mainTXID)
        time.sleep(10)
        if ordersClosed():
            askTXID = crypto.trade(crypto._SELL_,orderask,ordervol,currency)
            print(askTXID)
            tradeongoing = True
            cumulprofit += profitCalc(orderbid,orderask)
        else: crypto.cancelOrder(mainTXID)
    elif movedirection == 'neg':
        askTXID = crypto.trade(crypto._SELL_,orderask,ordervol,currency)
        print(askTXID)
        time.sleep(10)
        if ordersClosed():
            mainTXID = crypto.trade(crypto._BUY_,orderbid,ordervol,currency)
            print(mainTXID)
            tradeongoing = True
            cumulprofit += profitCalc(orderbid,orderask)
        else: crypto.cancelOrder(askTXID)
    elif movedirection == 'flat':
        mainTXID = crypto.trade(crypto._BUY_,orderbid,ordervol,currency)
        askTXID = crypto.trade(crypto._SELL_,orderask,ordervol,currency)
    #crypto.sendMessage("")

def checkStatus(): # not used right now
    bid = crypto.getBid(currency)
    ask = crypto.getAsk(currency)
    print("Order Status:")
    if orderbid != 0:
        print('current bid '+ str(bid)+ ' orderbid ' + str(orderbid))
        if bid > orderbid:
            print(mainTXID)
            return(crypto.cancelOrder(mainTXID))
    if orderask != 0:
        print('current ask '+ str(ask)+ ' orderask ' + str(orderask))
        if ask < orderask:
            print(askTXID)
            return(crypto.cancelOrder(askTXID))

def balancer(): #API call count: 0
    bal = crypto.getCurrBalance()
    eth = float(bal["XETH"])
    eur = float(bal["ZEUR"])
    ethbalancevol = (ordervol - eth)
    if eth < (ordervol+.001) and ethbalancevol > .02 and ordersClosed():
        print("Rebalancing...")
        crypto.trade(crypto._BUY_,round(crypto.getBidAsk(currency)[1],2),ethbalancevol+.02,currency)
        time.sleep(10)
    elif eur < 100 and ordersClosed():
        print("Rebalancing...")
        crypto.trade(crypto._SELL_,round(crypto.getBidAsk(currency)[0],2),(eth-.25),currency)
        time.sleep(10)

def stopLoss(): #API call count: 0
    global cumulprofit
    if not tradeclosed:
        bidask = crypto.getBidAsk(currency)
        if orderbid != 0 and bidask[0] > orderbid+(orderbid*stoplosspercent):
            print("Stop Loss Triggered at " + str(bidask[0]))
            cumulprofit = cumulprofit - Calc(orderbid,orderask)
            crypto.cancelOrder(mainTXID)
            crpyto.cancelOrder(askTXID) #added for the case of movedirection == 'flat'
        if orderask != 0 and bidask[1] < orderask-(orderask*stoplosspercent):
            print("Stop Loss Triggered at " + str(bidask[1]))
            cumulprofit = cumulprofit - Calc(orderbid,orderask)
            crypto.cancelOrder(askTXID)
            crypto.cancelOrder(mainTXID) #added for the case of movedirection == 'flat'

if __name__ == '__main__':
    while True:
        print("Move Direction: " + movedirection + " by " + str(moveamount))
        balancer()
        print("Previous Orders Closed: " + str(tradeclosed))
        percent = spreadPercent(currency)
        print("Bid/Ask Spread Percentage: " + str(percent))
        print("Accumulated Profit This Iteration: $" + str(round(cumulprofit,5)))
        tradeTrigger(currency,percent)
        stopLoss()
        time.sleep(6)
