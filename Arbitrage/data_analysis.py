import csv
import matplotlib
import pandas as pd
import numpy as np
import pylab as pl

def histogram_from_csv(filename):
    df = pd.read_csv(filename)
    df.hist(bins=60)
    pl.show()

if __name__ == '__main__':
    histogram_from_csv('forexdata.csv')
