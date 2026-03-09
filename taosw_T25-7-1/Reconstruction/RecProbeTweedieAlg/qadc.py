import numpy as np
import h5py
from scipy import optimize
from calculate import CalculatePE
from tqdm import trange
from tweedie import tweedie_pdf
import argparse

psr = argparse.ArgumentParser()
psr.add_argument("-i", type=str, help="Input elecsim h5 file")
psr.add_argument("-o", type=str, help="Output h5 file")
psr.add_argument("--en", type=int, default=2000, help="event number we need")
psr.add_argument("-c", type=str, default="./probe_coef.h5", help="Probe coefficients h5 file")
psr.add_argument("-g", type=str, default="./sipm_pos.csv", help="SiPM position csv file")
args = psr.parse_args()

r_max = 900
r_sipm = 935
num_sipm = 4024
mu = 2599.99
p = 1.001455
phi = 3190.186
tweedie_npe = 0.60722
dn_rate = 20 * (6 * 12) * 16 * 2
t_min = -300
t_max = 700
dn_pe = dn_rate * (t_max - t_min) * 1e-9
E_k1 = np.sqrt(0.511**2 + 1**2) - 0.511

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

n_sipm = len(geo_card)

with h5py.File(args.c) as f:
    E_mean = f["coeff"].attrs["E_mean"]
    tau = f["coeff"].attrs["tau"]

with h5py.File(args.i) as f:
    channel = f['ElecEvent/Channel'][:]
    event_num = len(np.unique(channel['id']))
    ADC_channel =  np.zeros((num_sipm*2, event_num))
    for item in channel:
        ADC_channel[item["ChannelID"]][item["id"]] += item['ADC']
    ADC_SiPM = ADC_channel[::2, :] + ADC_channel[1::2, :]

if event_num > args.en:
    event_num = args.en

def angle_rel(vertex):
    cos_theta = np.sum(geo_card * vertex, axis=1) \
        / np.linalg.norm(geo_card, axis=1) \
        / np.linalg.norm(vertex)
    return np.arccos(np.clip(cos_theta, -1, 1))

def mlogL_qadc(x, adc_sipm):
    vertex = x[:3]
    r_rel = np.linalg.norm(vertex) / r_max
    theta_rel = angle_rel(vertex)

    expect_pe_eval, _ = CalculatePE(r_rel, theta_rel, E_mean=E_mean, tau=tau)
    E = adc_sipm.sum() / ((expect_pe_eval + dn_pe).sum() / (tweedie_npe + dn_pe) * mu) * E_mean

    expect_pe, _ = CalculatePE(r_rel, theta_rel, E_mean=E, tau=tau)

    mL = - np.sum(np.log(tweedie_pdf(adc_sipm, p=p, mu=(expect_pe+dn_pe) /
        (tweedie_npe+dn_pe) * mu, phi=phi)))

    if (np.linalg.norm(vertex) > r_max):
        mL += np.tanh(np.linalg.norm(vertex) - r_max) * 1e40

    return mL


res = np.zeros((event_num, 4))

for evt_id in trange(event_num):
    adc_sipm = ADC_SiPM[:, evt_id]
    x_bary, y_bary, z_bary = np.einsum("i,ij->j", adc_sipm, geo_card) \
            / np.sum(adc_sipm) * 1.5 * r_sipm
    vertex_bary = [x_bary, y_bary, z_bary]
    x1 = optimize.minimize(mlogL_qadc, x0=(x_bary, y_bary, z_bary),
            args=(adc_sipm), method="Powell")

    res[evt_id][0:3] = x1.x

    r_rel_tmp = np.linalg.norm(res[evt_id][0:3]) / r_max
    theta_rel_tmp = angle_rel(res[evt_id][0:3])
    expect_pe_eval_tmp, _ = CalculatePE(r_rel_tmp, theta_rel_tmp, E_mean=E_mean, tau=tau)
    res[evt_id][3] = adc_sipm.sum() / ((expect_pe_eval_tmp +
        dn_pe).sum()/(tweedie_npe + dn_pe) * mu) * E_k1

with h5py.File(args.o, 'w') as f:
    f["rec_res"] = res
