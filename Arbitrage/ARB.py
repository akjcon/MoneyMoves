import krakenex #pip install krakenex
import time
import socket
from datetime import datetime
#import gdax #pip install gdax
from twilio.rest import Client #pip install twilio
#from bitfinex.client import Client as bfxClient
import requests

'''
This used to be a program that would trade the time delay between Kraken and GDAX/Bitfinex
but that difference is now gone so it's just used as an interface for other trading programs to
take methods from
'''

#known issues:
# - none as of now
# TODO: print PNL after position is closed

#for twilio
client = Client("AC7ce4b6445b3aa408e94c7b78a4099b2d","98552e5ecbb877566e98cd3efbe2ff10")

#for Kraken
k = krakenex.API() #private methods
#k.load_key('kraken.key')
kpublic = krakenex.API() # public methods


# transaction IDs/info for closing extra trades:
mainTXID = ''
closeTXID = ''
stoplossTXID = ''
main = ''
trade = ''
closedirection = ''
inPosition = False

# Api Key Strings:
_RATE_LIMIT_ERROR_ = 'EAPI:Rate limit exceeded'
_K_CURR_ = 'XETHXXBT'
_G_CURR_ = 'ETH-USD'
_ADD_ORDER_ = 'AddOrder'
_PAIR_ = 'pair'
_TYPE_ = 'type'
_ETH_CURRENCY_ = 'ETHUSD'
_LEVERAGE_ = 'leverage'
_BUY_ = 'buy'
_SELL_ = 'sell'
_LIMIT_ = 'limit'
_STOP_LOSS_ = 'stop-loss'
_ORDER_TYPE_ = 'ordertype'
_PRICE_ = 'price'
_PRICE_2_ = 'price2'
_VOLUME_ = 'volume'
_EXPIRETM_ = 'expiretm'
_RESULT_ = 'result'
_TXID_ = 'txid'
_CANCEL_ORDER_ = 'CancelOrder'
_DEPTH_ = 'Depth'
_COUNT_ = 'count'
_BIDS_ = 'bids'
_ASKS_ = 'asks'
_OPEN_POSITIONS_ = 'OpenPositions'
_QUERY_ORDERS_ = 'QueryOrders'
_STATUS_ = 'status'
_CLOSED_ = 'closed'
_CANCELLED_ = 'canceled' #stupid Kraken doesnt know how to spell...
_TYPE_ = 'type'
_ALL_ = 'all'
_TRADES_ = 'Trades'
_OPEN_ = 'open'
_ERROR_ = 'error'
_OPEN_ORDERS_ = 'OpenOrders'
_CLOSED_ORDERS_ = 'ClosedOrders'
_MARKET_ = 'market'
_SINCE_ = 'since'
_LAST_ = 'last'

# API Values
_LEVERAGE_VALUE_ = 5
_COUNT_VALUE_ = '20'
_LIMIT_PRICE_DIFF_ = 0.5
_POS_STOP_LOSS_PRICE_DIFF_ = 3
_NEG_STOP_LOSS_PRICE_DIFF_ = -3

# constant variables for price checking and trading:
availablecapital = 100
posTradePriceGap = 4
negTradePriceGap = -4
posPercent = .1
negPercent = -.1
loopnum = 0
stoplossTime = 200



def orderFillCheck():
    #returns true if main order has filled, false if not
    while True:
        try:
            mainorder = k.query_private(_QUERY_ORDERS_, {_TXID_: mainTXID})
            if _RESULT_ in mainorder:
                mTXID = mainorder[_RESULT_][mainTXID]
                print("order fill check: ")
                print(mTXID)
                if 'partial' in mTXID['misc']: return True
                if _CLOSED_ in mTXID[_STATUS_]: return True
            if _RESULT_ not in (mainorder): # error is returned usually
                print(mainorder)
                continue
            else: return False
        except socket.timeout:
            print('[orderFillCheck] socket timeout')
        except ValueError:
            print('[orderFillCheck] JSON error')

def stopLoss():
    #requires getMain() to have been run first
    global stoplosscount
    if main and (stoplosscount == 0) and not positionsClosed():
        direction = main['descr'][_TYPE_]
        if direction == 'buy':
            if (krakenEthPrice() - float(main['price'])) < _NEG_STOP_LOSS_PRICE_DIFF_:
                print("Stop loss triggered")
                sendMessage('Stop loss triggered')
                cancelOrder(closeTXID)
                closeMain()
                stoplosscount = 1
                print(stoplosscount)
        elif direction == 'sell':
            if (krakenEthPrice() - float(main['price'])) > _POS_STOP_LOSS_PRICE_DIFF_:
                print("Stop loss triggered")
                sendMessage('Stop loss triggered')
                cancelOrder(closeTXID)
                closeMain()
                stoplosscount = 1
                print(stoplosscount)
        else:
            print("not buy or sell? what..?")

def getMain():
    global main
    while True:
        try:
            mainquery = k.query_private(_CLOSED_ORDERS_)
            if _RESULT_ in mainquery:
                main = mainquery[_RESULT_][_CLOSED_][mainTXID]
                print(main)
                break
            else:
                print(mainquery)
                continue
        except ValueError:
            print('[getMain] JSON Error')
            continue
        except socket.timeout:
            print('[getMain] Timeout Error')
            continue

def closeMain():
    volume = main['vol']
    direction = main['descr'][_TYPE_]
    closedirection = ''
    if direction == 'buy':
        closedirection = 'sell'
    else: closedirection = 'buy'
    while True:
        try:
            closingmain = k.query_private(_ADD_ORDER_, {
                                          _PAIR_: _ETH_CURRENCY_,
                                          _TYPE_: closedirection,
                                          _ORDER_TYPE_: _MARKET_,
                                          _VOLUME_: volume,
                                          _LEVERAGE_: _LEVERAGE_VALUE_,
                                         # 'validate': 'True'
                                          })
            print('Closing main:')
            print(closingmain)
            break
        except ValueError:
            print('[closePositionTimer] JSON Error')
            continue
        except socket.timeout:
            print('[closePositionTimer] Timeout Error')
            continue

def getCurrBalance():
    while True:
        try:
            balance = k.query_private('Balance')
            if _RESULT_ not in balance:
                print(balance)
                continue
            else: return balance[_RESULT_] #returns list for minimizing API calls
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")

def lastOrderTXID():
    while True:
        try:
            openorders = k.query_private(_OPEN_ORDERS_)
            if _RESULT_ not in openorders:
                print(openorders)
                continue
            if openorders[_RESULT_][_OPEN_]:
                print(openorders)
                return next(iter(openorders[_RESULT_][_OPEN_]))
            else: continue
        except socket.timeout:
            print('[lastOrderTXID] Socket Timeout on getting TXID')
        except ValueError:
            print('[lastOrderTXID] JSON error on getting TXID')

def sendMessage(messagebody):
    return client.messages.create(to='+19079030789',
                           from_='+17042702244',
                           body=messagebody)

def krakenEthPrice():
    while True:
        try:
            firstPrice_Kraken = k.query_public(_DEPTH_, {_PAIR_:_K_CURR_,_COUNT_:_COUNT_VALUE_})
            if _RESULT_ not in firstPrice_Kraken:
                print(firstPrice_Kraken)
                continue
            else: break
        except ValueError:
            print('[krakenEthPrice] JSON error in price, retrying...')
        except socket.timeout:
            print('[krakenEthPrice] Timeout error in price, retrying...')
        except ConnectionResetError:
            print('[krakenEthPrice] Connection Reset Error')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    #get ask and bid, average and return number
    bestbid = float(firstPrice_Kraken[_RESULT_][_K_CURR_][_BIDS_][0][0])
    bestask = float(firstPrice_Kraken[_RESULT_][_K_CURR_][_ASKS_][0][0])
    return (bestask+bestbid)/2

def getHistoricalData(currency):
    since = 1546300800000000000 # 1/1/2019
    all_trades = []
    wait = 10
    while True:
        try:
            data = kpublic.query_public(_TRADES_, {_PAIR_:currency,_SINCE_:since})
            if (_RESULT_ not in data):
                print(data)
                time.sleep(wait)
                wait += 1
            elif (currency not in data[_RESULT_] or len(data[_RESULT_][currency]) == 0):
                return all_trades
            else:
                new_since = int(data[_RESULT_][_LAST_])
                new_trades = data[_RESULT_][currency]
                all_trades.extend(data[_RESULT_][currency])
                print(len(all_trades))
            since = new_since
            print(since)
            print(datetime.utcfromtimestamp(int(str(since)[0:10])).strftime('%Y-%m-%d %H:%M:%S'))
            time.sleep(5)
        except:
            time.sleep(20)
    return all_trades

def hourly_price_historical(symbol, comparison_symbol, limit, exchange):
    url = 'https://min-api.cryptocompare.com/data/v2/histohour?fsym={}&tsym={}&limit={}&e={}'\
            .format(symbol.upper(), comparison_symbol.upper(), limit, exchange)
    page = requests.get(url)
    data = page.json()['Data']
    return data

def krakenPrice(currency):
    while True:
        try:
            firstPrice_Kraken = kpublic.query_public(_DEPTH_, {_PAIR_:currency,_COUNT_:_COUNT_VALUE_})
            if _RESULT_ not in firstPrice_Kraken:
                print(firstPrice_Kraken)
                continue
            else: break
        except ValueError:
            print('[krakenPrice] JSON error in price, retrying...')
        except socket.timeout:
            print('[krakenPrice] Timeout error in price, retrying...')
        except ConnectionResetError:
            print('[krakenPrice] Connection Reset Error')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    #get ask and bid, average and return number
    bestbid = float(firstPrice_Kraken[_RESULT_][currency][_BIDS_][0][0])
    bestask = float(firstPrice_Kraken[_RESULT_][currency][_ASKS_][0][0])
    return (bestask+bestbid)/2

def krakenBTCPrice():
    while True:
        try:
            firstPrice_Kraken = k.query_public(_DEPTH_, {_PAIR_:"XXBTZUSD",_COUNT_:_COUNT_VALUE_})
            if _RESULT_ not in firstPrice_Kraken:
                print(firstPrice_Kraken)
                continue
            else: break
        except ValueError:
            print('[krakenBTCPrice] JSON error in price, retrying...')
        except socket.timeout:
            print('[krakenBTCPrice] Timeout error in price, retrying...')
        except ConnectionResetError:
            print('[krakenBTCPrice] Connection Reset Error')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    #get ask and bid, average and return number
    bestbid = float(firstPrice_Kraken[_RESULT_]["XXBTZUSD"][_BIDS_][0][0])
    bestask = float(firstPrice_Kraken[_RESULT_]["XXBTZUSD"][_ASKS_][0][0])
    return (bestask+bestbid)/2

def krakencalcprice():
    btc = krakenBTCPrice()
    eth = krakenEthPrice()
    return eth/btc

def getBidAsk(ticker): #returns 4 values: (bid,bidvol,ask,askvol)
    while True:
        try:
            firstPrice_Kraken = kpublic.query_public(_DEPTH_, {_PAIR_:ticker,_COUNT_:_COUNT_VALUE_})
            if _RESULT_ not in firstPrice_Kraken:
                print(firstPrice_Kraken)
                continue
            else: break
        except ValueError:
            print('[krakenBTCPrice] JSON error in price, retrying...')
        except socket.timeout:
            print('[krakenBTCPrice] Timeout error in price, retrying...')
        except ConnectionResetError:
            print('[krakenBTCPrice] Connection Reset Error')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    bestbid = float(firstPrice_Kraken[_RESULT_][ticker][_BIDS_][0][0])
    bidvol = float(firstPrice_Kraken[_RESULT_][ticker][_BIDS_][0][1])
    bestask = float(firstPrice_Kraken[_RESULT_][ticker][_ASKS_][0][0])
    askvol = float(firstPrice_Kraken[_RESULT_][ticker][_ASKS_][0][1])
    return bestbid,bidvol,bestask,askvol

def krakenBTCETHPrice():
    while True:
        try:
            firstPrice_Kraken = k.query_public(_DEPTH_, {_PAIR_:"XETHXXBT",_COUNT_:_COUNT_VALUE_})
            if _RESULT_ not in firstPrice_Kraken:
                print(firstPrice_Kraken)
                continue
            else: break
        except ValueError:
            print('[krakenBTCPrice] JSON error in price, retrying...')
        except socket.timeout:
            print('[krakenBTCPrice] Timeout error in price, retrying...')
        except ConnectionResetError:
            print('[krakenBTCPrice] Connection Reset Error')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    #get ask and bid, average and return number
    bestbid = float(firstPrice_Kraken[_RESULT_]["XETHXXBT"][_BIDS_][0][0])
    bestask = float(firstPrice_Kraken[_RESULT_]["XETHXXBT"][_ASKS_][0][0])
    return (bestask+bestbid)/2

def BTCETHpercent():
    btc = krakenBTCPrice()
    eth = krakenEthPrice()
    btceth = eth/btc
    kbtceth = krakenBTCETHPrice()
    return (btceth - kbtceth)/kbtceth*100

def positionsClosed():
    if not mainTXID: #if mainTXID is empty
        return True
    else:
        while True:
            try:
                opens = k.query_private(_OPEN_POSITIONS_)
                print("Open Positions:")
                print(opens)
                if _RESULT_ in opens:
                    return len(opens[_RESULT_]) == 0
            except socket.timeout:
                print('[positionsClosed] Timeout Error. Retrying.')
            except ValueError:
                print('[positionsClosed] JSON Error. Retrying.')

def ordersClosed():
    global inPosition
    if not mainTXID: #if mainTXID is empty
        return True
    else:
        while True:
            try:
                opens = k.query_private(_OPEN_ORDERS_)
                if _RESULT_ in opens:
                    print(opens[_RESULT_])
                    status = len(opens[_RESULT_][_OPEN_]) == 0
                    if status == True:
                        inPosition = False
                    return status
            except socket.timeout:
                print('[positionsClosed] Timeout Error. Retrying.')
            except ValueError:
                print('[positionsClosed] JSON Error. Retrying.')

def trade(direction,price,volume,ticker,ordertype):
    # should return the TXID of the trade
    while True:
        try:
            trade = k.query_private(_ADD_ORDER_,{
                _PAIR_: ticker,
                _TYPE_: direction,
                _ORDER_TYPE_: ordertype,
                _PRICE_: price,
                _VOLUME_: volume,
                _LEVERAGE_: _LEVERAGE_VALUE_,
                'validate': 'True',

            })
            if _RESULT_ not in trade:
                if trade[_ERROR_] == 'EOrder:Insufficient funds':
                    break
                print(trade)
                break
            else:
                #sendMessage('Trade order with ID' + trade[_RESULT_][_TXID_][0] + 'sent. Check Kraken. ')
                return trade[_RESULT_][_TXID_][0]
        except socket.timeout:
            print('[trade] Order Timeout. Check TXIDs')
            #sendMessage("Order probably didn't go but you should check")
            lastorder = lastOrderTXID()
            if lastorder != mainTXID:
                return lastorder
            else: continue
        except ValueError:
            print('[trade] JSON error. Retrying.')
            #sendMessage("Order probably didn't go but you should check")
            return lastOrderTXID()

def main_position_trade(direction,avg_price,volume):
    # returns main position TXID
    price = avg_price
    if direction not in [_BUY_,_SELL_]:
        raise Exception('Invalid parameter')
    return trade(direction,price,volume,_K_CURR_)

def close_position_trade(direction,price,volume):
    # returns closing order TXID
    if direction not in [_BUY_,_SELL_]:
        raise Exception('Invalid parameter')
    return trade(direction,price,volume,_K_CURR_)

def make_trade(direction,volume,price,calcprice):
    global mainTXID,closeTXID, stoplosscount,closedirection
    if direction == _BUY_:
        opp_direction = _SELL_
    else: # Must be _SELL_
        opp_direction = _BUY_
    closedirection = opp_direction
    mainTXID = main_position_trade(direction,price,volume)
    print('Main Position TXID: '+ str(mainTXID))
    time.sleep(10)
    if orderFillCheck() == True:
        inPosition = True
        closeTXID = close_position_trade(opp_direction,calcprice,volume)
        print('Closing order TXID: '+ str(closeTXID))
        sendMessage("Main order has been filled! Check Kraken!")
        getMain()
    else:
        print('Main order did not fill, cancelling...')
        sendMessage('Main order did not fill, cancelling...')
        print(cancelOrder(mainTXID))

def cancelOrder(orderTXID):
    print('Cancelling ' +str(orderTXID) + ' Order')
    while True:
        try:
            cancel = k.query_private(_CANCEL_ORDER_, {_TXID_: orderTXID})
            if _RESULT_ not in cancel:
                print(cancel)
                if 'EOrder' in cancel[_ERROR_]:
                    print('Order already cancelled. Proceeding to next order if it exists')
                    break
                break
            else: return cancel
        except socket.timeout:
            return '[cancelOrder] Query timeout, order may not have sent. Check manually.'
            continue
        except ValueError:
            return '[cancelOrder] JSON error. Check manually.'
            continue

def makeTrade(volume,price,calcprice):
    percent = BTCETHpercent()
    if percent <= negPercent and ordersClosed():
        print('Making trade...')
        make_trade(_SELL_,volume,price,calcprice)
    elif percent >= posPercent and ordersClosed():
        print('Making trade...')
        make_trade(_BUY_,volume,price,calcprice)

def printTXIDs():
    if mainTXID:
        print("Main: " + str(mainTXID))
    if closeTXID:
        print("Close: " + str(closeTXID))

def printTime():
    time.ctime()
    print(time.strftime('%I:%M%p %Z on %b %d')) # ' 1:36PM EDT on Oct 18, 2010'

def balanceCheck(currency):
    bal = getCurrBalance(currency)
    tradevol = .27-bal
    if inPosition == False:
        if bal < .27 and .27-bal > .02:
            tradevol = .26-bal
            trade(_BUY_,round(krakenBTCETHPrice(),5),tradevol,_K_CURR_)
            time.sleep(5)
            return

def main():
    global _TRADE_VOLUME_
    _TRADE_VOLUME_ = .25 #(availablecapital/krakenEthPrice())
    while True:
        printTXIDs()
        #balanceCheck("XETH")
        makeTrade(_TRADE_VOLUME_,round(krakenBTCETHPrice(),5),round(krakencalcprice(),5))
        print("BTC/ETH diff: " + str(BTCETHpercent()))
        print("Close direction: " + str(closedirection))
        loopnum += 4
        print("Loop number:" + str(loopnum))
        if loopnum > stoplossTime:
            print("Order didn't close, stoploss triggered")
            print(cancelOrder(closeTXID))
            print(trade(str(closedirection),round(krakenBTCETHPrice(),5),_TRADE_VOLUME_,_K_CURR_))
            loopnum = 0
        elif ordersClosed():
            loopnum = 0
        time.sleep(4)

if __name__ == '__main__':
    main()
