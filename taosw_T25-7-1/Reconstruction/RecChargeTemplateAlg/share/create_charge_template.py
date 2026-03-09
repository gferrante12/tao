import argparse
from utils import ElecSimData, DetSimData
from utils import ReadoutChannelGeom
import numpy as np
import ROOT
from tqdm import tqdm
import glob

def get_opts():

    parser = argparse.ArgumentParser()
    parser.add_argument("--close_corpd_check", action = "store_true")
    parser.add_argument("--det_sim_files", nargs = "+", help = "Detector simulation input file lists")
    parser.add_argument("--elec_sim_files", nargs = "+", help = "Electronics simulation input file lists")
    parser.add_argument("--template_radius", type = int, default = 0, help = "radius of charge template")
    parser.add_argument("--output", default = "output.root", help = "output file path")
    return parser.parse_args()

def create_charge_template():

    opt = get_opts()
    print(opt)

    # check the det_sim_file and elec_sim_files corresponding
    # there's no variable to give the corresponding information,
    # so we only compare the file name and the number of events.
    det_sim_files = []
    for item in opt.det_sim_files:
        det_sim_files += glob.glob(item)
    elec_sim_files = []
    for item in opt.elec_sim_files:
        elec_sim_files += glob.glob(item)
    matched_detsim_files = []
    matched_elecsim_files = []
    if not opt.close_corpd_check:
        for dsf, esf in zip(det_sim_files, elec_sim_files):
            assert dsf.strip().split("/")[-1] == esf.strip().split("/")[-1]
            tmp_det = DetSimData([dsf])
            tmp_elec = ElecSimData([esf])
            if tmp_det.GetEntries() == tmp_elec.GetEntries():
                matched_detsim_files.append(dsf)
                matched_elecsim_files.append(esf)
            del tmp_det
            del tmp_elec
    print(matched_detsim_files)
    print(matched_elecsim_files)

    det_sim = DetSimData(matched_detsim_files)
    elec_sim = ElecSimData(matched_elecsim_files)
    channel_geom = ReadoutChannelGeom()
    if det_sim.GetEntries() != elec_sim.GetEntries():
        print(f"Warning : {det_sim.GetEntries()} events in detsim, {elec_sim.GetEntries()} events in elecsim")
        return

    # generate template hist
    ctemp = ROOT.TH1F(f"r_{int(opt.template_radius)}", f"r_{int(opt.template_radius)}", 360, 0, 180)
    num_counted = [0] * 360
    for eid in tqdm(range(det_sim.GetEntries())):

        det_evt = det_sim.GetEvent(eid)
        elec_evt = elec_sim.GetEvent(eid)
        edep_pos = np.array([det_evt.GdLSEdepX(), det_evt.GdLSEdepY(), det_evt.GdLSEdepZ()])
        edep_radius = np.sqrt(np.sum(edep_pos * edep_pos))
        if abs(edep_radius - opt.template_radius) > 5:
            continue

        channels = elec_evt.GetElecChannels()
        angles = [
            np.arccos(np.sum(edep_pos * channel_geom.get_channel_info(cid, "pos")) / \
                    (channel_geom.get_channel_info(cid, "radius") * edep_radius)) * 180 / np.pi for cid in range(channel_geom.get_channel_num())
                ]
        adcs = [-1 * channel_geom.get_channel_info(0, "dark_noise")] * channel_geom.get_channel_num()
        for channel in channels:
            cid = channel.getChannelID()
            adc = np.sum(list(channel.getADCs()))
            adcs[cid] += adc
        total_adc = np.sum(adcs)
        for adc, angle in zip(adcs, angles):
            bin_idx = ctemp.Fill(angle, adc/total_adc)
            num_counted[bin_idx - 1] += 1

    for i in range(360):
        if num_counted[i] < 1:
            continue
        adc = ctemp.GetBinContent(i + 1)
        ctemp.SetBinContent(i + 1, adc / num_counted[i])
        ctemp.SetBinError(i + 1, np.sqrt(adc / num_counted[i])/num_counted[i])

    ctemp.SaveAs(opt.output)

if __name__ == "__main__":
    create_charge_template()
