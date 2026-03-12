#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OrsaAlg Execution Script
========================

This script is the main entry point to run the OrsaClassification algorithm
within the SNiPER framework. It sets up the execution environment, configures
inputs/outputs, loads the necessary libraries, and launches the analysis chain.

Usage:
    python run.py --input <file1> <file2> ... --output output.root --config config.json
    python run.py --input-list files.txt ...

Arguments:
    --evtmax        : Maximum number of events to process (default: 1000).
    --input         : List of input ESD/ROOT files.
    --input-list    : Text file containing a list of input files (one per line).
    --output        : Path to the output ROOT file.
    --config        : Path to the JSON configuration file for categories/rules.
    --loglevel      : SNiPER log level (0:Test ... 3:Info ... 6:Fatal).
"""

import Sniper
import os

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Run OrsaClassification')
    parser.add_argument("--evtmax", type=int, default=1000, help="Max events")
    parser.add_argument("--input", nargs="+", help="Input ESD files")
    parser.add_argument("--input-list", help="Text file containing list of input files")
    parser.add_argument("--input-correlation", nargs="+", help="Input correlation (rtraw) files")
    parser.add_argument("--input-correlation-list", help="Text file with rtraw file list")
    parser.add_argument("--output", default="orsa_output.root", help="Output file path")
    parser.add_argument("--config", default="", help="Config JSON path")
    parser.add_argument("-v", "--loglevel", default=3, type=int, choices=[0,1,2,3,4,5,6],
                        help="Log level (0:test, 2:debug, 3:info, 4:warn, 5:error, 6:fatal)")
    return parser


def read_input_list(file_path):
    """Read file paths from a text file, one per line"""
    if not os.path.exists(file_path):
        print(f"ERROR: File list '{file_path}' does not exist.")
        exit(1)
    files = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                files.append(line)
    return files


def find_config_file(config_arg):
    """Find config file, checks argument first then searches common locations."""
    if config_arg and os.path.exists(config_arg):
        return os.path.abspath(config_arg)
    
    # Check common locations relative to this script or current work dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "config.json"),
        os.path.join(script_dir, "..", "share", "config.json"),
        os.path.join(os.getcwd(), "config.json"),
        os.path.join(os.getcwd(), "share", "config.json"),
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    print(f"ERROR: Could not find config.json. Tried: {config_arg}, {candidates}")
    exit(1)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    # --- 1. Configure Input Files ---
    input_files = []
    if args.input_list:
        input_files = read_input_list(args.input_list)
        print(f"Read {len(input_files)} input files from {args.input_list}")
    elif args.input:
        input_files = args.input
    else:
        print("ERROR: Must provide either --input or --input-list")
        exit(1)
    
    # Handle optional correlation files (e.g. for trigger headers)
    correlation_files = []
    if args.input_correlation_list:
        correlation_files = read_input_list(args.input_correlation_list)
        print(f"Read {len(correlation_files)} correlation files")
    elif args.input_correlation:
        correlation_files = args.input_correlation

    # Find configuration file
    config_path = find_config_file(args.config)
    print(f"Using config: {config_path}")

    # --- 2. Setup SNiPER Task ---
    task = Sniper.Task("task")
    task.setEvtMax(args.evtmax)
    task.setLogLevel(args.loglevel)

    # BufferMemMgr: Manages event memory buffer.
    # Setting the time window [-1.5s, 0.5s] ensures that sufficient history
    # is available in memory for accidental background estimation (which often
    # requires looking back by 1 second).
    import BufferMemMgr
    bufMgr = task.createSvc("BufferMemMgr")
    bufMgr.property("TimeWindow").set([-1.5, 0.5]) 

    # RootInputSvc: Handles reading of ROOT/ESD files.
    import RootIOSvc
    inputsvc = task.createSvc("RootInputSvc/InputSvc")
    inputsvc.property("InputFile").set(input_files)
    
    if correlation_files:
        inputsvc.property("InputCorrelationFile").set(correlation_files)
        print(f"Loaded {len(correlation_files)} correlation file(s) for trigger headers")

    # --- 3. Setup Output ---
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    task.createSvc("RootOutputSvc/RootOutputSvc")
    import RootWriter
    task.property("svcs").append("RootWriter")
    rw = task.find("RootWriter")
    rw.property("Output").set({"output": args.output})

    # --- 4. Load Geometry and Libraries ---
    # PMTParamSvc is needed for some reconstruction parameters.
    try:
        import Geometry
        task.createSvc("PMTParamSvc")
    except Exception as e:
        print(f"Note: PMTParamSvc not loaded ({e}), some features may be unavailable")

    import os
    Sniper.loadDll("libRecEvent.so")
    # Load OecEvent only if not in TAO environment (TAO has its own event model)
    if not os.getenv("TAOTOP"):
        Sniper.loadDll("libOecEvent.so")
    
    # Load our custom library
    Sniper.loadDll("libOrsaClassification.so")
    
    # --- 5. Create and Run Algorithm ---
    alg = task.createAlg("OrsaAlg")
    alg.property("Config").set(config_path)

    task.show()
    task.run()
