import pandas as pd
import numpy as np
import os


class ReadoutChannelGeom:

    def __init__(self, geom_csv = None):

        if geom_csv is None:
            csv_path = os.path.join(os.getenv("TAOSIMROOT"), "xml/sipm_pos.csv")
            self.geom_csv = csv_path
        else:
            self.geom_csv = geom_csv
        self.radius = 939.5   # mm
        self.channel_area = 50.71*50.71/2 # mm^2
        self.dark_noise_rate = 20 # Hz/mm^2
        self.readout_window = 1000 # ns
        self.readout_channels = {};
        self.initialize()

    def initialize(self):

        f = open(self.geom_csv, "r")
        lines = f.readlines()
        for line in lines:
            values = line.strip().split()
            c  = {
                 "radius" : self.radius,
                 "theta"  : np.pi * float(values[1]) / 180,
                 "phi"    : np.pi * float(values[2]) / 180,
                 "dark_noise" : self.channel_area * self.dark_noise_rate * self.readout_window * 1.e-9
                 }
            c["pos"] = np.array([
                c["radius"] * np.sin(c["theta"]) * np.cos(c["phi"]),
                c["radius"] * np.sin(c["theta"]) * np.sin(c["phi"]),
                c["radius"] * np.cos(c["theta"])
                ])
            self.readout_channels[int(values[0]) * 2] = c
            self.readout_channels[int(values[0]) * 2 + 1] = c

    def get_channel_num(self):
        return len(self.readout_channels)

    def get_channel_info(self, idx, name):
        if idx not in self.readout_channels:
            return None
        item = self.readout_channels[idx]
        if name not in item:
            return None
        return item[name]


if __name__ == "__main__":
    channels = ReadoutChannelGeom()
    pos = channels.get_channel_info(8047, "pos")
