import os
import Sniper
import RootIOSvc
import BufferMemMgr
import time

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run Tao Elec2Rec Package.')
    ##Common
    parser.add_argument("--evtmax", type=int, default=-1, help='events to be processed')
    parser.add_argument("--seed", type=int, default=42, help='seed')
    parser.add_argument("--input", default="elesim.root", nargs='+', help="specify input filename")
    parser.add_argument("--inputList", default="", help="specify input file list")
    parser.add_argument("--inputcalibpar", default="", help="Input SiPM Calibration parameter wihtout using Database")
    parser.add_argument("--output", default="user-ana-output.root", help="specify output filename")
    parser.add_argument("--loglevel", default="Info",
                                      choices=["Test", "Debug", "Info", "Warn", "Error", "Fatal"],
                                      help="Set the Log Level")
    ##CalibAlg
    parser.add_argument("--dbconf", default=None, help="Database Configuration (YAML format)")
    parser.add_argument("--EnableUseCondDB", dest="EnableUseCondDB", action= 'store_true', help='Enable Use CondDB')
    parser.add_argument("--DisableUseCondDB", dest="EnableUseCondDB", action='store_false')
    parser.add_argument('--GTag', type=str, default="T25.6.3", help='Enter your name')
    parser.add_argument('--Tag', type=str, default="Calib.SiPMCalibAlg.Para", help='Enter your name')
    parser.add_argument('--IOV', type=int, default=1764720000, help='Enter your name')
    parser.add_argument("--EnableDynamicBaseline", dest="EnableDynamicBaseline", action="store_true",help="Enable dynamic baseline in calibration")
    parser.set_defaults(EnableUseCondDB=True)
    parser.set_defaults(EnableDynamicBaseline=False)

    ##ChargeCenterRec
    parser.add_argument("--user-output", default="None", help="specify output filename")
    parser.add_argument("--algorithm", default="ChargeCenterRec", help="specify the analysis algorithm")
    parser.add_argument("--isRealData", type=str, choices=['true', 'false'], default='true', help="specify if the input data is real data (true/false)")
    parser.add_argument("--input_ElecFile", default="None", help="specify ElecSim input filename")
    parser.add_argument("--isOpeningsCorrection", type=str, choices=['true', 'false'], default='false', help="Specify whether to apply the openings correction (true/false)")
    parser.add_argument("--isDarkNoiseCorrection",type=str, choices=['true', 'false'], default='false', help="Specify whether to apply the dark noise correction (true/false)")
    parser.add_argument("--CurveCorrectionPattern",type=str, choices=["multicurve", "AllCalibcurve", "CLScurve", "ACUcurve", "None","Test","Test01","Test02R","Test02RSim","Test02","Test03","Test04","Test04RSim"], default="Test02R", help="Select the appropriate curve correction mode")
    parser.add_argument("--minTDC",type=float, default=200, help= "TDC windows start.")
    parser.add_argument("--maxTDC",type=float, default=450, help= "TDC windows end.")
    parser.add_argument("--BadChannelIDFile", default="", help="specify BadChannelID filename")
    parser.add_argument("--nonUniformMapFile", default="", help="specify nonUniformMap filename")
    parser.add_argument("--CurveParamsFile", default="", help="specify CurveParams filename")
    parser.add_argument("--EnergyScaleFactor", type=float, nargs=2, default=[5894.69,5933], help="specify Energy Scale Factor")
    parser.add_argument("--isEnergyCorrection",type=str, choices=['true', 'false'], default='true', help="Specify whether to apply the energy correction (true/false)")
    return parser

DATA_LOG_MAP = {"Test":0, "Debug":2, "Info":3, "Warn":4, "Error":5, "Fatal":6}

if __name__ == "__main__":

    t0= time.time()

    parser = get_parser()
    args = parser.parse_args()
    if args.inputcalibpar not in ["", None]:
        print("[INFO] inputcalibpar is provided, CondDB is disabled automatically.")
        args.EnableUseCondDB = False
    print (args)

    task = Sniper.Task("task")
    task.setEvtMax(args.evtmax)
    task.setLogLevel(DATA_LOG_MAP[args.loglevel])


    import DBISvc

    dbconf = args.dbconf
    if dbconf is None:
        # set to DBISVCROOT/share/dbi.yaml
        dbconf = os.environ.get("CALIBALGROOT")
    if dbconf is None:
        print("ERROR: dbconf is not set. ")
        sys.exit(-1)
    dbconf = os.path.join(dbconf, "share", "dbi.yaml")

    if not os.path.exists(dbconf):
        print("ERROR: dbconf '%s' does not exist. "%dbconf)
        sys.exit(-1)

    # Load the conf
    def load_config(db_config_file):
        import yaml
        with open(db_config_file) as f:
            return yaml.safe_load(f)

    db_config = load_config(dbconf)

    connections = db_config.get('connections')
    clients = db_config.get('clients')
    schemas = db_config.get('schemas')
    dbisvc = Sniper.create("SharedElem<DBISvc>/DBISvc")
    dbisvc.property("Connections").set(connections)
    dbisvc.property("Clients").set(clients)
    dbisvc.property("Schemas").set(schemas)
    task.addSvc(dbisvc)

    import CondDB
    conddbsvc = Sniper.create("SharedElem<CondDBSvc>/CondDBSvc")
    conddbsvc.property("RepoTypes").set({
        #    "local": "LocalFSRepo",
        # "frontier": "Frontier"
        "dbi": "DBI"
    })
    conddbsvc.property("RepoURIs").set({
        #    "local": os.path.join("dummy-repo"),
        # "frontier": "http://junodb1.ihep.ac.cn:8080/Frontier",
        "dbi": "dbi://conddb" # configured by DBISvc
    })
    conddbsvc.property("GlobalTag").set(
        args.GTag
    )
    task.addSvc(conddbsvc)


     # = BufferMemMgr =
    import BufferMemMgr
    bufMgr = task.createSvc("BufferMemMgr")
    bufMgr.property("TimeWindow").set([0, 0])


    # = random svc =
    import RandomSvc
    rndm = task.createSvc("RandomSvc")
    rndm.property("Seed").set(args.seed)

    import RootWriter
    ###
    if args.user_output != "None":
        rootwriter = task.createSvc("RootWriter")
        rootwriter.property("Output").set({"RECEVT": args.user_output})
        print("args.user_output: ", args.user_output)
    else:
        print("args.user_output is 'None', skip RootWriter and RootOutputSvc creation")

    import RootIOSvc
    if not args.input:
        print("Please provide an input file for analysis") 
        exit(-1)
    ris = task.createSvc("RootInputSvc/InputSvc")
    ris.property("InputFile").set(args.input)
    ros = task.createSvc("RootOutputSvc/OutputSvc")
    ros.property("OutputStreams").set({
        "/Event/Calib": args.output,
        "/Event/Rec/ChargeCenterAlg" : args.output,
        })

    import CalibSvc
    calibsvc = task.createSvc("CalibSvc")
    calibsvc.property("EnableCondDB").set(args.EnableUseCondDB)
    calibsvc.property("Tag").set(args.Tag)
    calibsvc.property("IOV").set(args.IOV)
    calibsvc.property("inputcalibpar").set(args.inputcalibpar)
    calibsvc.property("UseDynamicBaseline").set(args.EnableDynamicBaseline)
    
    ##CCRec
    # = ana CCRec =
    Sniper.loadDll("libRecChargeCenterAlg.so")
    CCRecAlg = task.createAlg(args.algorithm)
    CCRecAlg.property("input_ElecFile").set(args.input_ElecFile)
    CCRecAlg.property("CurveCorrectionPattern").set(args.CurveCorrectionPattern)
    CCRecAlg.property("BadChannelIDFile").set(args.BadChannelIDFile)
    CCRecAlg.property("nonUniformMapFile").set(args.nonUniformMapFile)
    CCRecAlg.property("CurveParamsFile").set(args.CurveParamsFile)
    CCRecAlg.property("minTDC").set(float(args.minTDC))
    CCRecAlg.property("maxTDC").set(float(args.maxTDC))
    #
    is_real_data = args.isRealData.lower() == 'true'
    CCRecAlg.property("isRealData").set(is_real_data)
    #
    is_Openings_Correction = args.isOpeningsCorrection == 'true'
    CCRecAlg.property("isOpeningsCorrection").set(is_Openings_Correction)
    #
    is_DarkNoise_Correction = args.isDarkNoiseCorrection == 'true'
    CCRecAlg.property("isDarkNoiseCorrection").set(is_DarkNoise_Correction)
    #
    EnergyScaleFactor = args.EnergyScaleFactor
    CCRecAlg.property("EnergyScaleFactor").set(EnergyScaleFactor)
    #
    is_Energy_Correction = args.isEnergyCorrection == 'true'
    CCRecAlg.property("isEnergyCorrection").set(is_Energy_Correction)

    task.show()
    task.run()

