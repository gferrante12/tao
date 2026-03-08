#!/usr/bin/env python3
"""
sipm_fit_models_v2.py
=====================
Physics-motivated fit models for SiPM ADC spectra at TAO.
No external optimizers — custom BFGS (MIGRAD-equivalent), no scipy.

MODELS
------
1. multigauss      Plain multi-Gaussian (baseline, up to 8 PE peaks)
2. multigauss_ct   Multi-Gaussian + binomial optical crosstalk (physics-motivated)
3. multigauss_ap   Multi-Gaussian + geometric afterpulse (SYSU/TAO model, Ziang Li 2026)
4. emg             Exponential Modified Gaussian with shared CT tail (continuous approx.)
5. emg_ap          EMG peaks + geometric afterpulse (combined model)

COMMON PARAMETRISATION
-----------------------
  μ_n  = μ_1 + (n-1)·Gain           equidistant PE peaks
  σ_n  = sqrt(n·σ_PE² + σ_base²)   quadratic width scaling with PE multiplicity
  COTI threshold (optional): erf factor applied to left side of 1PE peak to model
  hardware COTI threshold cutting the rising edge.

PHYSICS NOTES
-------------
MODEL multigauss_ct (Binomial optical crosstalk):
  The most physically motivated TAO model. Each primary n-PE event can produce
  k additional optical CT avalanches with probability
    P(k|n) = C(n,k) · p_ct^k · (1-p_ct)^{n-k}    (k = 0, 1, ..., K_ct)
  Observed charge deposited at PE position n+k:  μ_{n+k}, σ_{n+k}.
  Free amplitudes A_n represent the TRUE (pre-CT) detected PE distribution.
  K_ct = 3 suffices for p_ct < 0.20; external CT dominates at TAO over internal CT.
  Reference: Ziang Li, Backup slide "Generalized Poisson Distribution", JAN 2026.
  Note: the Generalized Poisson model for amplitude constraints is NOT used because
  at TAO with Ge-68 source the dominant CT is EXTERNAL (optical, between SiPMs),
  making GP amplitude priors unreliable (as noted in the backup slides).

MODEL multigauss_ap (SYSU geometric afterpulse, Hanwen's model):
  f_n(Q) = A_n · Σ_{i=0}^{N_ap} (1-nα)(nα)^i · G(Q; μ_n + i·Q_ap, σ_n)
  i=0: main PE peak.  i>0: afterpulse sub-peaks shifted by i·Q_ap
  (appear as bumps BETWEEN integer PE peaks).
  α = after-pulse probability per fired cell (constraint: n·α < 1).
  Q_ap = charge deposited by single AP avalanche (typically 0.1–0.4·Gain).
  Reference: Ziang Li slides, "Four Gaussian Fitting", TAO commissioning 2026.

MODEL emg (Exponential Modified Gaussian):
  f(x) = A/(2τ) exp[(μ-x)/τ + σ²/(2τ²)] · erfc[σ/(τ√2) - (x-μ)/(σ√2)]
  Gaussian peak convolved with one-sided exponential: models continuous right
  CT / AP tail. τ/Gain ≈ p_ct (single-level approximation).
  Reference: Kowalski & Bhatt, journals.vsu; standard SiPM spectroscopy.

MINIMISATION (MIGRAD-equivalent, implemented from scratch)
-------------------------------------------------------------
Custom L-BFGS-B variant:
  · Central-difference gradients, parameter-relative step h = max(ε|x|, ε)
  · Armijo sufficient-decrease backtracking line search
  · Box constraint projection at each step
  · Numerical Hessian at convergence → covariance matrix (Cov = ½ H⁻¹)
  · Scaled gradient norm convergence criterion

TWO-STAGE FITTING
-----------------
Stage 1: Fit each detected PE peak independently (single Gaussian) in a narrow
         window. Provides good initial conditions: μ₁, Gain, σ_PE, σ_base.
Stage 2: Joint multi-peak model fit starting from Stage-1 values.
"""

import math
import numpy as np
from math import comb

# ---------------------------------------------------------------------------
# Vectorised math primitives (no scipy)
# ---------------------------------------------------------------------------
erfc_arr = np.vectorize(math.erfc)
erf_arr  = np.vectorize(math.erf)

MODEL_NAMES = ('multigauss', 'multigauss_ct', 'multigauss_ap', 'emg', 'emg_ap')

MODEL_LABELS = {
    'multigauss':    'Multi-Gaussian',
    'multigauss_ct': 'Multi-Gauss + CT (Binomial)',
    'multigauss_ap': 'Multi-Gauss + AP (SYSU)',
    'emg':           'EMG (CT tail)',
    'emg_ap':        'EMG + AP',
}

# ---------------------------------------------------------------------------
# Shared peak geometry
# ---------------------------------------------------------------------------

def peak_mu(n, mu1, gain):
    """μ_n = μ_1 + (n-1)·Gain  (1-indexed: n=1 → μ_1)."""
    return mu1 + (n - 1) * gain

def peak_sigma(n, sigma_pe, sigma_base):
    """σ_n = sqrt(n·σ_PE² + σ_base²).  Floor at 1 ADC."""
    return math.sqrt(max(n * sigma_pe**2 + sigma_base**2, 1.0))

def gauss(x, A, mu, sigma):
    """A · exp(−(x−μ)² / (2σ²))  — amplitude parametrisation."""
    s = max(abs(sigma), 1.0)
    return A * np.exp(-0.5 * ((x - mu) / s)**2)

def coti_erf_factor(x, q_thr, sigma_thr):
    """
    COTI hardware threshold correction for 1PE peak (erf rise).
      0.5 · [1 + erf((x − Q_thr) / (σ_thr · √2))]
    Applied only to the i=0 sub-peak of the 1PE Gaussian.
    """
    s = max(abs(sigma_thr), 1.0)
    return 0.5 * (1.0 + erf_arr((x - q_thr) / (s * math.sqrt(2.0))))


# ---------------------------------------------------------------------------
# MODEL 1  multigauss  —  plain multi-Gaussian
# ---------------------------------------------------------------------------

def model_multigauss(x, n_peaks, mu1, gain, sigma_pe, sigma_base, amplitudes,
                     apply_coti=False, q_thr=0.0, sigma_thr=1.0):
    """
    Baseline multi-Gaussian:  f(Q) = Σ_{n=1}^{N} A_n · G(Q; μ_n, σ_n).

    Parameters
    ----------
    x          : array of ADC bin centres
    n_peaks    : number of PE peaks (up to 8)
    mu1        : position of the 1PE peak [ADC]
    gain       : peak spacing [ADC/PE]
    sigma_pe   : single-photon width contribution
    sigma_base : baseline/electronics width contribution
    amplitudes : list of length n_peaks (peak heights)
    apply_coti : multiply 1PE Gaussian by erf threshold factor
    q_thr, sigma_thr : COTI threshold parameters
    """
    y = np.zeros_like(x, dtype=float)
    for n in range(1, n_peaks + 1):
        A_n = max(amplitudes[n-1], 0.0)
        g   = gauss(x, A_n, peak_mu(n, mu1, gain), peak_sigma(n, sigma_pe, sigma_base))
        if apply_coti and n == 1:
            g *= coti_erf_factor(x, q_thr, sigma_thr)
        y += g
    return y


# ---------------------------------------------------------------------------
# MODEL 2  multigauss_ct  —  binomial optical crosstalk
# ---------------------------------------------------------------------------

def model_multigauss_ct(x, n_peaks, mu1, gain, sigma_pe, sigma_base, amplitudes,
                        p_ct, k_ct_max=3,
                        apply_coti=False, q_thr=0.0, sigma_thr=1.0):
    """
    Multi-Gaussian with binomial optical crosstalk weights.

    Each primary n-PE event triggers k additional CT avalanches:
      w(k|n) = C(n,k) · p_ct^k · (1-p_ct)^{n-k}
    The total observed PE is n+k, placed at μ_{n+k}, σ_{n+k}.

    amplitudes[n-1] = A_n = number of TRUE n-PE primary events (before CT).
    p_ct = per-photon optical crosstalk probability (shared, global).
    k_ct_max = max CT order considered (3 covers >99% for p_ct < 0.2).

    Physical motivation: dominant CT at TAO is external optical CT between
    neighbouring SiPM pixels; binomial model is the correct framework.
    Ref: Ziang Li (SYSU) backup slides, TAO gain fitting report JAN 2026.
    """
    p_ct = max(0.0, min(p_ct, 0.98))
    y    = np.zeros_like(x, dtype=float)

    for n in range(1, n_peaks + 1):
        A_n = max(amplitudes[n-1], 0.0)
        if A_n < 1e-10:
            continue
        for k in range(0, k_ct_max + 1):
            # Binomial weight
            w = comb(n, k) * (p_ct**k) * ((1.0 - p_ct)**(n - k))
            if w < 1e-12:
                continue
            obs = n + k           # observed PE after CT
            mu_obs  = peak_mu(obs,  mu1, gain)
            sig_obs = peak_sigma(obs, sigma_pe, sigma_base)
            g = gauss(x, A_n * w, mu_obs, sig_obs)
            if apply_coti and obs == 1 and k == 0:
                g *= coti_erf_factor(x, q_thr, sigma_thr)
            y += g
    return y


# ---------------------------------------------------------------------------
# MODEL 3  multigauss_ap  —  SYSU geometric afterpulse model
# ---------------------------------------------------------------------------

def model_multigauss_ap(x, n_peaks, mu1, gain, sigma_pe, sigma_base, amplitudes,
                        q_ap, alpha, n_ap=6,
                        apply_coti=False, q_thr=0.0, sigma_thr=1.0):
    """
    Multi-Gaussian + geometric intra-gate afterpulse (SYSU/TAO, Hanwen's model).

    For each n-PE peak:
      f_n(Q) = A_n · Σ_{i=0}^{n_ap} (1-nα)(nα)^i · G(Q; μ_n + i·Q_ap, σ_n)

    i=0 → main PE peak (no AP).
    i>0 → i-th AP sub-peak shifted by i·Q_ap; creates bumps BETWEEN integer PE peaks.

    Constraints
    -----------
    α < 1/n_peaks  (otherwise (1-nα) < 0; enforced by clamp).
    q_ap  ∈ (0, 0.95·Gain) — AP charge is less than full gain.

    Reference: Ziang Li, "Four Gaussian Fitting", slide 4, TAO group JAN 2026.
               Σ_{i=0}^{6} (1-nα)(nα)^i exp[−(Q−μ_n−iQ_ap)²/(2σ_n²)]
    """
    alpha = max(0.0, min(alpha, 0.99 / max(n_peaks, 1)))
    q_ap  = max(0.0, min(q_ap,  0.95 * abs(gain)))
    y     = np.zeros_like(x, dtype=float)

    for n in range(1, n_peaks + 1):
        A_n  = max(amplitudes[n-1], 0.0)
        mu_n = peak_mu(n, mu1, gain)
        s_n  = peak_sigma(n, sigma_pe, sigma_base)
        na   = n * alpha
        comp = np.zeros_like(x, dtype=float)
        for i in range(n_ap + 1):
            w_i = (1.0 - na) * (na**i)
            if w_i < 1e-12:
                break
            g = gauss(x, 1.0, mu_n + i * q_ap, s_n)
            if apply_coti and n == 1 and i == 0:
                g *= coti_erf_factor(x, q_thr, sigma_thr)
            comp += w_i * g
        y += A_n * comp
    return y


# ---------------------------------------------------------------------------
# MODEL 4  emg  —  Exponential Modified Gaussian
# ---------------------------------------------------------------------------

def emg_single(x, A, mu, sigma, tau):
    """
    Single EMG peak (area parametrisation).

      f(x) = A/(2τ) · exp[(μ−x)/τ + σ²/(2τ²)] · erfc[σ/(τ√2) − (x−μ)/(σ√2)]

    Derived from Gauss(μ,σ) convolved with one-sided exponential Exp(+1/τ) θ(t).
    This creates a right-side exponential tail at x > μ.

    Physical interpretation for SiPMs
    ----------------------------------
    The tail models the charge added by optical CT or fast intra-gate afterpulses
    that overlap within the integration window. The shape parameter τ captures:
      · p_ct ≈ τ / Gain     (single-level, small-p_ct approximation)
      · p_ct = 1 − exp(−τ/Gain)  (exact single-level)
    A shared τ across all peaks = global CT probability.

    Parameters
    ----------
    A   : peak area [counts · ADC]
    mu  : Gaussian centre
    sigma : Gaussian width
    tau   : exponential decay constant (τ → 0 recovers plain Gaussian)
    """
    tau   = max(abs(tau),   0.1)
    sigma = max(abs(sigma), 0.1)
    exp_arg  = np.clip((mu - x)/tau + sigma**2 / (2.0*tau**2), -500.0, 300.0)
    erfc_arg = sigma / (tau * math.sqrt(2.0)) - (x - mu) / (sigma * math.sqrt(2.0))
    return (A / (2.0*tau)) * np.exp(exp_arg) * erfc_arr(erfc_arg)


def model_emg(x, n_peaks, mu1, gain, sigma_pe, sigma_base, amplitudes, tau,
              apply_coti=False, q_thr=0.0, sigma_thr=1.0):
    """
    Multi-peak EMG with one shared exponential tail constant τ (global CT).

    The shared τ provides a physically global crosstalk scale across all peaks.
    amplitudes are AREAS (not heights); τ shifts probability from the peak centre
    toward the right tail.
    """
    y = np.zeros_like(x, dtype=float)
    for n in range(1, n_peaks + 1):
        A_n  = max(amplitudes[n-1], 0.0)
        mu_n = peak_mu(n, mu1, gain)
        s_n  = peak_sigma(n, sigma_pe, sigma_base)
        peak = emg_single(x, A_n, mu_n, s_n, tau)
        if apply_coti and n == 1:
            peak *= coti_erf_factor(x, q_thr, sigma_thr)
        y += peak
    return y


# ---------------------------------------------------------------------------
# MODEL 5  emg_ap  —  EMG + geometric afterpulse (combined)
# ---------------------------------------------------------------------------

def model_emg_ap(x, n_peaks, mu1, gain, sigma_pe, sigma_base, amplitudes,
                 tau, q_ap, alpha, n_ap=6,
                 apply_coti=False, q_thr=0.0, sigma_thr=1.0):
    """
    EMG main peaks + geometric afterpulse sub-peaks.

    Same afterpulse structure as multigauss_ap but each sub-peak uses an EMG
    shape instead of a plain Gaussian. The shared τ captures the smooth CT tail
    while Q_ap / α capture the discrete intra-gate afterpulse structure.
    Most complete model but also most parameter-rich.
    """
    alpha = max(0.0, min(alpha, 0.99 / max(n_peaks, 1)))
    q_ap  = max(0.0, min(q_ap,  0.95 * abs(gain)))
    y     = np.zeros_like(x, dtype=float)

    for n in range(1, n_peaks + 1):
        A_n  = max(amplitudes[n-1], 0.0)
        mu_n = peak_mu(n, mu1, gain)
        s_n  = peak_sigma(n, sigma_pe, sigma_base)
        na   = n * alpha
        comp = np.zeros_like(x, dtype=float)
        for i in range(n_ap + 1):
            w_i = (1.0 - na) * (na**i)
            if w_i < 1e-12:
                break
            e = emg_single(x, 1.0, mu_n + i * q_ap, s_n, tau)
            if apply_coti and n == 1 and i == 0:
                e *= coti_erf_factor(x, q_thr, sigma_thr)
            comp += w_i * e
        y += A_n * comp
    return y


# ---------------------------------------------------------------------------
# Cost functions
# ---------------------------------------------------------------------------

def chi2_poisson(y_obs, y_pred):
    """
    Poisson-weighted chi²:  Σ_i (y_obs_i − y_pred_i)² / max(y_obs_i, 1).
    Standard estimator for histogram fits where σ_i = sqrt(N_i).
    Converges to the unbinned NLL for large N.
    """
    w = 1.0 / np.maximum(y_obs, 1.0)
    return float(np.sum(w * (y_obs - y_pred)**2))


def chi2_ndf(chi2_val, n_data, n_params):
    """χ²/ndf  (returns -1 if ndf ≤ 0)."""
    ndf = n_data - n_params
    return chi2_val / ndf if ndf > 0 else -1.0


# ---------------------------------------------------------------------------
# Model parameter layout helpers
# ---------------------------------------------------------------------------

def build_param_vector(model_name, n_peaks, init):
    """
    Build (names, x0, bounds) from an 'init' dict.

    Required init keys: mu1, gain
    Optional init keys: sigma_pe, sigma_base, amplitudes (list),
                        tau, p_ct, q_ap, alpha
    """
    gain = float(init['gain'])
    mu1  = float(init['mu1'])
    sp   = float(init.get('sigma_pe',   gain * 0.15))
    sb   = float(init.get('sigma_base', gain * 0.05))

    names = ['mu1', 'gain', 'sigma_pe', 'sigma_base']
    x0    = [mu1, gain, sp, sb]
    bds   = [
        (max(mu1 * 0.3, 100.0), mu1 * 1.8),
        (gain * 0.35, gain * 2.2),
        (30.0,  gain * 0.9),
        (5.0,   gain * 0.4),
    ]

    amps = init.get('amplitudes', [10.0] * n_peaks)
    for k in range(n_peaks):
        # Floor at 1 so bounds are always well-defined
        a0 = max(float(amps[k]) if k < len(amps) else 10.0, 1.0)
        names.append(f'A{k+1}')
        x0.append(a0)
        # Tighter upper bound: ×10 instead of ×30 — prevents amplitude explosion
        # while still allowing for some underestimation in stage-1
        bds.append((max(a0 * 0.05, 0.5), max(a0 * 10.0, 50.0)))

    if model_name == 'multigauss_ct':
        p0 = float(init.get('p_ct', 0.05))
        names.append('p_ct');  x0.append(p0);  bds.append((0.001, 0.5))

    if model_name in ('multigauss_ap', 'emg_ap'):
        qap0   = float(init.get('q_ap',  gain * 0.25))
        alph0  = float(init.get('alpha', 0.02))
        names += ['q_ap', 'alpha']
        x0    += [qap0, alph0]
        bds   += [(30.0, 0.95 * gain), (1e-4, 0.6 / max(n_peaks, 1))]

    if model_name in ('emg', 'emg_ap'):
        tau0 = float(init.get('tau', gain * 0.08))
        names.append('tau');  x0.append(tau0);  bds.append((3.0, gain * 2.5))

    return names, np.array(x0, dtype=float), bds


def vec_to_dict(names, vec):
    """Map flat parameter array to dict."""
    return dict(zip(names, vec))


def eval_model(model_name, x, n_peaks, params):
    """
    Evaluate model_name at array x given a params dict.

    params must contain: mu1, gain, sigma_pe, sigma_base, A1..An
    plus model-specific keys (p_ct / q_ap+alpha / tau).
    """
    mu1   = params['mu1']
    gain  = params['gain']
    spe   = params['sigma_pe']
    sb    = params['sigma_base']
    amps  = [params[f'A{k+1}'] for k in range(n_peaks)]
    coti  = params.get('apply_coti', False)
    qt    = params.get('q_thr',    0.0)
    st    = params.get('sigma_thr', 1.0)

    if model_name == 'multigauss':
        return model_multigauss(x, n_peaks, mu1, gain, spe, sb, amps, coti, qt, st)
    if model_name == 'multigauss_ct':
        return model_multigauss_ct(x, n_peaks, mu1, gain, spe, sb, amps,
                                   params['p_ct'], apply_coti=coti, q_thr=qt, sigma_thr=st)
    if model_name == 'multigauss_ap':
        return model_multigauss_ap(x, n_peaks, mu1, gain, spe, sb, amps,
                                   params['q_ap'], params['alpha'],
                                   apply_coti=coti, q_thr=qt, sigma_thr=st)
    if model_name == 'emg':
        return model_emg(x, n_peaks, mu1, gain, spe, sb, amps, params['tau'],
                         coti, qt, st)
    if model_name == 'emg_ap':
        return model_emg_ap(x, n_peaks, mu1, gain, spe, sb, amps,
                            params['tau'], params['q_ap'], params['alpha'],
                            apply_coti=coti, q_thr=qt, sigma_thr=st)
    raise ValueError(f"Unknown model '{model_name}'")


# ---------------------------------------------------------------------------
# BFGS minimizer  (MIGRAD-equivalent, written from scratch)
# ---------------------------------------------------------------------------

def _grad_central(f, x, rel_eps=1e-3):
    """
    Gradient by central finite differences.
    Step size h_i = max(rel_eps·|x_i|, rel_eps) avoids vanishing steps for
    large-valued parameters such as ADC positions (5000–30000 range).
    """
    n = len(x)
    g = np.empty(n)
    for i in range(n):
        h   = max(rel_eps * abs(x[i]), rel_eps)
        xp  = x.copy(); xp[i] += h
        xm  = x.copy(); xm[i] -= h
        g[i] = (f(xp) - f(xm)) / (2.0 * h)
    return g


def _project(x, bounds):
    """Project x onto the box defined by bounds = [(lo,hi), ...]."""
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    return np.clip(x, lo, hi)


def bfgs_minimize(f, x0, bounds, gtol=1e-3, maxiter=400, grad_eps=1e-3):
    """
    BFGS minimisation with box constraints (MIGRAD-equivalent).

    Algorithm
    ---------
    1. Central-difference gradient with parameter-relative step.
    2. BFGS inverse-Hessian update (rank-2 Broyden formula).
    3. Armijo backtracking line search with steepest-descent fallback.
    4. Box constraint enforcement by projection.
    5. Convergence: scaled gradient norm ||g/scale||₂ < gtol.
    6. Covariance from numerical Hessian at minimum: Cov = ½ H⁻¹.

    Returns
    -------
    x_opt, cov, f_min, success, n_iter
    """
    n  = len(x0)
    x  = _project(np.array(x0, dtype=float), bounds)
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    H  = np.eye(n)     # inverse Hessian approximation
    fc = f(x)
    ok = False

    for k in range(maxiter):
        g = _grad_central(f, x, grad_eps)
        scale = np.maximum(np.abs(x), 1.0)
        if np.linalg.norm(g / scale) < gtol:
            ok = True
            break

        # BFGS search direction
        d = -H @ g
        # Null out components that push against active bounds
        for i in range(n):
            if d[i] < 0 and x[i] <= lo[i] + 1e-12: d[i] = 0.0
            if d[i] > 0 and x[i] >= hi[i] - 1e-12: d[i] = 0.0
        if np.linalg.norm(d) == 0:
            ok = True
            break

        # Armijo backtracking line search
        alpha_ls, c1 = 1.0, 1e-4
        gd = np.dot(g, d)
        for _ in range(50):
            xt = _project(x + alpha_ls * d, bounds)
            ft = f(xt)
            if ft <= fc + c1 * alpha_ls * abs(gd):
                break
            alpha_ls *= 0.5
        else:
            # Fall back to steepest descent with tiny step
            d_sd = -g
            alpha_ls = 1e-5 / (np.linalg.norm(d_sd) + 1e-30)
            xt = _project(x + alpha_ls * d_sd, bounds)
            ft = f(xt)

        s     = xt - x
        x     = xt
        fc    = ft
        g_new = _grad_central(f, x, grad_eps)
        y_v   = g_new - g
        sy    = float(np.dot(s, y_v))

        # BFGS rank-2 update (only if curvature condition sy > 0)
        if sy > 1e-10 * np.linalg.norm(s) * np.linalg.norm(y_v):
            rho = 1.0 / sy
            ImS = np.eye(n) - rho * np.outer(s, y_v)
            H   = ImS @ H @ ImS.T + rho * np.outer(s, s)
            H   = 0.5 * (H + H.T)   # symmetrize to prevent drift

    # ── Numerical Hessian at minimum → covariance Cov = ½ H⁻¹ ──────────────
    h_sc = np.maximum(np.abs(x) * 0.01, 1.0)
    Hmat = np.zeros((n, n))
    f0   = f(x)
    for i in range(n):
        hi_s = h_sc[i]
        ei   = np.zeros(n); ei[i] = hi_s
        Hmat[i, i] = (f(x + ei) - 2.0*f0 + f(x - ei)) / hi_s**2
        for j in range(i+1, n):
            hj = h_sc[j]; ej = np.zeros(n); ej[j] = hj
            Hmat[i, j] = (f(x+ei+ej) - f(x+ei) - f(x+ej) + f0) / (hi_s * hj)
            Hmat[j, i] = Hmat[i, j]
    Hmat += np.eye(n) * 1e-12 * max(1.0, float(np.max(np.abs(Hmat))))
    try:
        cov = 0.5 * np.linalg.inv(Hmat)
    except np.linalg.LinAlgError:
        cov = np.diag(np.full(n, np.inf))

    return x, cov, float(f(x)), ok, k + 1


# ---------------------------------------------------------------------------
# Weighted least-squares linear fit: μ_n = intercept + gain · n
# ---------------------------------------------------------------------------

def linear_fit_gain(peak_numbers, peak_means, peak_errors=None):
    """
    WLS fit μ_n = a + b·n  →  b = Gain, a = intercept (ADC offset at n=0).

    Returns
    -------
    gain, gain_err, intercept, intercept_err, R², chi²/dof
    """
    n  = len(peak_numbers)
    X  = np.column_stack([np.ones(n), np.array(peak_numbers, dtype=float)])
    Y  = np.array(peak_means, dtype=float)
    if peak_errors is not None and np.any(np.array(peak_errors, dtype=float) > 0):
        w = np.maximum(np.array(peak_errors, dtype=float)**2, 1e-10)
        W = np.diag(1.0 / w)
    else:
        W = np.eye(n)
    try:
        Cov_b = np.linalg.inv(X.T @ W @ X)
    except np.linalg.LinAlgError:
        return 0.0, np.inf, 0.0, np.inf, 0.0, -1.0

    beta    = Cov_b @ X.T @ W @ Y
    icept, gain = beta[0], beta[1]
    Y_pred  = X @ beta
    ss_res  = float(np.sum((Y - Y_pred)**2))
    ss_tot  = float(np.sum((Y - Y.mean())**2))
    r2      = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    c2      = float((Y - Y_pred) @ W @ (Y - Y_pred))
    dof     = n - 2
    c2dof   = c2 / dof if dof > 0 else -1.0
    return (gain, math.sqrt(max(Cov_b[1,1], 0.0)),
            icept, math.sqrt(max(Cov_b[0,0], 0.0)),
            r2, c2dof)


# ---------------------------------------------------------------------------
# Two-stage fitting
# ---------------------------------------------------------------------------

def _stage1_single_peak(x_data, y_data, pos, gain_est):
    """Fit single Gaussian to a narrow window around detected peak position."""
    hw   = 0.4 * gain_est
    mask = np.abs(x_data - pos) < hw
    # Bin height at peak position as a reliable amplitude estimate
    bin_height = max(float(y_data[np.argmin(np.abs(x_data - pos))]), 10.0)
    if np.sum(mask) < 4:
        return pos, gain_est * 0.12, bin_height
    xi   = x_data[mask]
    yi   = y_data[mask].astype(float)
    A0   = float(np.max(yi))
    mu0  = float(xi[np.argmax(yi)])
    s0   = gain_est * 0.12
    # Upper amplitude bound: 8× the bin height (not 8× the noisy A0)
    A_hi = max(A0 * 8.0, bin_height * 8.0, 50.0)
    bds1 = [(A0 * 0.05, A_hi), (mu0 - hw, mu0 + hw), (10.0, gain_est * 0.6)]
    x0_1 = np.array([A0, mu0, s0])
    w1   = 1.0 / np.maximum(yi, 1.0)

    def cost1(p):
        s = max(abs(p[2]), 1.0)
        pred = p[0] * np.exp(-0.5 * ((xi - p[1]) / s)**2)
        return float(np.sum(w1 * (yi - pred)**2))

    opt, _, _, _, _ = bfgs_minimize(cost1, x0_1, bds1, gtol=1e-3, maxiter=120)
    # Use max(fitted_amplitude, bin_height*0.5) to avoid near-zero amplitudes
    amp_out = float(max(opt[0], bin_height * 0.5, 1.0))
    return float(opt[1]), float(abs(opt[2])), amp_out


def stage1_fits(x_data, y_data, peak_positions, gain_est):
    """
    Stage-1: independent single-Gaussian fits for each detected peak.

    Returns (mus, sigmas, amps, gain_s1, mu1_s1)
    where gain_s1 and mu1_s1 are derived by linear regression on peak positions.
    """
    mus, sigs, amps = [], [], []
    for pos in peak_positions:
        mu, sig, amp = _stage1_single_peak(x_data, y_data, pos, gain_est)
        mus.append(mu); sigs.append(sig); amps.append(amp)

    n = len(mus)
    if n >= 2:
        ns = np.arange(1, n + 1, dtype=float)
        gain_s1, _, mu0_s1, _, _, _ = linear_fit_gain(ns, np.array(mus))
        mu1_s1 = mu0_s1 + gain_s1   # intercept is at n=0, so n=1 position
        if gain_s1 < gain_est * 0.35 or gain_s1 > gain_est * 2.8:
            gain_s1 = gain_est
            mu1_s1  = mus[0]
    else:
        gain_s1 = gain_est
        mu1_s1  = mus[0] if mus else gain_est

    return mus, sigs, amps, gain_s1, mu1_s1


def fit_channel(x_data, y_data, n_peaks, peak_positions, gain_est, model_name,
                apply_coti=False, gtol=1e-4, maxiter=450):
    """
    Two-stage channel fit for a given model.

    Stage 1: independent single-Gaussian fits → initial conditions.
    Stage 2: joint multi-peak model fit from Stage-1 values.

    Returns
    -------
    dict with keys:
      success, gain, gain_err, intercept, intercept_err,
      chi2_dof, r2_linear, n_peaks,
      param_names, popt, pcov, y_fit, extra
    """
    FAIL = dict(success=False, gain=0.0, gain_err=np.inf,
                intercept=0.0, intercept_err=np.inf,
                chi2_dof=-1.0, r2_linear=0.0, n_peaks=n_peaks,
                param_names=[], popt=None, pcov=None, y_fit=None, extra={})

    if len(y_data) < 5 or float(np.sum(y_data)) < 200:
        return FAIL

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    mus, sigs, amps, gain_s1, mu1_s1 = stage1_fits(
        x_data, y_data, peak_positions, gain_est)

    spe_s1  = max(float(np.median(sigs)) * 0.65, 30.0)
    sbase_s1 = max(float(np.median(sigs)) * 0.35, 5.0)

    # COTI threshold estimate: ~30% of 1PE peak position
    q_thr_est   = mu1_s1 * 0.30
    s_thr_est   = 200.0

    init = dict(
        mu1=mu1_s1, gain=gain_s1,
        sigma_pe=spe_s1, sigma_base=sbase_s1,
        amplitudes=amps,
        tau=gain_s1 * 0.08, p_ct=0.05,
        q_ap=gain_s1 * 0.25, alpha=0.02,
    )

    # ── Stage 2 ──────────────────────────────────────────────────────────────
    names, x0, bds = build_param_vector(model_name, n_peaks, init)
    weights = 1.0 / np.maximum(y_data, 1.0)

    def cost(p):
        try:
            par = vec_to_dict(names, p)
            par['apply_coti'] = apply_coti
            par['q_thr']      = q_thr_est
            par['sigma_thr']  = s_thr_est
            yp = eval_model(model_name, x_data, n_peaks, par)
            return float(np.sum(weights * (y_data - yp)**2))
        except Exception:
            return 1e15

    popt, pcov, f_min, ok, _ = bfgs_minimize(cost, x0, bds,
                                              gtol=gtol, maxiter=maxiter)
    if not ok and f_min > 1e14:
        return FAIL

    par_fit = vec_to_dict(names, popt)
    par_fit.update(apply_coti=apply_coti, q_thr=q_thr_est, sigma_thr=s_thr_est)
    y_fit   = eval_model(model_name, x_data, n_peaks, par_fit)

    chi2  = chi2_poisson(y_data, y_fit)
    c2ndf = chi2_ndf(chi2, len(x_data), len(popt))

    # ── Gain from linear fit on peak means ────────────────────────────────────
    # Use the stage-1 MEASURED peak positions (independent single-Gaussian
    # centres), NOT peak_mu(n, mu1_f, gain_f) which is μ_1+(n-1)·G by
    # construction and therefore always perfectly collinear → R²=1 regardless
    # of fit quality.  Stage-1 positions reflect the actual data scatter and
    # give a meaningful R² and gain uncertainty.
    errs   = np.sqrt(np.maximum(np.diag(pcov), 0.0))
    edict  = dict(zip(names, errs))

    ns     = np.arange(1, n_peaks + 1, dtype=float)
    # stage-1 positions are in `mus` (length = len(peak_positions) ≤ n_peaks)
    n_s1   = min(len(mus), n_peaks)
    ns_s1  = ns[:n_s1]
    pm_s1  = np.array(mus[:n_s1], dtype=float)
    # Propagate stage-1 peak-fit uncertainty: use sigma/sqrt(N) ≈ sigma_pe/sqrt(amp)
    # as a rough per-peak positional error; floor at 1 ADC so WLS is never degenerate.
    pe_s1  = np.array([max(sigs[k] / math.sqrt(max(amps[k], 1.0)), 1.0)
                       for k in range(n_s1)])

    gain_wls, gain_err, icept, icept_err, r2, lin_c2dof = linear_fit_gain(ns_s1, pm_s1, pe_s1)

    # ── Model-specific extra parameters ──────────────────────────────────────
    extra = {'sigma_pe': par_fit.get('sigma_pe', 0.0),
             'sigma_base': par_fit.get('sigma_base', 0.0)}
    if 'tau' in par_fit:
        t = par_fit['tau']
        extra.update(tau=t, tau_err=edict.get('tau', 0.0),
                     p_ct_emg=t/gain_wls if gain_wls > 0 else 0.0)
    if 'p_ct' in par_fit:
        extra.update(p_ct=par_fit['p_ct'], p_ct_err=edict.get('p_ct', 0.0))
    if 'q_ap' in par_fit:
        extra.update(q_ap=par_fit['q_ap'],
                     q_ap_rel=par_fit['q_ap']/gain_wls if gain_wls > 0 else 0.0,
                     alpha=par_fit['alpha'], alpha_err=edict.get('alpha', 0.0))

    return dict(
        success=True,
        gain=gain_wls, gain_err=gain_err,
        intercept=icept, intercept_err=icept_err,
        chi2_dof=c2ndf, r2_linear=r2,
        linear_chi2_dof=lin_c2dof,
        n_peaks=n_peaks, param_names=names,
        popt=popt, pcov=pcov, y_fit=y_fit,
        extra=extra,
        _par_fit=par_fit,   # full dict for plotting
        _x_data=x_data,     # store for residual plots
    )
