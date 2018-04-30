from forex_python.converter import CurrencyRates
import ARB as crypto
import time
import csv
from liquidity import ordersClosed

'''
Explanation of how this bot works:

1: Get usd -> eur and eur -> usd for each coin in the pairlist
2: Highest usd -> eur and highest eur -> usd, use those two coins
3: highest + highest, if that's above fees + arbitrary percentage, then do step 4
4: make round trip trade, collect percentage minus fees.

safe version: only use taker orders, more fees but orders fill instantly
risky version: only use maker orders, less than half fees but orders might not fill
'''

#for forex
c = CurrencyRates()

# currency pairs available in USD and EUR:
# only pairs with enough volume to get fills quickly and not lose too much on the spread
pairlist = [['XXBTZUSD','XXBTZEUR'],
            ['BCHUSD','BCHEUR'],
            ['XETHZUSD','XETHZEUR'],
            ['XXRPZUSD','XXRPZEUR'],
            ['XLTCZUSD','XLTCZEUR'],
            ['XXMRZUSD','XXMRZEUR'],
            ['XZECZUSD','XZECZEUR'],
            ['DASHUSD','DASHEUR']]
#trade IDs:
mainTXID1 = ''
askTXID1 = ''
mainTXID2 = ''
askTXID2 = ''


#trading variables:
coin1 = [] #usd -> eur
percent1 = -100
coin2 = [] # eur -> usd
percent2 = -100

#trading constants, change as needed:
_TRADE_VOLUME_ = 300 # in usd
_CURRENT_FEE_ = .0016
_FEES_ = .64
_PERCENT_GAIN_ = .2
_THRESHOLD_ = 0

def pair_checker(plist): #0 API
    global coin1, percent1, coin2, percent2
    for coin in plist:
        percentages = usd_euro_diff(coin[0],coin[1])
        coinpercentage1 = percentages[0] #usd -> eur
        coinpercentage2 = percentages[1] #eur -> usd
        if coinpercentage1 > percent1:
            coin1 = coin
            percent1 = coinpercentage1
        if coinpercentage2 > percent2:
            coin2 = coin
            percent2 = coinpercentage2
        print(coin[0][:4] + ': ' + str(usd_euro_diff(coin[0],coin[1])))
        #time.sleep(2) #can be changed to 1 if tier 3 account
def best_roundtrip(): #returns best roundtrip trade with fees and percent gain factored in
    global percent1,percent2
    print("Best roundtrip is " + str(percent1+percent2) + " with coins " + str(coin1) + ' and ' + str(coin2))
    return (percent1+percent2)
def make_trade(): #must run pair_checker before this
    global mainTXID1,mainTXID2,askTXID1,askTXID2
    besttrip = best_roundtrip()
    if besttrip > _THRESHOLD_ and ordersClosed(): #use positionsClosed() if using margin
        print("Trading...")
        #crypto.sendMessage('Trade Triggered! Check Kraken...')
        usdorderask1 = crypto.getBidAsk(coin1[0])[1] # step 1 of 2 (going to euros)
        eurorderbid1 = crypto.getBidAsk(coin1[1])[0]
        usdorderbid2 = crypto.getBidAsk(coin2[0])[0] # step 2 of 2 (going back to usd)
        eurorderask2 = crypto.getBidAsk(coin2[1])[1]
        mainTXID1 = crypto.trade(crypto._BUY_,usdorderask1,(_TRADE_VOLUME_/usdorderask1),coin1[0]) #buy with USD
        time.sleep(3) #to make sure trade has closed before selling
        if ordersClosed():
            askTXID1 = crypto.trade(crypto._SELL_,eurorderbid1,(_TRADE_VOLUME_/usdorderask1),coin1[1]) #sell for EUR
        time.sleep(3) #same as above, make sure it's closed and I have EUR
        tx2vol = c.convert('USD','EUR',(_TRADE_VOLUME_+(_TRADE_VOLUME_*_CURRENT_FEE_*2))/eurorderask2)
        if ordersClosed():
            mainTXID2 = crypto.trade(crypto._BUY_,eurorderask2,tx2vol,coin2[1]) #buy with EUR
        time.sleep(3) #make sure trade has closed before selling
        if ordersClosed():
            askTXID2 = crypto.trade(crypto._SELL_,usdorderbid2,tx2vol,coin2[0]) #sell for USD
        print("Round trip completed!")
        print('Profit percentage: ' + str(besttrip))
def usd_euro_diff(usdpair,eurpair): #optimized so its only two api calls
    eurobidask = crypto.getBidAsk(eurpair)
    eurobid = eurobidask[0]
    euroask = eurobidask[1]
    usdbidask = crypto.getBidAsk(usdpair)
    usdbid = usdbidask[0]
    usdask = usdbidask[1]
    lasteuro = (eurobid+euroask)/2
    lastusd = (usdbid+usdask)/2
    usdconvert = c.convert('USD','EUR', lastusd)#usd price converted to euros
    time.sleep(1)
    eurconvert = c.convert('EUR','USD', lasteuro)
    usdtoeurperc = round(((lasteuro-usdconvert)/usdconvert)*100,4)
    eurtousdperc = round(((lastusd-eurconvert)/eurconvert)*100,4)
    return usdtoeurperc,eurtousdperc #returns (usd to euro,euro to usd)
def data_writer(data):
    with open('forexdata.csv', 'a') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',')
        datawriter.writerow(data)
def reset():
    global percent1,percent2,coin1,coin2
    percent1 = -100
    percent2 = -100
    coin1 = []
    coin2 = [] #resets coins and percentages

if __name__ == '__main__':
    while True:
        pair_checker(pairlist)
        data_writer([best_roundtrip(),]) #for data scraping
        #make_trade()
        reset()
        time.sleep(5)
