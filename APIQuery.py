import krakenex #pip install krakenex
import time
import socket
import gdax #pip install gdax
from twilio.rest import Client #pip install twilio
from bitfinex.client import Client as bfxClient

#known issues:
# - none as of now
# TODO: print PNL after position is closed

'''
Basically this was a program that traded based on the time delay between Kraken and GDAX, 
but now that delay is gone so this is just used as an interface for other programs to use
'''

#for twilio
client = Client("AC06acf04d5efc6ae091465ef53268a697","459ffb1e09486a45db18fe5cc50813b4")

#for Kraken
k = krakenex.API()
k.load_key('kraken.key')
c = krakenex.Connection()

#for Bitfinex
bfxClient = bfxClient()

#for GDAX
GDAXpublic_client = gdax.PublicClient()

# transaction IDs/info for closing extra trades:
mainTXID = ''
closeTXID = ''
stoplossTXID = ''
main = ''
trade = ''
stoplosscount = 0

# Api Key Strings:
_K_CURR_ = 'XETHZUSD'
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
availablecapital = 160
posTradePriceGap = 4
negTradePriceGap = -4

def orderFillCheck():
    #returns true if main order has filled, false if not
    time.sleep(90)
    while True:
        try:
            mainorder = k.query_private(_QUERY_ORDERS_, {_TXID_: mainTXID})
            if _RESULT_ in mainorder:
                mTXID = mainorder[_RESULT_][mainTXID]
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

def cleanUp():
    # cancels all extra orders after a position has been closed, just to be sure.
    while True:
        try:
            opens = k.query_private(_OPEN_ORDERS_)
            if opens[_RESULT_] and opens[_RESULT_][_OPEN_]:
                for key,value in opens[_RESULT_][_OPEN_]:
                    print(cancelOrder(key))
                    break
            else: break
        except socket.timeout:
            print('[positionsClosed] Timeout Error. Retrying.')
        except ValueError:
            print('[positionsClosed] JSON Error. Retrying.')

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

def getBalance():
    return k.query_private('TradeBalance', {'asset': 'ZUSD'})[_RESULT_]['mf'] #not used

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
                           from_='+14243611620',
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

def GDAXEthPrice():
    while True:
        try:
            orderbook = GDAXpublic_client.get_product_order_book(_G_CURR_, level=1)
            break
        except ValueError:
            print('[GDAXEthPrice] JSON Error. Retrying.')
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error")
    bestbid = float(orderbook[_BIDS_][0][0])
    bestask = float(orderbook[_ASKS_][0][0])
    return (bestask+bestbid)/2

def BitfinexPrice():
    while True:
        try:
            return float(bfxClient.ticker('ETHUSD')['mid'])
        except KeyboardInterrupt:
            raise
        except:
            print("Unexpected error in BFX price")

def kraken_minus_gdax():
    return krakenEthPrice() - GDAXEthPrice()

def kraken_minus_bfx():
    return krakenEthPrice() - BitfinexPrice()

def positionsClosed():
    if not mainTXID: #if mainTXID is empty
        return True
    else:
        while True:
            try:
                opens = k.query_private(_OPEN_POSITIONS_)
                if _RESULT_ in opens:
                    return len(opens[_RESULT_]) == 0
            except socket.timeout:
                print('[positionsClosed] Timeout Error. Retrying.')
            except ValueError:
                print('[positionsClosed] JSON Error. Retrying.')

def trade(direction,price,volume):
    # should return the TXID of the trade
    while True:
        try:
            trade = k.query_private(_ADD_ORDER_,{
                _PAIR_: _ETH_CURRENCY_,
                _TYPE_: direction,
                _ORDER_TYPE_: _LIMIT_,
                _PRICE_: price,
                _VOLUME_: volume,
                _LEVERAGE_: _LEVERAGE_VALUE_
            })
            if _RESULT_ not in trade:
                if trade[_ERROR_] == 'EOrder:Insufficient funds':
                    break
                print(trade)
                continue
            else:
                sendMessage('Trade order with ID' + trade[_RESULT_][_TXID_][0] + 'sent. Check Kraken. ')
                return trade[_RESULT_][_TXID_][0]
        except socket.timeout:
            print('[trade] Order Timeout. Check TXIDs')
            sendMessage("Order probably didn't go but you should check")
            lastorder = lastOrderTXID()
            if lastorder != mainTXID:
                return lastorder
            else: continue
        except ValueError:
            print('[trade] JSON error. Retrying.')
            sendMessage("Order probably didn't go but you should check")
            return lastOrderTXID()

def main_position_trade(direction,avg_price,volume):
    # returns main position TXID
    price = avg_price
    if direction not in [_BUY_,_SELL_]:
        raise Exception('Invalid parameter')
    if volume < .01:
        raise Exception('Invalid volume')
    # Check the validity of params

    if direction == 'buy':
        price += _LIMIT_PRICE_DIFF_
    else: # Must be a sell
        price -= _LIMIT_PRICE_DIFF_

    return trade(direction,price,volume)

def close_position_trade(direction,price,volume):
    # returns closing order TXID
    if direction not in [_BUY_,_SELL_]:
        raise Exception('Invalid parameter')
    if volume < .01:
        raise Exception('Invalid volume')

    return trade(direction,price,volume)

def make_trade(direction,volume):
    global mainTXID,closeTXID, stoplosscount
    if direction == _BUY_:
        opp_direction = _SELL_
    else: # Must be _SELL_
        opp_direction = _BUY_
    #cleanUp()
    stoplosscount = 0
    mainTXID = main_position_trade(direction,round(krakenEthPrice(),2),volume)
    print('Main Position TXID: '+ str(mainTXID))
    time.sleep(3)
    closeTXID = close_position_trade(opp_direction,round((GDAXEthPrice()+.3),2),volume)
    print('Closing order TXID: '+ str(closeTXID))
    if orderFillCheck() == True:
        sendMessage("Trade has been filled! Check Kraken!")
        getMain()
    else:
        print('Orders did not fill, cancelling...')
        sendMessage('Orders did not fill, cancelling...')
        print(cancelOrder(mainTXID))
        print(cancelOrder(closeTXID))

def cancelOrder(orderTXID):
    print('Cancelling ' +str(orderTXID[:-4]) + ' Order')
    while True:
        try:
            cancel = k.query_private(_CANCEL_ORDER_, {_TXID_: orderTXID})
            if _RESULT_ not in cancel:
                print(cancel)
                if 'EOrder' in cancel[_ERROR_]:
                    print('Order already cancelled. Proceeding to next order if it exists')
                    break
                continue
        except socket.timeout:
            return '[cancelOrder] Query timeout, order may not have sent. Check manually.'
            continue
        except ValueError:
            return '[cancelOrder] JSON error. Check manually.'
            continue

def makeTrade(volume):
    if kraken_minus_bfx() <= negTradePriceGap and positionsClosed():
        print('Making trade...')
        make_trade(_BUY_,volume)
    elif kraken_minus_bfx() >= posTradePriceGap and positionsClosed():
        print('Making trade...')
        make_trade(_SELL_,volume)

def printTXIDs():
    if mainTXID:
        print(mainTXID)
    if closeTXID:
        print(closeTXID)
    if stoplossTXID:
        print(stoplossTXID)

def printTime():
    time.ctime()
    print(time.strftime('%I:%M%p %Z on %b %d')) # ' 1:36PM EDT on Oct 18, 2010'

if __name__ == '__main__':
    _TRADE_VOLUME_ = (availablecapital/krakenEthPrice())
    while True:
        #print('Price Difference: ' + str(kraken_minus_bfx()))
        #printTime()
        #stopLoss()
        #printTXIDs()
        #makeTrade(_TRADE_VOLUME_)
        #positionsClosed()
        btc = krakenBTCPrice()
        eth = krakenEthPrice()
        btceth = eth/btc
        kbtceth = krakenBTCETHPrice()

        print("BTC " + str(btc))
        print("ETH " + str(eth))
        print("BTC/ETH diff: " + str((btceth - kbtceth)/kbtceth*100))
        time.sleep(6)
