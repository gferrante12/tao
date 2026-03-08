#!/usr/bin/env python3
"""
Explore ROOT file structure - find all trees and branches
"""

import ROOT
import sys

def find_trees(directory, path="", indent=0):
    """Recursively find all trees in a ROOT file"""
    prefix = "  " * indent

    for key in directory.GetListOfKeys():
        obj = key.ReadObj()
        full_path = f"{path}/{key.GetName()}" if path else key.GetName()

        if obj.InheritsFrom("TTree"):
            tree = obj
            print(f"{prefix}📊 TREE: {full_path}")
            print(f"{prefix}   Entries: {tree.GetEntries()}")
            print(f"{prefix}   Branches:")
            for branch in tree.GetListOfBranches():
                branch_name = branch.GetName()
                branch_type = branch.GetClassName()
                if not branch_type:
                    # Leaf type for basic types
                    leaves = branch.GetListOfLeaves()
                    if leaves.GetEntries() > 0:
                        branch_type = leaves.At(0).GetTypeName()
                print(f"{prefix}     • {branch_name:20s} : {branch_type}")
            print()

        elif obj.InheritsFrom("TDirectoryFile"):
            print(f"{prefix}📁 DIR: {full_path}")
            find_trees(obj, full_path, indent + 1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python explore_root.py <file.root>")
        sys.exit(1)

    filename = sys.argv[1]
    f = ROOT.TFile.Open(filename)

    if not f or f.IsZombie():
        print(f"ERROR: Cannot open {filename}")
        sys.exit(1)

    print("="*80)
    print(f"Exploring: {filename}")
    print("="*80)
    print()

    find_trees(f)

    f.Close()
