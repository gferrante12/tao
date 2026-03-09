#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import Sniper
import RootIOSvc
import BufferMemMgr

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run Tao Calibration Package.')
    parser.add_argument("--evtmax", type=int, default=-1, help='events to be processed')
    parser.add_argument("--seed", type=int, default=42, help='seed')
    parser.add_argument("--input", default="elesim.root", nargs='+', help="specify input filename")
    parser.add_argument("--inputList", default="", help="specify input file list")
    parser.add_argument("--inputcalibpar", default="", help="Input SiPM Calibration parameter wihtout using Database")
    parser.add_argument("--output", default="user-ana-output.root", help="specify output filename")
    parser.add_argument("--dbconf", default=None, help="Database Configuration (YAML format)")
    parser.add_argument("--EnableUseCondDB", dest="EnableUseCondDB", action= 'store_true', help='Enable Use CondDB')
    parser.add_argument("--DisableUseCondDB", dest="EnableUseCondDB", action='store_false')
    parser.add_argument('--GTag', type=str, default="T25.6.3", help='Enter your name')
    parser.add_argument('--Tag', type=str, default="Calib.SiPMCalibAlg.Para", help='Enter your name')
    parser.add_argument('--IOV', type=int, default=1764720000, help='Enter your name')
    parser.add_argument("--loglevel", default="Info",
                                      choices=["Test", "Debug", "Info", "Warn", "Error", "Fatal"],
                                      help="Set the Log Level")
    parser.add_argument("--EnableDynamicBaseline", dest="EnableDynamicBaseline", action="store_true",help="Enable dynamic baseline in calibration")
    parser.set_defaults(EnableUseCondDB=False)
    parser.set_defaults(EnableDynamicBaseline=False)
    return parser

DATA_LOG_MAP = {"Test":0, "Debug":2, "Info":3, "Warn":4, "Error":5, "Fatal":6}

if __name__ == "__main__":
    
    #t0= time.clock()

    parser = get_parser()
    args = parser.parse_args()
    print (args)

    task = Sniper.Task("task")
    task.setEvtMax(args.evtmax)
    task.setLogLevel(DATA_LOG_MAP[args.loglevel])
    #task.setLogLevel(0)

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

    # = random svc =
    import RandomSvc
    rndm = task.createSvc("RandomSvc")
    rndm.property("Seed").set(args.seed)

    # = rootio =
    import RootIOSvc
    if not args.input and not args.inputList:
        print("Please provide an input file for analysis")
        exit(-1)
    inputs = []
    if args.inputList:
        import sys
        import os.path
        if not os.path.exists(args.inputList):
            sys.exit(-1)
        with open(args.inputList) as f:
            for line in f:
                line = line.strip()
                inputs.append(line)
    else:
        inputs.extend(args.input)
    ris = task.createSvc("RootInputSvc/InputSvc")
    ris.property("InputFile").set(inputs)
    ros = task.createSvc("RootOutputSvc/OutputSvc")
    # ros.property("OutputStreams").set({"/Event/Calib": args.output})
    ros.property("OutputStreams").set({
        "/Event/Calib": args.output,
        "/Event/TvtTrig" : args.output,
        "/Event/TvtElec" : args.output,
        "/Event/WtTrig" : args.output,
        "/Event/WtElec" : args.output,
        })
    # = BufferMemMgr =
    import BufferMemMgr
    bufMgr = task.createSvc("BufferMemMgr")
    bufMgr.property("TimeWindow").set([0, 0])

    import CalibSvc
    calibsvc = task.createSvc("CalibSvc")
    calibsvc.property("EnableCondDB").set(args.EnableUseCondDB)
    calibsvc.property("Tag").set(args.Tag)
    calibsvc.property("IOV").set(args.IOV)
    calibsvc.property("inputcalibpar").set(args.inputcalibpar)
    calibsvc.property("UseDynamicBaseline").set(args.EnableDynamicBaseline)
  

    # = root writer =
    #import RootWriter
    #rootwriter = task.createSvc("RootWriter")
    #rootwriter.property("Output").set({"ANASIMEVT": args.output})

    

    # = ana detsim =
    Sniper.loadDll("libCalibAlg.so")
    calibalg = task.createAlg("CalibAlg")
    

    task.show()
    task.run()
    
    #t1 = time.clock() - t0
    #print "==================================="
    #print "run.py INFO: time elapsed: ", "{:10.4f}".format(t1), "s =", "{:10.4f}".format(t1/60), "min"
