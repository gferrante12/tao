# Reconstruction with QADC and 1st hit time of SiPM
import numpy as np
import h5py
from matplotlib import pyplot as plt
from scipy import optimize
from tqdm import trange
from calculate import CalculatePE
import argparse

from tweedie import tweedie_pdf,tweedie_dlambda

psr = argparse.ArgumentParser()
psr.add_argument("-i", type=str, help="Input detsim h5 file")
psr.add_argument("--ie", type=str, help="Input elecsim h5 file")
psr.add_argument("-c", type=str, default="./probe_coef.h5", help="Probe coefficients h5 file")
psr.add_argument("--cs", type=str, default="./probe_mc.h5", help="Probe scatter h5 file")
psr.add_argument("-g", type=str, default="./sipm_pos.csv", help="SiPM position csv file")
psr.add_argument("--en", type=int, default=2000, help="Event number you need")
psr.add_argument("-o", type=str, help="Output h5 file")
args = psr.parse_args()

r_max = 900
r_sipm = 935
num_sipm = 4024
mu = 2599.99
p = 1.001455
phi_o = 3190.186
tweedie_npe = 0.60722
dnr = 20 * (6 * 12) * 16 * 2 * 1e-9
t_min = -300
t_max = 700
t_len = t_max - t_min
E_k1 = np.sqrt(0.511**2 + 1**2) - 0.511

with h5py.File(args.i) as f:
    track = f["SimEvent/Track"][:]
    cdhit = f["SimEvent/CDHit"][:]

event_num = len(track)

if event_num > args.en:
    event_num = args.en

geo = np.genfromtxt(
      args.g,
      autostrip=True,
      dtype=[("Id", np.int_), ("theta", np.float_), ("phi", np.float_)],
  )
geo["theta"] /= 180 / np.pi
geo["phi"] /= 180 / np.pi
geo_card = np.zeros((len(geo), 3))
geo_card[:, 0] = np.sin(geo["theta"]) * np.cos(geo["phi"])
geo_card[:, 1] = np.sin(geo["theta"]) * np.sin(geo["phi"])
geo_card[:, 2] = np.cos(geo["theta"])

with h5py.File(args.c) as f:
    tmin = f["coeff"].attrs["t_min"]
    tmax = f["coeff"].attrs["t_max"]
    tbins = tmax - tmin
    E_mean = f["coeff"].attrs["E_mean"]
    tau = f["coeff"].attrs["tau"]

with h5py.File(args.cs) as f:
    coef_R = f["R"][:]
    coef_R_int = f["R_int"][:]
    coef_R_int_reverse = f["R_int_reverse"][:]

with h5py.File(args.ie) as f:
    channel = f['ElecEvent/Channel'][:]
    evt_num = len(np.unique(channel['id']))
    ADC_channel =  np.zeros((num_sipm*2, evt_num))
    for item in channel:
        ADC_channel[item["ChannelID"]][item["id"]] += item['ADC']
    ADC_SiPM = ADC_channel[::2, :] + ADC_channel[1::2, :]

def angle_rel(vertex):
    cos_theta = np.sum(geo_card * vertex, axis=1) \
        / np.linalg.norm(geo_card, axis=1) \
        / np.linalg.norm(vertex)
    return np.arccos(np.clip(cos_theta, -1, 1))

def index_interp(T):
    t_lc = (T >= 0)
    t_uc = (T < tbins)
    sel_t = t_lc & t_uc
    Ts = T / tbins
    T_float = Ts[sel_t] * (len(coef_R) - 1)
    T_frac, T_int = np.modf(T_float)
    T_int = np.int_(T_int)
    return t_lc, t_uc, T_int, T_frac, sel_t

def T_interp(coef_list, T_index_int, T_index_frac):
    return (coef_list[T_index_int + 1] - coef_list[T_index_int]) * T_index_frac\
            + coef_list[T_index_int]

def mlogL_Q_fht(x, qadc, fht):
    vertex = x[:3]
    t = x[3]
    r_rel = np.linalg.norm(vertex) / r_max
    theta_rel = angle_rel(vertex)
    expect_pe_eval, _ = CalculatePE(r_rel, theta_rel, E_mean=E_mean, tau=tau)

    sel = (qadc != 0) & (fht != 99999)

    E = qadc.sum() / ((expect_pe_eval + dnr * t_len).sum() / (tweedie_npe + dnr * t_len) * mu) * E_mean

    expect_pe, dist = CalculatePE(r_rel, theta_rel, E_mean=E, tau=tau)
    flight_time = dist * 1 / 0.3 * 1.57

    mlogL = 0
    mlogL += np.sum(expect_pe[~sel] + dnr*t_len)

    To = fht - t - flight_time

    t_lc, t_uc, T_int, T_frac, sel_t = index_interp(To)

    T_interp_R = np.zeros(len(fht))
    T_interp_R_int = np.zeros(len(fht))
    T_interp_R_int_reverse = np.zeros(len(fht))

    T_interp_R[sel_t] = T_interp(coef_R, T_int, T_frac)
    T_interp_R_int[sel_t] = T_interp(coef_R_int, T_int, T_frac)
    T_interp_R_int_reverse[sel_t] = T_interp(coef_R_int_reverse, T_int, T_frac)

    T_interp_R[~t_lc] = coef_R[0]
    T_interp_R[~t_uc] = coef_R[-1]
    T_interp_R_int[~t_lc] = coef_R_int[0]
    T_interp_R_int[~t_uc] = coef_R_int[-1]
    T_interp_R_int_reverse[~t_lc] = coef_R_int_reverse[0]
    T_interp_R_int_reverse[~t_uc] = coef_R_int_reverse[-1]

    mlogL += np.sum(expect_pe[sel] * T_interp_R_int[sel] + dnr * (fht[sel] - t_min))
    mlogL -= np.sum(np.log(expect_pe[sel] * T_interp_R[sel] + dnr))

    lambda_pois = expect_pe[sel] * T_interp_R_int_reverse[sel] + dnr * (t_max - fht[sel])
    mu0 = lambda_pois / (tweedie_npe + dnr * t_len) * mu
    phi = 1 / lambda_pois * mu0**(2 - p) / (2 - p)

    sum1 = tweedie_pdf(qadc[sel], p, mu0, phi) + tweedie_dlambda(qadc[sel], p, mu0, phi)
    mlogL -= np.sum(np.log(sum1))

    if (np.linalg.norm(vertex) > r_max):
        mlogL += 1e40 * np.tanh(np.linalg.norm(vertex) - r_max)

    return mlogL

res = np.zeros((event_num, 5))

for evt_id in trange(event_num):
    cdhit_sel = cdhit[cdhit["EventID"] == evt_id]
    first_hit_time = np.ones(num_sipm) * 99999
    for item in cdhit_sel:
        if item["HitTime"] < first_hit_time[item["SipmID"]]:
            first_hit_time[item["SipmID"]] = item["HitTime"]
    adc_sipm = ADC_SiPM[:, evt_id]

    x_bary, y_bary, z_bary = np.einsum("i,ij->j", adc_sipm, geo_card) \
            / np.sum(adc_sipm) * 1.5 * r_sipm
    t_init = 1
    x1 = optimize.minimize(mlogL_Q_fht, x0=(x_bary, y_bary, z_bary, t_init),
            args=(adc_sipm, first_hit_time), method="Powell")

    res[evt_id][0:4] = x1.x
    r_rel_tmp = np.linalg.norm(res[evt_id][0:3]) / r_max
    theta_rel_tmp = angle_rel(res[evt_id][0:3])
    expect_pe_eval_tmp, _ = CalculatePE(r_rel_tmp, theta_rel_tmp, E_mean=E_mean, tau=tau)
    res[evt_id][4] = adc_sipm.sum() / ((expect_pe_eval_tmp + dnr * t_len).sum() /
            (tweedie_npe + dnr * t_len) * mu) * E_k1

with h5py.File(args.o, 'w') as f:
    f["rec_res"] = res
