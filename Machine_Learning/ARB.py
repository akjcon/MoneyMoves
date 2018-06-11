import krakenex #pip install krakenex
import time
import socket
#import gdax #pip install gdax
from twilio.rest import Client #pip install twilio
#from bitfinex.client import Client as bfxClient

'''
This used to be a program that would trade the time delay between Kraken and GDAX/Bitfinex
but that difference is now gone so it's just used as an interface for other trading programs to
take methods from
'''

#for twilio
client = Client("AC1c40800c09f14885137023f22ac618b6","264ebf359aedd9157f654f160ca22eb7")

#for Kraken
k = krakenex.API() #private methods
k.load_key('kraken.key')
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
_TRADES_ = 'trades'
_OPEN_ = 'open'
_ERROR_ = 'error'
_OPEN_ORDERS_ = 'OpenOrders'
_CLOSED_ORDERS_ = 'ClosedOrders'
_MARKET_ = 'market'

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



def orderFillCheck(txid):
    #returns true if order has filled, false if not
    while True:
        try:
            mainorder = k.query_private(_QUERY_ORDERS_, {_TXID_: txid})
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
    # DEPRECIATED #
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

def getLastOrder(ordertype):
    # takes _OPEN_ORDERS_ or _CLOSED_ORDERS_ as argument
    if ordertype == _OPEN_ORDERS_:
         otype = _OPEN_
    else: otype = _CLOSED_
    while True:
        try:
            orders = k.query_private(ordertype)
            if _RESULT_ not in orders:
                print(orders)
                continue
            if orders[_RESULT_][otype]:
                print(orders)
                return next(iter(orders[_RESULT_][otype]))
            else: continue
        except socket.timeout:
            print('[lastOrderTXID] Socket Timeout on getting TXID')
        except ValueError:
            print('[lastOrderTXID] JSON error on getting TXID')

def sendMessage(messagebody):
    return client.messages.create(to='+19079030789',
                           from_='+17606385256',
                           body=messagebody)

def getBidAsk(ticker): #returns four values: (bid,ask,bidvol,bidask) for specified pair
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
    return bestbid,bestask,bidvol,askvol

def positionsClosed():
    # returns True if no positions are currently open
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
                _LEVERAGE_: _LEVERAGE_VALUE_
            })
            if _RESULT_ not in trade:
                if trade[_ERROR_] == 'EOrder:Insufficient funds':
                    break #make sure we don't keep trying... redundancies
                print(trade) #for info
                return _ERROR_
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




if __name__ == '__main__':
    print("test")
