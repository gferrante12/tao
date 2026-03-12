import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import awkward as ak
from itertools import cycle

class OrsaVisualizer:
    def __init__(self, data, config=None, tag_map=None):
        """
        Initialize with awkward array data.
        """
        self.data = data
        self.config = config
        self.tag_map = tag_map or {}
        # Inverse mapping for lookup: ID -> Name
        self.id_to_tag = {v: k for k, v in self.tag_map.items()}
        
        # Schema detection
        self.is_picker = 'TriggerID' in self.data.fields
        
        # Default column mapping
        if self.is_picker:
            print("Detected TimeWindowPicker output format.")
            self.col_map = {
                'x': 'X', 'y': 'Y', 'z': 'Z', 'E': 'Energy', 't': 'Time'
            }
        else:
            self.col_map = {
                'x': 'x_p', 'y': 'y_p', 'z': 'z_p', 'E': 'E_p', 't': 't_p'
            }

        # Set professional style
        try:
            plt.style.use('seaborn-v0_8-paper')
        except:
            try:
                plt.style.use('seaborn-paper')
            except:
                plt.style.use('ggplot') 
        
        plt.rcParams.update({
            'font.size': 12,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.figsize': (10, 8),
            'lines.linewidth': 2,
            'lines.markersize': 6,
            'grid.alpha': 0.5,
        })

    def _draw_cylinder(self, ax, radius, height, z_offset=0, color='blue', edgecolor='k', alpha=0.1):
        """Helper to draw a cylinder using surface plot."""
        z = np.linspace(0, height, 10) + z_offset
        theta = np.linspace(0, 2*np.pi, 30)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = radius * np.cos(theta_grid)
        y_grid = radius * np.sin(theta_grid)
        ax.plot_surface(x_grid, y_grid, z_grid, color=color, alpha=alpha, edgecolor=edgecolor, linewidth=0.5, shade=True)

    def _draw_box(self, ax, size_x, size_y, size_z, pos=(0,0,0), color='green', edgecolor='k', alpha=0.1):
        """Helper to draw a box using Poly3DCollection for filled surfaces."""
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        
        x = [pos[0] - size_x/2, pos[0] + size_x/2]
        y = [pos[1] - size_y/2, pos[1] + size_y/2]
        z = [pos[2] - size_z/2, pos[2] + size_z/2]
        
        # Vertices of the box
        # Bottom face
        v = [
            [[x[0], y[0], z[0]], [x[1], y[0], z[0]], [x[1], y[1], z[0]], [x[0], y[1], z[0]]], # Bottom
            [[x[0], y[0], z[1]], [x[1], y[0], z[1]], [x[1], y[1], z[1]], [x[0], y[1], z[1]]], # Top
            [[x[0], y[0], z[0]], [x[1], y[0], z[0]], [x[1], y[0], z[1]], [x[0], y[0], z[1]]], # Front
            [[x[0], y[1], z[0]], [x[1], y[1], z[0]], [x[1], y[1], z[1]], [x[0], y[1], z[1]]], # Back
            [[x[0], y[0], z[0]], [x[0], y[1], z[0]], [x[0], y[1], z[1]], [x[0], y[0], z[1]]], # Left
            [[x[1], y[0], z[0]], [x[1], y[1], z[0]], [x[1], y[1], z[1]], [x[1], y[0], z[1]]]  # Right
        ]
        
        # Plot faces
        for vertices in v:
            poly = Poly3DCollection([vertices], alpha=alpha, facecolor=color, edgecolor=edgecolor, linewidth=0.5)
            ax.add_collection3d(poly)

    def _draw_detector_wireframe(self, ax, detector="TAO", 
                                 show_cd=True, cd_color='gray', cd_alpha=0.1, cd_edge='k',
                                 show_wp=True, wp_color='blue', wp_alpha=0.05, wp_edge='k',
                                 show_tt=True, tt_color='green', tt_alpha=0.1, tt_edge='k'):
        """Draws the detector geometry with filled surfaces."""
        if detector == "TAO":
            # TAO Geometry
            # 1. Central Detector (Acrylic Sphere): R ~ 900 mm
            if show_cd:
                radius = 900 # mm
                u = np.linspace(0, 2 * np.pi, 50)
                v = np.linspace(0, np.pi, 30)
                x = radius * np.outer(np.cos(u), np.sin(v))
                y = radius * np.outer(np.sin(u), np.sin(v))
                z = radius * np.outer(np.ones(np.size(u)), np.cos(v))
                ax.plot_surface(x, y, z, color=cd_color, alpha=cd_alpha, edgecolor=cd_edge, linewidth=0.5)

            # 2. Water Tank (Box): 5.108m x 5.108m x 4.04m
            if show_wp:
                self._draw_box(ax, 5108, 5108, 4040, color=wp_color, edgecolor=wp_edge, alpha=wp_alpha)

            # 3. Top Veto Tracker (TVT) (Box): 5m x 5m x 0.22m, Offset ~ 2.5m
            if show_tt:
                self._draw_box(ax, 5000, 5000, 220, pos=(0, 0, 2500), color=tt_color, edgecolor=tt_edge, alpha=tt_alpha)

        elif detector == "JUNO":
            # JUNO Geometry
            # 1. Central Detector (Acrylic Sphere): R ~ 17.7m
            if show_cd:
                radius = 17700 # mm
                u = np.linspace(0, 2 * np.pi, 50)
                v = np.linspace(0, np.pi, 30)
                x = radius * np.outer(np.cos(u), np.sin(v))
                y = radius * np.outer(np.sin(u), np.sin(v))
                z = radius * np.outer(np.ones(np.size(u)), np.cos(v))
                ax.plot_surface(x, y, z, color=cd_color, alpha=cd_alpha, edgecolor=cd_edge, linewidth=0.5)

            # 2. Water Pool (Cylinder): R ~ 21.75m, H ~ 44m
            if show_wp:
                radius_wp = 21750 # mm
                height_wp = 44000 # mm
                self._draw_cylinder(ax, radius_wp, height_wp, z_offset=-height_wp/2, color=wp_color, edgecolor=wp_edge, alpha=wp_alpha)

            # 3. Top Tracker (Global Box/Plane)
            if show_tt:
                self._draw_box(ax, 20000, 20000, 500, pos=(0,0, 22500), color=tt_color, edgecolor=tt_edge, alpha=tt_alpha)
        
        else:
            # Fallback
            radius = 650
            u = np.linspace(0, 2 * np.pi, 30)
            v = np.linspace(0, np.pi, 20)
            x = radius * np.outer(np.cos(u), np.sin(v))
            y = radius * np.outer(np.sin(u), np.sin(v))
            z = radius * np.outer(np.ones(np.size(u)), np.cos(v))
            ax.plot_surface(x, y, z, color='gray', alpha=0.1, edgecolor='k', linewidth=0.5)

    def _get_axis_limit(self, detector, show_cd, show_wp, show_tt):
        """Calculates specific axis limits based on visible components."""
        limit = 1000 # Default
        
        if detector == "TAO":
            # Hierarchy of sizes: TT/WP (>2.5m) > CD (~0.9m)
            if show_wp or show_tt:
                limit = 2600 # Fits 5.1m box
            elif show_cd:
                limit = 1000 # Fits 0.9m sphere closely
            else:
                limit = 2600 # Fallback
                
        elif detector == "JUNO":
            # Hierarchy: TT (~22.5m height) > WP (~22m height) > CD (~17.7m)
            if show_tt:
                limit = 23000 # Fits Top Tracker at z=22.5m
            elif show_wp:
                limit = 22000 # Fits Water Pool
            elif show_cd:
                limit = 18000 # Fits 17.7m sphere closely
            else:
                limit = 22000 # Fallback
        
        return limit

    def plot_scatter_3d(self, x_col=None, y_col=None, z_col=None, c_col=None, s_col=None, s_scale=10,
                        detector="TAO", title="3D Event Distribution",
                        show_cd=True, cd_color='gray', cd_alpha=0.1, cd_edge='k',
                        show_wp=True, wp_color='blue', wp_alpha=0.05, wp_edge='k',
                        show_tt=True, tt_color='green', tt_alpha=0.1, tt_edge='k'):
        """
        3D scatter plot of events.
        Args:
            s_col: Column for marker size (e.g., Energy).
            s_scale: Scaling factor for marker size.
        """
        if len(self.data) == 0:
            print("Warning: Dataset is empty. Skipping plot.")
            return plt.figure(), None

        # Resolve defaults based on schema
        x_col = x_col or self.col_map['x']
        y_col = y_col or self.col_map['y']
        z_col = z_col or self.col_map['z']
        c_col = c_col or self.col_map['E']

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Convert awkward array to numpy for plotting
        x = ak.to_numpy(self.data[x_col])
        y = ak.to_numpy(self.data[y_col])
        z = ak.to_numpy(self.data[z_col])
        c = ak.to_numpy(self.data[c_col]) if c_col in self.data.fields else None
        
        if s_col and s_col in self.data.fields:
            s = ak.to_numpy(self.data[s_col]) * s_scale
            # Ensure minimum size
            s = np.maximum(s, 1.0)
        else:
            s = 20
        
        self._draw_detector_wireframe(ax, detector, 
                                      show_cd, cd_color, cd_alpha, cd_edge,
                                      show_wp, wp_color, wp_alpha, wp_edge,
                                      show_tt, tt_color, tt_alpha, tt_edge)
        
        sc = ax.scatter(x, y, z, c=c, cmap='viridis', s=s, alpha=0.9, edgecolors='w', linewidth=0.5, zorder=10)
        
        if c is not None:
            cbar = plt.colorbar(sc, ax=ax, pad=0.1)
            cbar.set_label(c_col)

        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_zlabel('Z [mm]')
        ax.set_title(f"{title} - {detector} Geometry")
        
        limit = self._get_axis_limit(detector, show_cd, show_wp, show_tt)

        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_zlim(-limit, limit)
        
        ax.set_box_aspect([1, 1, 1]) # Equal aspect ratio
        
        plt.tight_layout()
        return fig, ax

    def plot_correlations(self):
        """
        Standard IBD correlation plots: Prompt vs Delayed Energy, dt vs dr.
        """
        fig = plt.figure(figsize=(12, 5))
        gs = gridspec.GridSpec(1, 2, figure=fig)
        
        # Plot 1: Ep vs Ed
        ax1 = fig.add_subplot(gs[0, 0])
        ep = ak.to_numpy(self.data['E_p'])
        ed = ak.to_numpy(self.data['E_d'])
        
        h1 = ax1.hist2d(ep, ed, bins=50, cmap='inferno', cmin=1)
        ax1.set_xlabel('Prompt Energy [MeV]')
        ax1.set_ylabel('Delayed Energy [MeV]')
        ax1.set_title('Prompt vs Delayed Energy')
        plt.colorbar(h1[3], ax=ax1, label='Counts')
        
        # Plot 2: dt vs dr
        ax2 = fig.add_subplot(gs[0, 1])
        # If dt/dr are already calculated in ROOT file
        if 'dt' in self.data.fields and 'dr' in self.data.fields:
            dt = ak.to_numpy(self.data['dt']) 
            dr = ak.to_numpy(self.data['dr'])
            
            h2 = ax2.hist2d(dt, dr, bins=50, cmap='inferno', cmin=1)
            ax2.set_xlabel('Time Difference [ns]')
            ax2.set_ylabel('Distance [mm]')
            ax2.set_title('Time vs Distance Separation')
            plt.colorbar(h2[3], ax=ax2, label='Counts')
        
        plt.tight_layout()
        return fig

    def plot_event_topology(self, n_events=50, detector="TAO", 
                            show_cd=True, cd_color='gray', cd_alpha=0.1, cd_edge='k',
                            show_wp=True, wp_color='blue', wp_alpha=0.05, wp_edge='k',
                            show_tt=True, tt_color='green', tt_alpha=0.1, tt_edge='k'):
        """
        Plots 3D arrows connecting prompt and delayed events for a subset of events.
        """
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        self._draw_detector_wireframe(ax, detector, 
                                      show_cd, cd_color, cd_alpha, cd_edge,
                                      show_wp, wp_color, wp_alpha, wp_edge,
                                      show_tt, tt_color, tt_alpha, tt_edge)
        
        # Take subset
        subset = self.data[:n_events]
        
        xp = ak.to_numpy(subset['x_p'])
        yp = ak.to_numpy(subset['y_p'])
        zp = ak.to_numpy(subset['z_p'])
        
        xd = ak.to_numpy(subset['x_d'])
        yd = ak.to_numpy(subset['y_d'])
        zd = ak.to_numpy(subset['z_d'])
        
        # Plot points
        ax.scatter(xp, yp, zp, c='blue', label='Prompt', s=30)
        ax.scatter(xd, yd, zd, c='red', label='Delayed', s=30)
        
        # Draw arrows
        for i in range(len(xp)):
            ax.plot([xp[i], xd[i]], [yp[i], yd[i]], [zp[i], zd[i]], color='gray', alpha=0.5, linestyle='--')
            
        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_zlabel('Z [mm]')
        ax.set_title(f'Event Topology (First {n_events} pairs) - {detector}')
        ax.legend()
        
        limit = self._get_axis_limit(detector, show_cd, show_wp, show_tt)

        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_zlim(-limit, limit)
        ax.set_box_aspect([1, 1, 1])
        
        return fig

    def plot_muon_veto(self):
        """
        Plots the correlation between time since last muon (dt_mu) and distance to muon track (dist_mu).
        Useful for analyzing background rejection.
        """
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Check if muon data exists
        if 'dt_mu' not in self.data.fields or 'dist_mu' not in self.data.fields:
            print("Warning: Muon data not found.")
            return fig
            
        dt_mu = ak.to_numpy(self.data['dt_mu']) 
        dist_mu = ak.to_numpy(self.data['dist_mu']) 
        
        # 2D Histogram
        h = ax.hist2d(dt_mu, dist_mu, bins=[50, 50], norm=plt.matplotlib.colors.LogNorm(), cmap='plasma')
        
        ax.set_xlabel('Time since last Muon [ns]')
        ax.set_ylabel('Distance to Muon Track [mm]')
        ax.set_title('Muon Veto Correlations')
        plt.colorbar(h[3], ax=ax, label='Counts')
        
        plt.tight_layout()
        return fig

    def plot_neighborhood(self, event_idx=0, target_time=None, window_ns=200000, show_labels=True):
        """
        Plots a neighborhood view around a specific event.
        Args:
            event_idx: Index of the central event.
            target_time: If provided, finds the event closest to this timestamp 
                         and overrides event_idx.
            window_ns: Time window in nanoseconds (±).
            show_labels: Whether to show text labels (Energy, Tag) next to points.
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111)
        
        # Detector mapping from C++ source
        DET_MAP = {1: 'CD', 2: 'WP', 4: 'TT'}
        
        times = ak.to_numpy(self.data[self.col_map['t']])
        
        # If target_time is provided, find the closest event
        if target_time is not None:
            # Find index of event with closest time
            event_idx = np.argmin(np.abs(times - target_time))
            found_time = times[event_idx]
            print(f"Selecting event {event_idx} closest to time {target_time} (found {found_time})")
        
        # Get central event data
        center_t = times[event_idx]
        center_pos = np.array([self.data[self.col_map['x']][event_idx], 
                               self.data[self.col_map['y']][event_idx], 
                               self.data[self.col_map['z']][event_idx]])
        
        # Efficient filtering
        dt = (times - center_t) 
        mask = np.abs(dt) < window_ns
        indices = np.where(mask)[0]
        
        # If too many events, restrict labels but still plot points
        max_labels = 50
        labeled_count = 0
        
        if len(indices) > 500:
            print(f"Warning: Too many events in window ({len(indices)}). Plotting first 500 closest in time.")
            rel_times = np.abs(dt[indices])
            sorted_args = np.argsort(rel_times)
            indices = indices[sorted_args[:500]]

        # Plot based on data type
        # Plot based on data type
        if self.is_picker:
            # Flat events
            x = ak.to_numpy(self.data[self.col_map['x']])
            y = ak.to_numpy(self.data[self.col_map['y']])
            z = ak.to_numpy(self.data[self.col_map['z']])
            E = ak.to_numpy(self.data[self.col_map['E']])
            D = ak.to_numpy(self.data['Det']) if 'Det' in self.data.fields else None
            TID = ak.to_numpy(self.data['TriggerID']) if 'TriggerID' in self.data.fields else None
            TAGS = ak.to_numpy(self.data['tags']) if 'tags' in self.data.fields else None
            
            # Create proxy artists for legend
            legend_elements = [
                plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='gold', markersize=15, label='Center Event'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=plt.get_cmap('Set1')(1 % 9), markersize=8, label='Det: CD'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=plt.get_cmap('Set1')(2 % 9), markersize=8, label='Det: WP'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=plt.get_cmap('Set1')(4 % 9), markersize=8, label='Det: TT'),
            ]

            # To avoid overlaps, use simple staggering
            stagger = cycle([12, 25, -12, -25])

            for i in indices:
                pos = np.array([x[i], y[i], z[i]])
                dist = np.linalg.norm(pos - center_pos)
                
                # Highlight center
                if i == event_idx:
                    ax.scatter(dt[i], dist, c='gold', s=E[i]*50, edgecolor='k', marker='*', zorder=10)
                    if show_labels:
                        lbl = f"CENTER\n{E[i]:.2f} MeV"
                        if TAGS is not None and len(TAGS[i]) > 0:
                            cat_names = [self.id_to_tag.get(int(t), str(t)) for t in TAGS[i]]
                            lbl += f"\n({', '.join(cat_names)})"
                        ax.text(dt[i], dist + 30, lbl, fontsize=9, fontweight='bold', ha='center', color='darkred',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                else:
                    # Color by Detector 
                    if D is not None:
                        color = plt.get_cmap('Set1')(D[i] % 9)
                        label = f"Det: {DET_MAP.get(D[i], D[i])}"
                    else:
                        color = 'blue'
                        label = 'Other'
                        
                    ax.scatter(dt[i], dist, color=color, s=E[i]*20, alpha=0.6)
                    
                    # Label events with significant energy or if within limit
                    if show_labels and (E[i] > 0.5 or labeled_count < max_labels):
                        lbl = f"{E[i]:.2f} MeV"
                        if TAGS is not None and len(TAGS[i]) > 0:
                            cat_names = [self.id_to_tag.get(int(t), str(t)) for t in TAGS[i]]
                            lbl += f"\n{cat_names[0]}"
                        
                        offset = next(stagger)
                        ax.text(dt[i], dist + offset, lbl, fontsize=8, alpha=0.9, ha='center',
                                bbox=dict(facecolor='white', alpha=0.4, edgecolor='none', pad=1))
                        labeled_count += 1
            ax.legend(handles=legend_elements, loc='upper right', frameon=True, framealpha=0.9)
        else:
            # Standard Pairs logic (Prompt only for neighborhood reference)
            all_t_p = ak.to_numpy(self.data['t_p'])
            all_t_d = ak.to_numpy(self.data['t_d'])
            stagger = cycle([10, 20, -10, -20])
            
            for i in indices:
                p_t = all_t_p[i] - center_t
                d_t = all_t_d[i] - center_t
                
                p_pos = np.array([self.data['x_p'][i], self.data['y_p'][i], self.data['z_p'][i]])
                d_pos = np.array([self.data['x_d'][i], self.data['y_d'][i], self.data['z_d'][i]])
                
                p_dist = np.linalg.norm(p_pos - center_pos)
                d_dist = np.linalg.norm(d_pos - center_pos)
                
                p_E = self.data['E_p'][i]
                d_E = self.data['E_d'][i]
                
                if i == event_idx:
                    ax.scatter(p_t, p_dist, c='gold', s=p_E*50, edgecolor='k', marker='*', label='Center Prompt', zorder=10)
                    ax.scatter(d_t, d_dist, c='orange', s=d_E*50, edgecolor='k', marker='*', label='Center Delayed', zorder=10)
                    if show_labels:
                        p_tags = self.data['tags_p'][i] if 'tags_p' in self.data.fields else []
                        p_cat = self.id_to_tag.get(int(p_tags[0]), str(p_tags[0])) if (hasattr(p_tags, '__len__') and len(p_tags)>0) else "None"
                        ax.text(p_t, p_dist+25, f"{p_E:.2f} MeV\n({p_cat})", fontsize=8, fontweight='bold', ha='center',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                else:
                    tag = 0
                    cat_name = "Unknown"
                    if 'tags_p' in self.data.fields:
                        tag_val = self.data['tags_p'][i]
                        tag = tag_val[0] if (hasattr(tag_val, '__len__') and len(tag_val)>0) else (tag_val if not hasattr(tag_val, '__len__') else 0)
                        cat_name = self.id_to_tag.get(int(tag), f"Tag {tag}")
                    
                    cmap = plt.get_cmap('tab10')
                    ax.scatter(p_t, p_dist, color=cmap(tag%10), s=p_E*20, alpha=0.6, label=f'Pair: {cat_name}')
                    ax.scatter(d_t, d_dist, color=cmap(tag%10), s=d_E*20, alpha=0.6)
                    
                    if show_labels and labeled_count < max_labels:
                        offset = next(stagger)
                        ax.text(p_t, p_dist+offset, f"{p_E:.2f} MeV", fontsize=7, alpha=0.8, ha='center',
                                bbox=dict(facecolor='white', alpha=0.4, edgecolor='none', pad=1))
                        labeled_count += 1
                
                # Arrow
                ax.annotate("", xy=(d_t, d_dist), xytext=(p_t, p_dist),
                            arrowprops=dict(arrowstyle="->", color="gray", alpha=0.3))
            
            # Refine Pairs legend
            handles, labels = ax.get_legend_handles_labels()
            by_label = {}
            for l, h in zip(labels, handles):
                if l not in by_label: by_label[l] = h
            ax.legend(by_label.values(), by_label.keys(), loc='upper right', frameon=True, framealpha=0.9)

        ax.set_xlabel(f'Time Difference relative to Event {event_idx} [ns]')
        ax.set_ylabel(f'Distance relative to Center Position [mm]')
        ax.set_title(f'Event Neighborhood (Selected Event {event_idx}, T={center_t:.0f})')
        ax.grid(True, alpha=0.3)
        
        return fig

    def plot_trigger(self, trigger_id=None, target_time=None):
        """
        Plots all events within a single trigger window.
        Args:
            trigger_id: Specific TriggerID from picker.
            target_time: If provided, finds the trigger containing this time.
        """
        if target_time is not None:
            # Find trigger closest to time
            times = ak.to_numpy(self.data[self.col_map['t']])
            idx = np.argmin(np.abs(times - target_time))
            trigger_id = self.data['TriggerID'][idx]
            print(f"Selecting TriggerID {trigger_id} closest to time {target_time}")
        
        if trigger_id is None:
            print("Error: Must provide either trigger_id or target_time.")
            return None
            
        # Filter data for this trigger
        mask = self.data['TriggerID'] == trigger_id
        trigger_data = self.data[mask]
        
        if len(trigger_data) == 0:
            print(f"Warning: No events found for TriggerID {trigger_id}")
            return None
            
        # Extract coordinates
        x = ak.to_numpy(trigger_data[self.col_map['x']])
        y = ak.to_numpy(trigger_data[self.col_map['y']])
        z = ak.to_numpy(trigger_data[self.col_map['z']])
        E = ak.to_numpy(trigger_data[self.col_map['E']])
        T = ak.to_numpy(trigger_data[self.col_map['t']])
        
        # 3D Plot
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Detector geometry (TAO default for picker usually)
        self._draw_detector_wireframe(ax, detector="TAO", show_tt=False)
        
        # Scatter points colored by time within window
        # Normalize time relative to trigger start
        t_rel = (T - np.min(T)) / 1e3 # relative us
        sc = ax.scatter(x, y, z, c=t_rel, s=E*20, cmap='viridis', alpha=0.8, edgecolors='k')
        
        cbar = plt.colorbar(sc, ax=ax, label='Relative Time [us]')
        ax.set_title(f'Trigger {trigger_id} Window ({len(x)} events)')
        
        # Dynamic limits
        lim = self._get_axis_limit("TAO", True, False, False)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_zlim(lim)
        
        return fig
