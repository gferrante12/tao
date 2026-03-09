#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import Sniper

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run Tao Detector Simulation Analysis.')
    parser.add_argument("--evtmax", type=int, default=10, help='events to be processed')
    parser.add_argument("--seed", type=int, default=42, help='seed')
    parser.add_argument("--charge_template_file", default = "charge_template", help='close dark noise')
    parser.add_argument("--input", default=None, nargs='+', help="specify input filename")
    # parser.add_argument("--inputType", default="calibAlg", choices=["calibAlg", "elecSim"], help="specify input type, calibAlg or elecSim") # 选择输入
    parser.add_argument("--use_true_vertex", default=False, help="use true vertex coordinate")
    parser.add_argument("--true_vertex_file", default='', help="input true vertex coordinate from Tbranch [Sim] in elecSim")

    parser.add_argument("--output", default="rec-output.root", help="specify output filename")
    parser.add_argument("--user-output", default="user-ana-output.root", help="specify output filename")
    parser.add_argument("--algorithm", default="QMLERec", help="specify the analysis algorithm")
    ##
    # parser.add_argument("--enableChargeInfo", default=False, help="use nPE or Charge to reconstruct") # 默认将输入的电荷信息换算为PE数进行重建,最小化调用Chi2()；设置为true则不进行换算，直接使用电荷信息进行重,z建,最小化调用QMLE()..实际Chi2()和QMLE()的切换还有没有实现，需要在程序里手动修改

    return parser

if __name__ == "__main__":

    t0= time.time()

    parser = get_parser()
    args = parser.parse_args()
    print(args)

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

    # = geometry service =
    import TAOGeometry
    simgeomsvc = task.createSvc("SimGeomSvc")

    # = root writer =
    import RootWriter
    rootwriter = task.createSvc("RootWriter")
    rootwriter.property("Output").set({"RECEVT": args.user_output})

    task_writer = task.createSvc("RootOutputSvc/OutputSvc")
    task_writer.property("OutputStreams").set({
        "/Event/Rec/QMLE" : args.output
        })

    # = ana detsim =
    Sniper.loadDll("libRecQMLEAlg.so")
    anadetsimalg = task.createAlg(args.algorithm)
    # if args.algorithm == "MakeChargeTemplate":
    #     anadetsimalg.property("TempRadius").set(args.temp_radius)
    #     anadetsimalg.property("CloseDarkNoise").set(True)
    # else:
    #     anadetsimalg.property("ChargeTemplateFile").set(args.charge_template_file)
    #     # if args.enableChargeInfo == "true":
    #     #     anadetsimalg.property("enableChargeInfo").set(True)
    #     # else:
    #     #     anadetsimalg.property("enableChargeInfo").set(False)
    #     # anadetsimalg.property("inputType").set(args.inputType)
    #     if args.use_true_vertex == "true":
    #         anadetsimalg.property("useTrueVertex").set(True)
    #     else:
    #         anadetsimalg.property("useTrueVertex").set(False)
    #     anadetsimalg.property("trueVertexFile").set(args.true_vertex_file)
    anadetsimalg.property("ChargeTemplateFile").set(args.charge_template_file)
    if args.use_true_vertex == "true":
        anadetsimalg.property("useTrueVertex").set(True)
    else:
        anadetsimalg.property("useTrueVertex").set(False)
    anadetsimalg.property("trueVertexFile").set(args.true_vertex_file)

    task.show()
    task.run()

    t1 = time.time() - t0
    print("===================================")
    print("run.py INFO: time elapsed: ", "{:10.4f}".format(t1), "s =", "{:10.4f}".format(t1/60), "min")
