# (c) Dan La Russa & Randy Taylor
# routines for fitting histograms

import numpy as np
import matplotlib.mlab as mlab
from scipy.optimize import curve_fit


def gauss_fit(data, freq, bins, binwidth):
    """
    Fits a Gaussian pdf to a histogram using
    the method of least squares.
    data = array of binned values
    freq = array of values for each bin
    bins = array of left-most positions for each bin
    binwidth = width of bin (float, not an array)
    """
    x = bincenters(bins)
    norm = np.float(np.size(data) * binwidth)

    initGuess = [norm, np.mean(data), np.std(data)]
    optParam, cov = curve_fit(gauss_pdf, x, freq, initGuess)

    return optParam, cov



def bincenters(bins):
    """
    Finds the midpoint of histogram bins from plots generated
    with matplotlib.
    """
    bincenters = 0.5 * (bins[1: ] + bins[:- 1])
    return bincenters



def gauss_pdf(x, norm, mu, sigma):
    """
    The method calculates the value of the Gaussian probability
    density function (using matplotlib routines) for a value/array x.
    for a given mean (mu) and standard deviation (sigma). The results
    is normalized (multiplied by) 'norm', and so 'norm' should equal
    1.000 unless you have a reason for it to be otherwise.
    """
    if any(np.isnan([norm,mu,sigma])) or any(np.isnan(x)):
        raise Exception("Invalid value in gauss_pdf")

    GaussPdf = norm * mlab.normpdf(x, mu, sigma)
    return GaussPdf
