# (c) Dan La Russa & Randy Taylor

import numpy as np

def binwidth(x, maxBins = None):
    """ 
    This method determines the optimal binwidth for a sample of data 
    The algorithm is taken from Neural Computation 19, 6, 1503 - 1527.
    N.B. This algorithm assume all events in a sample are independent.
    """

    minBins = 1         # must be not be zero!
    if maxBins is None:
        maxBins = 500   # must be larger than minBins

    span = np.max(x) - np.min(x)
    numOfBins = np.linspace(minBins, maxBins, maxBins - minBins + 1)
    C =  np.zeros( len(numOfBins) )

    for i in np.arange(0, len(numOfBins)):
        k, edges = np.histogram(x, bins = numOfBins[i])
        C[i] = get_cost_func(k, span, numOfBins[i])

    minCindex = np.where( C == np.min(C) )
    optBinWidth = span / numOfBins[minCindex]

    return optBinWidth

    

def get_cost_func(k, span, numOfBins):
    """ Calculates the cost function for a given bin width. """

    binwidth = span / numOfBins
    kmean = np.sum(k) / numOfBins
    var = np.sum( np.power(k - kmean, 2) ) / numOfBins

    cost_func = (2.* kmean - var) / np.power(binwidth, 2)

    return cost_func
