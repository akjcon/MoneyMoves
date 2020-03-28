


class Position:
    '''provides a data structure for each position'''

    def __init__(self,type,open,size):
        '''new order object'''
        self.type = type
        self.open = open
        self.size = size
        self.close = -999
        self.orderID = 12345

    def __str__(self):
        return "Order {} | {} | Open Price: {} | Close Price: {} | Size: {}".format(self.orderID,self.type,self.open,self.close,self.size)

        #when positions become real on kraken, things can be added here
        #like order ID, a filled boolean, timestamp, etc

if __name__ == '__main__':
    test = Position('long',1.2,1000)
    print(test)
