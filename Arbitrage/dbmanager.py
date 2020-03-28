import numpy as np
import pandas as pd
import sqlite3
import atexit
from decimal import *
import time

class DbManager:

    filename = None
    conn = None
    cursor = None

    def close(self):
        print("Disconnecting from database " + str(self.filename))
        self.conn.close()

    def connect(self, filename):
        self.filename = filename
        try:
            self.conn = sqlite3.connect(filename)
            self.cursor = self.conn.cursor()
            print("Connected to database " + str(filename))
            atexit.register(self.close)
        except Exception as e:
            print("Failed to connect to database " + str(filename))
            print(e)
            exit(1)

    def query(self, query):
        print("Executing query " + query)
        return pd.read_sql(query, self.conn)

    # trade should have format (timestamp, price, volume, buy_or_sell, market_or_limit)
    def insert_trade_record(self, trade):
        sql_insert_trade_record = """INSERT OR IGNORE INTO trade_history(
                                        timestamp, 
                                        price, 
                                        volume, 
                                        buy_or_sell, 
                                        market_or_limit
                                    ) VALUES (?, ?, ?, ?, ?); """

        self.cursor.execute(sql_insert_trade_record, trade)
        self.conn.commit()

    # trade should have format (timestamp, price, volume, buy_or_sell, market_or_limit)
    def insert_many_trade_records(self, trades):
        sql_insert_many_trade_records = """INSERT OR IGNORE INTO trade_history(
                                        timestamp, 
                                        price, 
                                        volume, 
                                        buy_or_sell, 
                                        market_or_limit
                                    ) VALUES (?, ?, ?, ?, ?); """

        self.cursor.executemany(sql_insert_many_trade_records, trades)
        self.conn.commit()

    def setup(self):
        sql_create_trade_history_table = """CREATE TABLE trade_history(
                                        timestamp integer PRIMARY KEY,
                                        price integer,
                                        volume integer,
                                        buy_or_sell text,
                                        market_or_limit text
                                    ); """
        self.cursor.execute(sql_create_trade_history_table)
        self.conn.commit()

"""manager = DbManager()
manager.connect('kraken.db')
manager.insert_trade_record((0, Decimal("102.20"), Decimal("103.20"), "b", "l"))
print(manager.query("SELECT * FROM trade_history WHERE (timestamp=0)"))"""

#manager.setup()