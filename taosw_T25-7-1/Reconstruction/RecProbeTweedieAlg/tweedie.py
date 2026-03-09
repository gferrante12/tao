import numpy as np
from scipy.special import loggamma

def tweedie_pdf(y, p, mu, phi):
    '''calculate tweedie pdf for 1 < p < 2

    Args:
        y: vector of values
        p: value of xi
        mu: array of mean value
        phi: dispersion coefficient

    Returns:
        density: tweedie probability density
    '''
    y0 = (y == 0)
    yp = (y != 0)

    density = np.zeros(len(y))

    if type(mu) is not np.ndarray:
        mu = np.full(len(y), mu)

    if np.any(y == 0):
        lambda_pois = mu[y0]**(2 - p) / (phi * (2 - p))
        density[y0] = np.exp(-lambda_pois)

    if np.any(y != 0):
        y = y[yp]
        a = (2 - p) / (1 - p)
        a1 = 1 - a
        r = -a * np.log(y) + a * np.log(p - 1) - a1 * np.log(phi) - np.log(2 - p)
        drop = 37
        logz = max(r)
        j_max = max(y**(2 - p)/(phi * (2 - p)))
        j = max(1, j_max)
        cc = logz + a1 + a * np.log(-a)
        wmax = a1 * j_max
        estlogw = wmax
        while (estlogw > (wmax - drop)):
            j = j + 2
            estlogw = j * (cc - a1 * np.log(j))

        hi_j = np.ceil(j).astype(int)
        logz = min(r)
        j_max = min(y ** (2 - p) / (phi * (2 - p)))
        j = max(1, j_max)
        wmax = a1 * j_max
        estlogw = wmax

        while ((estlogw > (wmax - drop)) and (j >= 2)):
            j = max(1, j - 2)
            estlogw = j * (cc - a1 * np.log(j))

        lo_j = max(1, np.floor(j).astype(int))
        j = np.arange(lo_j, hi_j+1)
        o = np.ones((len(y), 1))
        g = np.ones((1, hi_j - lo_j + 1)) * (loggamma(j+1) + loggamma(-a*j))
        og = o.dot(g)

        A = np.outer(r, j) - og

        m = np.apply_along_axis(np.max, 1, A)
        we = np.exp(A - m.reshape(-1, 1))
        sum_we = np.apply_along_axis(np.sum, 1, we)
        logw = np.log(sum_we) + m

        tau = phi * (p - 1) * mu[yp]**(p - 1)
        lambda_pois = mu[yp]**(2 - p) / (phi * (2 - p))

        logf = -y / tau - lambda_pois  - np.log(y) + logw
        f = np.exp(logf)

        density[yp] = f

    return density

def tweedie_dmu(y, p, mu, phi):
    '''calculate the derivative of f wrt mu
    NOTE: p, mu and phi must be independent.

    Args:
        y: vector of values
        p: value of xi
        mu: array of mean value
        phi: dispersion coefficient

    Returns:
        density: derivative tweedie probability density
    '''
    y0 = (y == 0)
    yp = (y != 0)

    density = np.zeros(len(y))

    if type(mu) is not np.ndarray:
        mu = np.full(len(y), mu)

    if np.any(y == 0):
        lambda_pois = mu[y0]**(2 - p) / (phi * (2 - p))
        dlambda_dmu = mu[y0]**(1 - p) / phi
        density[y0] =  -np.exp(-lambda_pois) * dlambda_dmu

    if np.any(y != 0):
        density[yp] = tweedie_pdf(y[yp], p, mu[yp], phi)

        tau = phi * (p - 1) * mu[yp]**(p - 1)
        lambda_pois = mu[yp]**(2 - p) / (phi * (2 - p))

        dtau = phi * (p - 1)**2 * mu[yp]**(p - 2)
        dlambda = mu[yp]**(1 - p) / phi
        t1 = y[yp] / tau**2 * dtau - dlambda

        density[yp] = density[yp] * t1

    return density


def tweedie_dlambda(y, p, mu, phi):
    '''calculate the derivative of f wrt lambda

    Args:
        y: vector of values
        p: value of xi
        mu: array of mean value
        phi: dispersion coefficient

    Returns:
        density: derivative tweedie probability density
    '''
    y0 = (y == 0)
    yp = (y != 0)

    density = np.zeros(len(y))

    if type(mu) is not np.ndarray:
        mu = np.full(len(y), mu)

    if np.any(y == 0):
        lambda_pois = mu[y0]**(2 - p) / (phi * (2 - p))
        density[y0] = -np.exp(-lambda_pois)

    if np.any(y != 0):
        y = y[yp]
        a = (2 - p) / (1 - p)
        a1 = 1 - a
        r = -a * np.log(y) + a * np.log(p - 1) - a1 * np.log(phi) - np.log(2 - p)
        drop = 37
        logz = max(r)
        j_max = max(y**(2 - p)/(phi * (2 - p)))
        j = max(1, j_max)
        cc = logz + a1 + a * np.log(-a)
        wmax = a1 * j_max
        estlogw = wmax
        while (estlogw > (wmax - drop)):
            j = j + 2
            estlogw = j * (cc - a1 * np.log(j))

        hi_j = np.ceil(j).astype(int)
        logz = min(r)
        j_max = min(y ** (2 - p) / (phi * (2 - p)))
        j = max(1, j_max)
        wmax = a1 * j_max
        estlogw = wmax

        while ((estlogw > (wmax - drop)) and (j >= 2)):
            j = max(1, j - 2)
            estlogw = j * (cc - a1 * np.log(j))

        lo_j = max(1, np.floor(j).astype(int))
        j = np.arange(lo_j, hi_j+1)
        o = np.ones((len(y), 1))
        g = np.ones((1, hi_j - lo_j + 1)) * (loggamma(j+1) + loggamma(-a*j))
        og = o.dot(g)

        A = np.outer(r, j) - og

        m = np.apply_along_axis(np.max, 1, A)
        we = np.exp(A - m.reshape(-1, 1))
        sum_we = np.apply_along_axis(np.sum, 1, we)
        logw = np.log(sum_we) + m

        tau = phi * (p - 1) * mu[yp]**(p - 1)
        lambda_pois = mu[yp]**(2 - p) / (phi * (2 - p))

        logf = -y / tau - lambda_pois  - np.log(y) + logw
        f = np.exp(logf)

        # calculate dW/dlambda
        A1 = A - np.log(lambda_pois).reshape(-1, 1) + np.log(j)
        m1 = np.apply_along_axis(np.max, 1, A1)
        we1 = np.exp(A1 - m1.reshape(-1, 1))
        sum_we1 = np.apply_along_axis(np.sum, 1, we1)
        logdw = np.log(sum_we1) + m1

        density[yp] = f * (-1 + np.exp(logdw - logw))

    return density
