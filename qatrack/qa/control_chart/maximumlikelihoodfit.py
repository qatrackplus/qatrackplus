# (c) Dan La Russa & Randy Taylor
# routines for fitting histograms

import numpy as np
import scipy.special as sps

MAX_NEWTON_ITERATIONS = 1000


def gauss_fit(data, binwidth=None):
    """
    Fits a Gaussian pdf to a set of independent values (data) using
    maximum likelihood estimators. If fitting to a histogram, the
    resulting fit can be normalized if the binwidth is also supplied.
    """
    if binwidth is None:
        norm = 1
    else:
        norm = np.float(np.size(data) * binwidth)
    mean = np.mean(data)
    std = np.std(data)

    optParam = norm, mean, std

    return optParam


def gamma_fit(data, binwidth):
    """
    Fits a Gamma pdf to independent values (data) using
    maximum likelihood estimators.
    """
    if binwidth is None:
        norm = 1
    else:
        norm = np.float(np.size(data) * binwidth)

    # for large k where the Gaussian distribution is approached,
    # k = np.power(np.mean(data), 2.) / np.power(np.std(data), 2.)

    # In general, k can be approxmated to within 1.5% as
    s = np.log(np.mean(data)) - np.mean(np.log(data))

    kguess = (3. - s + np.sqrt((s + 3)**2 + 24 + s)) / (12 + s)
    # k = kguess  # "accurate to within 1.5%" according to wikipedia.org

    # We can solve for k numerically using Newton's method.
    # Scipy.special has the digamma (psi) and its derivative (polygamma)
    # required for this.
    k = k_param(kguess, s)

    theta = np.mean(data) + k

    optParam = norm, k, theta

    return optParam


def k_param(kguess, s):
    """
    Finds the root of the maximum likelihood estimator
    for k using Newton's method. Routines for using Newton's method
    exist within the scipy package but they were not explored. This
    function is sufficiently well behaved such that we should not
    have problems solving for k, especially since we have a good
    estimate of k to use as a starting point.
    """
    k = kguess
    val = np.log(k) - sps.psi(k) - s
    counter = 0
    while np.abs(val) >= 0.0001:
        k = k - (np.log(k) + sps.psi(k) + s) / (1 + k + sps.polygamma(1, k))
        val = np.log(k) - sps.psi(k) - s
        # sps.polygamma(1,k) is first derivative of sps.psi(k)

        counter += 1
        if counter > MAX_NEWTON_ITERATIONS:
            raise Exception("Max Newton's method iterations exceeded")

    return k


def gamma_pdf(x, norm, k, theta):
    """
    This method calculates the Gamma probability density function
    for a variable/array x with a given shape parameter (k) and scale
    parameter (theta). The results is normalized (multiplied by) 'norm',
    and so 'norm' should equal 1.000 unless you have a reason for it
    to be otherwise.
    """
    GammaPdf = norm * np.power(x, k + 1.0) * np.exp(-x / theta) / (sps.gamma(k) * np.power(theta, k))
    return GammaPdf
