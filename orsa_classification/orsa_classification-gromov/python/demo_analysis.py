from orsa_loader import OrsaLoader
from orsa_visualizer import OrsaVisualizer
import matplotlib.pyplot as plt
import awkward as ak
import sys
import os

def main():
    # Helper to find a root file if none provided
    # Using a valid sub-file for showcase as the combined one has a corrupted Picker tree
    filename = "/storage/gpfs_data/juno/junofs/users/aserafin/tao_selection/tao_production_v4/root_output/output_1162_0087.root"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    # Fallback to known file if default doesn't exist
    if not os.path.exists(filename):
        fallback = "/storage/gpfs_data/juno/junofs/users/aserafin/tao_selection/tao_production_v3/combined_sel_v3.root"
        if os.path.exists(fallback):
            print(f"Default file {filename} not found. Using fallback: {fallback}")
            filename = fallback
        else:
            print(f"Error: File {filename} not found and fallback unavailable.")
            return

    print(f"Loading data from {filename}...")
    loader = OrsaLoader(filename)
    
    # --- Part 1: IBD Pairs (Standard Analysis) ---
    print("\n--- Showcase Part 1: IBD Pairs ---")
    try:
        data_pairs = loader.get_pairs()
        viz_pairs = OrsaVisualizer(data_pairs, tag_map=loader.tag_map)
        
        # TAO Full Geometry
        print("1. TAO Full Geometry (Pairs)...")
        fig1, _ = viz_pairs.plot_scatter_3d(detector="TAO", title="TAO: IBD Candidates")
        fig1.savefig("v4_showcase_1_tao.png")

        # Physics Correlations
        print("2. Physics Correlations...")
        fig2 = viz_pairs.plot_correlations()
        fig2.savefig("v4_showcase_2_correlations.png")

        # Neighborhood
        print("3. Event Neighborhood...")
        t_target = ak.to_numpy(data_pairs['t_p'])[10]
        fig3 = viz_pairs.plot_neighborhood(target_time=t_target, window_ns=500000) # 500 us
        fig3.savefig("v4_showcase_3_neighborhood.png")
        
    except Exception as e:
        print(f"Error in Pairs showcase: {e}")

    # --- Part 2: TimeWindowPicker (Trigger Analysis) ---
    print("\n--- Showcase Part 2: Picker Triggers ---")
    try:
        # Explicit cycle 1 to avoid empty 'output' subdirectory variants
        data_picker = loader.get_data("PickedEventsIBD;1")
        viz_picker = OrsaVisualizer(data_picker, tag_map=loader.tag_map)
        
        # All picked events
        print("4. All Picked Events...")
        fig4, _ = viz_picker.plot_scatter_3d(title="TimeWindowPicker: All Events")
        fig4.savefig("v4_showcase_4_picker_all.png")

        # Specific Trigger
        print("5. Specific Trigger Window...")
        # Pick the first TriggerID found
        tid = data_picker['TriggerID'][0]
        fig5 = viz_picker.plot_trigger(trigger_id=tid)
        fig5.savefig("v4_showcase_5_trigger.png")

        # Trigger by Time
        print("6. Trigger by Timestamp...")
        t_picker = ak.to_numpy(data_picker['Time'])[len(data_picker)//2]
        fig6 = viz_picker.plot_trigger(target_time=t_picker)
        fig6.savefig("v4_showcase_6_trigger_time.png")

        # Enhanced Neighborhood for Picker
        print("7. Enhanced Neighborhood (Picker Cluster)...")
        fig7 = viz_picker.plot_neighborhood(target_time=t_picker, window_ns=5000000) # 5ms
        fig7.savefig("v4_showcase_7_picker_neighborhood.png")

    except Exception as e:
        print(f"Error in Picker showcase: {e}")

    print("\nShowcase complete! All v4 files saved as v4_showcase_*.png")


if __name__ == "__main__":
    main()
