# Model Importing #
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.neighbors import KNeighborsRegressor


# Other useful stuff importing #
import pickle
import requests
import datetime
import math
import pandas as pd
from random import sample
from sklearn.model_selection import train_test_split
import numpy as np
import pylab as pl

'''
Main method here takes in a dictionary key of a type of ML model, and then using the data it's given, formats the data
and then creates+trains a model for the data. Then it uses the test data (randomized) to make predictions and returns accuracy
along with simulated trades over the test period. Works best for RandomForestRegressor.
'''


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
    rf_key : RandomForestRegressor(max_depth=10, random_state=0),
    nn_key : MLPRegressor(hidden_layer_sizes=4),
    svm_key : SVR(),
    gpr_key : GaussianProcessRegressor(),
    sgd_key : SGDRegressor(penalty='elasticnet'),
    knr_key : KNeighborsRegressor()
}

def preprocess_and_save(csv):
    # processing is depending on using minute_price_historical as the dataframe
    # want ML model to use xtrain values to predict ytrain value
    df = pd.read_csv(csv)
    x = df.drop(columns=['Timestamp','Close','Weighted_Price'])
    x = x.iloc[:(len(x)-1)]
    price_end = df['Close'].iloc[1:].reset_index()
    price_start = df['Close'].iloc[:(len(df)-1)].reset_index()
    y = (100*(price_end-price_start)/price_start).drop(columns=['index'])

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

            if np.abs(predictions[i]) >= pred_sd*s and predictions[i] > .5:
                moveslist.extend(truevalues[i])
                total_pay += (sign * truevalues[i])-.2
                pred_pay += (sign * predictions[i])-.2
        print('Max gain: {}'.format(total))
        print('scale= {}:'.format(s))
        print('\t pred gain = {:0.4f}'.format(pred_pay))
        print('\t total gain = {}'.format(total_pay))
    print(moveslist)
    pl.plot(moveslist)
    print(len(moveslist))
    pl.show()
        #print('scale = {}, predicted percent gain = {:0.4f}, real percent gain = {:0.4f}'.format(s,pred_pay,total_pay))

def main(modelkey):
    traindata = preprocess_and_save('~/Desktop/ML/Data/coinbase2014-18.csv')
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
