#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author: lintao

import time
import Sniper

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run Tao Calibration Analysis.')
    parser.add_argument("--evtmax", type=int, default=989, help='events to be processed')
    parser.add_argument("--seed", type=int, default=42, help='seed')
    parser.add_argument("--input", default=None, nargs='+', help="specify input filename")
    parser.add_argument("--output", default="user-ana-output-calib.root", help="specify output filename")
    parser.add_argument("--algorithm", default="CalibAnaTest", help="specify the analysis algorithm")
   
    return parser

if __name__ == "__main__":
    
    #t0= time.clock()

    parser = get_parser()
    args = parser.parse_args()
    print (args)

    task = Sniper.Task("task")
    task.setEvtMax(args.evtmax)
    #task.setLogLevel(0)

    # = random svc =
    import RandomSvc
    rndm = task.createSvc("RandomSvc")
    rndm.property("Seed").set(args.seed)

    # = rootio =
    import RootIOSvc
    if not args.input:
        print("Please provide an input file for analysis")
        exit(-1)
    ris = task.createSvc("RootInputSvc/InputSvc")
    ris.property("InputFile").set(args.input)

    # = BufferMemMgr =
    import BufferMemMgr
    bufMgr = task.createSvc("BufferMemMgr")
    bufMgr.property("TimeWindow").set([0, 0]);

 

    # = root writer =
    import RootWriter
    rootwriter = task.createSvc("RootWriter")
    rootwriter.property("Output").set({"ANASIMEVT": args.output})

    # = ana detsim =
    Sniper.loadDll("libCalibAna.so")
    calibana= task.createAlg(args.algorithm)
    

    task.show()
    task.run()
    
    #t1 = time.clock() - t0
    #print "==================================="
    #print "run.py INFO: time elapsed: ", "{:10.4f}".format(t1), "s =", "{:10.4f}".format(t1/60), "min"
