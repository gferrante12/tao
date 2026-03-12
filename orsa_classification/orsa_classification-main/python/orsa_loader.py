import uproot
import awkward as ak
import numpy as np
import json
import os

class OrsaLoader:
    def __init__(self, filename):
        """
        Initialize the loader with a ROOT filename.
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} not found.")
        
        self.filename = filename
        self.tag_map = {}
        self.config = self.load_config()
        self.data = None

    def load_config(self):
        """
        Attempts to load configuration and TagMap from the 'UserMetadata' tree.
        Closes file immediately.
        """
        config = None
        self.tag_map = {}
        
        try:
            with uproot.open(self.filename) as f:
                # Check for UserMetadata tree
                if "UserMetadata" in f:
                    meta = f["UserMetadata"]
                    arrays = meta.arrays(library="ak")
                    
                    if len(arrays) > 0:
                        # 1. Load ProductionConfig
                        if "ProductionConfig" in arrays.fields:
                             config_str = str(arrays[0].ProductionConfig)
                             try:
                                 config = json.loads(config_str)
                             except json.JSONDecodeError:
                                 print("Warning: Failed to parse ProductionConfig JSON.")

                        # 2. Load TagMap
                        self.tag_map = {}
                        try:
                            # Try different ways uproot might present the std::map
                            if "TagMap.first" in arrays.fields and "TagMap.second" in arrays.fields:
                                keys = arrays["TagMap.first"][0]
                                values = arrays["TagMap.second"][0]
                                self.tag_map = {str(k): int(v) for k, v in zip(keys, values)}
                            elif "TagMap/TagMap.first" in arrays.fields and "TagMap/TagMap.second" in arrays.fields:
                                keys = arrays["TagMap/TagMap.first"][0]
                                values = arrays["TagMap/TagMap.second"][0]
                                self.tag_map = {str(k): int(v) for k, v in zip(keys, values)}
                            elif "TagMap" in arrays.fields:
                                tm = arrays[0].TagMap
                                if hasattr(tm, "first") and hasattr(tm, "second"):
                                    self.tag_map = {str(k): int(v) for k, v in zip(tm.first, tm.second)}
                                elif hasattr(tm, "member"):
                                    self.tag_map = {str(k): int(v) for k, v in zip(tm.member("first"), tm.member("second"))}
                        except Exception as tag_e:
                            print(f"Warning: Could not parse TagMap: {tag_e}")
                                 
        except Exception as e:
            print(f"Note: No metadata found or error reading it ({e})")
            
        return config

    def list_trees(self):
        """Returns a list of keys (trees) in the ROOT file."""
        with uproot.open(self.filename) as f:
            return f.keys()

    def get_data(self, treename=None, branches=None):
        """
        Loads data from a TTree into an awkward array and closes the file.
        """
        with uproot.open(self.filename) as f:
            if treename is None:
                # Simple heuristic: find the first TTree that isn't metadata
                for key in f.keys():
                    if key == "UserMetadata;1" or key == "UserMetadata": continue
                    obj = f[key]
                    if isinstance(obj, uproot.behaviors.TTree.TTree):
                        treename = key
                        break
                
                if treename is None:
                    raise ValueError("No TTree found in file and no treename specified.")
                print(f"Auto-detected tree: {treename}")

            tree = f[treename]
            if branches is None:
                self.data = tree.arrays(library="ak")
            else:
                self.data = tree.arrays(branches, library="ak")
                
        print(f"Loaded {len(self.data)} entries from {treename}")
        return self.data

    def get_pairs(self, treename="IBDSignal_all"):
        """
        Specialized loader for IBD-like pairs.
        """
        return self.get_data(treename)
        
    def get_picked(self, treename="PickedEvents"):
        """
        Specialized loader for TimeWindowPicker output.
        """
        return self.get_data(treename)

