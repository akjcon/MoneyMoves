import numpy as np
import pandas as pd
import sqlite3
import atexit
from decimal import *
from datetime import datetime
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
        sql_insert_trade_record = """INSERT OR IGNORE INTO TRADE_HISTORY(
                                        base_currency,
                                        quote_currency,
                                        exchange,
                                        time,
                                        price,
                                        volume,
                                        precision,
                                        buy_or_sell
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?); """

        self.cursor.execute(sql_insert_trade_record, trade)
        self.conn.commit()

    # trade should have format (timestamp, price, volume, buy_or_sell, market_or_limit)
    def insert_many_trade_records(self, trades):
        sql_insert_many_trade_records = """INSERT OR IGNORE INTO TRADE_HISTORY(
                                        base_currency,
                                        quote_currency,
                                        exchange,
                                        time,
                                        price,
                                        volume,
                                        precision,
                                        buy_or_sell
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?); """

        self.cursor.executemany(sql_insert_many_trade_records, trades)
        self.conn.commit()

    def setup(self):
        sql_create_trade_history_table = """CREATE TABLE TRADE_HISTORY(
                                        base_currency text,
                                        quote_currency text,
                                        exchange text,
                                        time text,
                                        price integer,
                                        volume integer,
                                        precision integer,
                                        buy_or_sell text,
                                        PRIMARY KEY (base_currency, quote_currency, exchange, time)
                                    ); """
        self.cursor.execute(sql_create_trade_history_table)
        self.conn.commit()
