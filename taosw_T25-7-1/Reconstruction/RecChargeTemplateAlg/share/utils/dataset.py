import ROOT
ROOT.gSystem.Load("libTAOEDMUtil.so")
ROOT.gSystem.Load("libElecEvent.so")
ROOT.gSystem.Load("libSimEvent.so")

class ObjectData:

    def __init__(self,
            file_list = [],
            tree_path = ""
            ):

        self.file_list = file_list
        self.tree_path = tree_path
        self.events = None
        self.initialization()

    def initialization(self):
        self.events = ROOT.TChain(self.tree_path)
        for f in self.file_list:
            self.events.Add(f)
        return True

    def GetEntries(self):
        return self.events.GetEntries()

    def GetEvent(self, idx):
        pass

class ElecSimData(ObjectData):

    def __init__(self, file_list = [], tree_path = "/Event/Elec/CdElecEvt"):
        super().__init__(file_list, tree_path)

    def GetEvent(self, idx):
        self.events.GetEntry(idx)
        return self.events.CdElecEvt

class DetSimData(ObjectData):

    def __init__(self, file_list = [], tree_path = "/Event/Sim/SimEvent"):
        super().__init__(file_list, tree_path)

    def GetEvent(self, idx):
        self.events.GetEntry(idx)
        return self.events.SimEvent

if __name__ == "__main__":

    # test ...
    pass
