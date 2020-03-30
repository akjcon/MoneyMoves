from binance.client import Client
import time

binance_api_key = '[REDACTED]' #put your own api creds here
binance_api_secret = '[REDACTED]'#put your own api creds here

client = Client(binance_api_key, binance_api_secret)

def get_trades(symbol,limit,fromId=''):
    if fromId:
        trades = client.get_historical_trades(symbol=symbol,limit=limit,fromId=fromId)
    else: trades = client.get_historical_trades(symbol=symbol,limit=limit)

    return trades

if __name__ == '__main__':
    block = get_trades('PAXUSDT',limit=1000,fromId=1635183) #first 1000 trades since Jan 1 2019
    curr_id = get_trades('PAXUSDT',limit=1)[0]['id']
    year_list = block
    id = block[999]['id']
    f = open("binance_PAXUSDT.txt", "a")
    for trade in block:
        f.write('{}\n'.format(trade))

    while id < curr_id:
        newblock = get_trades('PAXUSDT',limit=1000,fromId=id)
        id = newblock[999]['id']
        year_list.extend(newblock)
        print(id)
        for newtrade in newblock:
            f.write('{}\n'.format(newtrade))
        time.sleep(.3)
    print("Done! {} trades recorded!".format(len(year_list)))
