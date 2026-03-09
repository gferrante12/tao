#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author: lintao

import time
import Sniper

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run Tao SiPM Calibration Algorithm.')
    parser.add_argument("--evtmax", type=int, default=-1, help='events to be processed')
    parser.add_argument("--seed", type=int, default=42, help='seed')
    parser.add_argument("--input", default="elesim.root", nargs='+', help="input filename")
    parser.add_argument("--inputList", default="", help="input file list")
    parser.add_argument("--output", default="cal_par.root", help="output result filename")
    parser.add_argument("--outgainfile", default="outgain.root", help="output gain fit file")
    parser.add_argument("--outgainflag", type=int, default=-1, help='output gain fit file flag')
    parser.add_argument("--outtimefile", default="outtimeoffset.root", help="output timeoffset fit file")
    parser.add_argument("--outtimeflag", type=int, default=-1, help='output timeoffset fit file flag')
    parser.add_argument("--outinctfile", default="outinct.root", help="output internal crosstalk fit file")
    parser.add_argument("--outinctflag", type=int, default=-1, help='output internal crosstalk fit file flag')
    parser.add_argument("--inctflag", type=int, default=1, help='internal crosstalk calibration flag')
    parser.add_argument("--dcrflag", type=int, default=1, help='dark count rate calibration flag')
    parser.add_argument("--pdeflag", type=int, default=1, help='relative pde calibration flag')
    parser.add_argument("--timeflag", type=int, default=1, help='timeoffset calibration flag')
    parser.add_argument("--gainflag", type=int, default=1, help='gain calibration flag')
    parser.add_argument("--algorithm", default="SiPMCalibAlg", help="specify the analysis algorithm")
    parser.add_argument("--loglevel", default="Info",
                                      choices=["Test", "Debug", "Info", "Warn", "Error", "Fatal"],
                                      help="Set the Log Level")

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
    # = BufferMemMgr =
    import BufferMemMgr
    bufMgr = task.createSvc("BufferMemMgr")
    bufMgr.property("TimeWindow").set([0, 0]);

  

    # = root writer =
    import RootWriter
    rootwriter = task.createSvc("RootWriter")
    rootwriter.property("Output").set({"ANASIMEVT": args.output})

    # = Tool =
    
    
    # = ana detsim =
    Sniper.loadDll("libSiPMCalibAlg.so")
    sipmcalibalg = task.createAlg(args.algorithm)
    sipmcalibalg.property("gainflag").set(args.gainflag)
    sipmcalibalg.property("timeflag").set(args.timeflag)
    sipmcalibalg.property("dcrflag").set(args.dcrflag)
    sipmcalibalg.property("inctflag").set(args.inctflag)
    sipmcalibalg.property("pdeflag").set(args.pdeflag)  
    darkcountratetool = sipmcalibalg.createTool("DarkCountRateCalibTool")
    relativepdetool = sipmcalibalg.createTool("RelativePDECalibTool")
    timeoffsettool = sipmcalibalg.createTool("TimeoffsetCalibTool")
    timeoffsettool.property("outtimefile").set(args.outtimefile)
    timeoffsettool.property("outtimeflag").set(args.outtimeflag)  
    gaintool = sipmcalibalg.createTool("GainCalibTool")
    gaintool.property("outgainfile").set(args.outgainfile)
    gaintool.property("outgainflag").set(args.outgainflag)
    incttool = sipmcalibalg.createTool("InternalCrossTalkCalibTool")
    incttool.property("outinctfile").set(args.outinctfile)
    incttool.property("outinctflag").set(args.outinctflag)
    # Add new Tool
    task.show()
    task.run()
    
    #t1 = time.clock() - t0
    #print "==================================="
    #print "run.py INFO: time elapsed: ", "{:10.4f}".format(t1), "s =", "{:10.4f}".format(t1/60), "min"
