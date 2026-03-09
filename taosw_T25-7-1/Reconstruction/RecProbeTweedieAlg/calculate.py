import numpy as np
import math
import numpy.polynomial.legendre as LG

def CalculateDist(r_rep, theta_rep, r_max=0.9, PMT_radius=0.935):
    r_rep_meter = r_rep * r_max
    cth = np.cos(theta_rep)
    dist = np.sqrt(PMT_radius ** 2 + r_rep_meter ** 2 - 2 * PMT_radius * r_rep_meter * cth)
    return np.float64(dist)

def CalculatePE(
    r_rep,
    theta_rep,
    r_max=0.9,
    PMT_radius=0.935,
    PMT_size=0.05,
    eta=0.5,
    Yield=11520,
    E_mean=0.7877,
    #E_mean=0.5006,
    tau=15,
):
    """
    Calculate PE expectation.

    Parameters
    ----------
    `r_rep`: r coordinates to calculate PE expectation; in range `[0, 1]`
    `theta_rep`: theta coordinates to calculate PE expectation
    `r_max`: the max radius of LS ball, in meter
    `PMT_radius`: the radius of position of PMT/SiPM, in meter
    `PMT_size`: the length of a side of PMT/SiPM, in meter; the area of it is `PMT_size ** 2`

    Returns
    -------
    `expect_pe`: PE expection
    `dist`: each distance between specified vertex and PMT/SiPM

    Examples
    --------
    When `rs` and `thetas` share a one to one mapping:
    ``` python
        expect_pe, dist = CalculatePE(rs, thetas)
    ```
    When `rs` and `thetas` constructs a mesh grid:
    ``` python
        expect_pe, dist = CalculatePE(rs, thetas.reshape(-1, 1))
    ```
    """
    r_rep_meter = r_rep * r_max
    cth = np.cos(theta_rep)
    dist = np.sqrt(PMT_radius ** 2 + r_rep_meter ** 2 - 2 * PMT_radius * r_rep_meter * cth)
    dist = np.float64(dist)
    cphi = (PMT_radius - r_rep_meter * cth) / dist
    solid_angle = (
        1
        / math.pi
        * np.arccos(
            dist
            * np.sqrt(
                (dist ** 2 + PMT_size ** 2 / 4 * (1 + cphi ** 2))
                / (dist ** 2 + PMT_size ** 2 / 4)
                / (dist ** 2 + PMT_size ** 2 / 4 * cphi ** 2)
            )
        )
    )
    expect_pe = E_mean * solid_angle * np.exp(-dist / tau) * Yield * eta
    return expect_pe, dist


def CalculateTime(dist, ts, coef, tbins, padding=0):
    """
    Calculate PE expectation in time.

    Parameters
    ----------
    `dist`: each distance between specified vertex and PMT/SiPM, usually calculated by `CalculatePE`
    `ts`: t coordinates to calculate PE expectation
    `coef`: coefficients for calculating Legendre polynomials, in 1-dimensional
    `tbins`: length of time window, in nanoseconds
    `padding`: pre-defined value for time not in the time window `[-1, 1]`

    Returns
    -------
    Legendre value, in shape like `ts - dist`.

    Examples
    --------
    When `rs` and `thetas` share a one to one mapping:
    ``` python
        ts = np.linspace(-1, 1, 10001)
        expect_pe, dist = CalculatePE(rs, thetas)
        expect_time = CalculateTime(dist.reshape(-1, 1), ts, coef, tbins)
        probe = np.average((expect_pe[:, np.newaxis] * expect_time).T, axis=1)
    ```
    there, we get a average probe for specified vertices.
    """
    # distance from vertex to SiPM
    flight_time = dist * 1 / 0.3 * 1.57  # ns
    t_corr = ts - flight_time / tbins * 2
    leg = np.exp(LG.legval(t_corr, coef.flatten()))
    leg[np.logical_or(t_corr < -1, t_corr > 1)] = padding
    return leg

