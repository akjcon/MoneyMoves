# Model Importing #
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.neighbors import KNeighborsRegressor

# Other useful stuff importing #
#import matplotlib
#matplotlib.use('TkAgg') #for working on school computers
import pickle
import requests
import datetime
import math
import pandas as pd
from random import sample
from sklearn.model_selection import train_test_split
import numpy as np
#import pylab as pl

# String Constants #
score = ''
_xtrain_fn = 'xtrain.pkl'
_ytrain_fn = 'ytrain.pkl'
_xtest_fn = 'xtest.pkl'
_ytest_fn = 'ytest.pkl'
rf_key = 'RandomForest'
nn_key = 'NeuralNet'
svm_key = 'SupportVectorMachine'
gpr_key = 'GaussianProcessRegressor'
sgd_key = 'StochasticGradientDescent'
knr_key = 'KNeighborsRegressor'

# Model Dictionary for save names #
filename_dictionary = {
    rf_key : 'RandomForestRegressor.sav',
    nn_key : 'NeuralNet.sav',
    svm_key : 'SupportVectorMachine.sav',
    gpr_key : 'GaussianProcessRegressor.sav',
    sgd_key : 'StochasticGradientDescent.sav',
    knr_key : 'KNeighborsRegressor.sav'
}
# Model Dictionary for model initialization #
model_dictionary = {
    rf_key : RandomForestRegressor(max_depth=10,n_jobs=-1, random_state=0,verbose=False),
    nn_key : MLPRegressor(hidden_layer_sizes=500,random_state=6900,warm_start=False,tol=.0001,verbose=False,max_iter=1000),
    svm_key : SVR(),
    gpr_key : GaussianProcessRegressor(),
    sgd_key : SGDRegressor(penalty='elasticnet'),
    knr_key : KNeighborsRegressor()
}

'''
Using a Random Forest Regressor yeilds a 31% gain over a 2.4 month period, assuming
.14% fees and using random state=0.
Using a Neural Net can yeild a much heigher return, but only with very low to zero fees

Also can't figure out why all the ML models change returns every time. ???
How to assess accuracy of ML algorithms? Difference between predicted return and actual..?
'''

def preprocess_and_save(csv):
    # processing is depending on using minute_price_historical as the dataframe
    # want ML model to use xtrain values to predict ytrain value
    df = pd.read_csv(csv)
    x = df.drop(columns=['Close','Date','Symbol','GDAX_Close','Index'])
    x = x.iloc[:(len(x)-1)]
    price_end = df['Close'].iloc[1:].reset_index()
    price_start = df['Close'].iloc[:(len(df)-1)].reset_index()
    y = (100*(price_end-price_start)/price_start).drop(columns=['index'])

    # add lagging inputs

    x['lagopen1'] = x['Open']
    x['lagopen2'] = x['Open']
    x['lagopen3'] = x['Open']
    x['lagvol1'] = x['Volume To']
    x['lagvol2'] = x['Volume To']
    x['lagvol3'] = x['Volume To']
    x['Glagopen1'] = x['GDAX_Open']
    x['Glagopen2'] = x['GDAX_Open']
    #x['Glagopen3'] = x['GDAX_Open']
    x.lagopen1.shift(1)
    x.lagopen2.shift(2)
    x.lagopen3.shift(3)
    x.lagvol1.shift(1)
    x.lagvol2.shift(2)
    x.lagvol3.shift(3)
    x.Glagopen1.shift(1)
    x.Glagopen2.shift(2)
    #x.Glagopen3.shift(3)
    x = x[3:-3]
    y = y[3:-3]

    # Shuffling and splitting the data into training and testing sets
    ptest = 0.3
    xtrain, xtest, ytrain, ytest = train_test_split(x, y, test_size=ptest, random_state=42)

    # Saving the data
    xtrain.to_pickle(_xtrain_fn)
    ytrain.to_pickle(_ytrain_fn)
    xtest.to_pickle(_xtest_fn)
    ytest.to_pickle(_ytest_fn)


    print("Saved OHLCV Data to Disk")

def fit_model(model,xtrain,ytrain,filename):
    #creates a random forest regressor model and trains it then saves it
    model.fit(xtrain,ytrain)
    trainscore = model.score(xtrain,ytrain)
    # save the model to disk
    pickle.dump(model, open(filename, 'wb'))
    print("Created and Saved Model")
    print(filename)
    print("R squared for train: {:0.4f}".format(trainscore))

def next_value(filename,test):
    model = pickle.load(open(filename, 'rb'))
    return model.predict(test)

def predict_values(filename,xtest,ytest):
    #load the model from disk
    print("Loading model from disk...")
    model = pickle.load(open(filename, 'rb'))
    print("Using test set to predict values")
    predictions = model.predict(xtest)
    testscore = model.score(xtest,ytest)
    print("R squared for test: {:0.4f}".format(testscore))

    #
    rmse = math.sqrt((sum((ytest.iloc[x] - predictions[x])**2 for x in range(len(ytest))))/len(ytest))
    print('RMSE: ' + str(rmse))

    # Financial Performance
    model_portfolio(predictions,ytest.as_matrix())


def model_portfolio(predictions,truevalues):
    pred_sd = predictions.std()
    moveslist = []
    #print(np.abs(truevalues).mean())
    #print(np.abs(predictions).mean())
    #print(np.abs(truevalues).std())
    #print(pred_sd)

    scales = [0.25*x for x in range(12)]
    for s in scales:
        total_pay = 0
        pred_pay = 0
        total = 0
        for i in range(len(predictions)):
            sign = np.sign(predictions[i])
            # 1 if "BUY", -1 if "SELL"
            total += abs(truevalues[i])

            if predictions[i] > 0.28 and np.abs(predictions[i]) >= pred_sd*s:
                moveslist.extend(truevalues[i])
                total_pay += (sign * truevalues[i])-.14
                pred_pay += (sign * predictions[i])-.14
        print('scale= {}:'.format(s))
        print('\t pred gain = {}'.format(pred_pay))
        print('\t total gain = {}'.format(total_pay))
    print('Max gain: {}'.format(total))
    pl.hist(moveslist,bins=60)
    print(len(moveslist))
    #pl.show()


def main(modelkey):
    traindata = preprocess_and_save('~/Desktop/MoneyMoves/Machine_Learning/Data/Combo.csv')
    xtrain = pd.read_pickle(_xtrain_fn)
    ytrain = pd.read_pickle(_ytrain_fn)
    print("Loaded data from disk")
    model_type = model_dictionary[modelkey]
    filename = filename_dictionary[modelkey]

    fit_model(model_type,xtrain,ytrain,filename)

    xtest = pd.read_pickle(_xtest_fn)
    ytest = pd.read_pickle(_ytest_fn)

    predict_values(filename,xtest,ytest)

if __name__ == '__main__':
    main(rf_key)
