"""
collision_analyzer.py (modified to use only MVCC_final)
"""

# Standard library imports
import os  # filesystem utilities
from datetime import datetime
import sys

# Third-party imports
import pandas as pd
import matplotlib.pyplot as plt

# Simple GUI using tkinter
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

# =======================
# COLLISION ANALYZER CLASS
# (enforces MVCC_final in script directory)
# =======================
class CollisionAnalyzer:
    """Load NYC collision CSV and provide analysis utilities."""

    def __init__(self, csv_file="MVCC_final.csv"):
        # Force using the fixed CSV file located beside this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file = os.path.join(script_dir, "MVCC_final.csv")

        # Inform user dataset is being loaded
        print("\n------------------------------")
        print("   LOADING COLLISION DATASET  ")
        print(f"   (Fixed file: {csv_file})")
        print("------------------------------\n")

        # Ensure the CSV (or file named MVCC_final) exists before attempting to read
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Read dataset without memory type inference issues
        self.df = pd.read_csv(csv_file, low_memory=False)
        print("Dataset loaded successfully!\n")

        # Verify required column exists and parse dates; drop invalid rows
        if "CRASH DATE" not in self.df.columns:
            raise KeyError("Required column 'CRASH DATE' not found in dataset.")

        self.df["CRASH DATE"] = pd.to_datetime(self.df["CRASH DATE"], errors="coerce")
        self.df = self.df.dropna(subset=["CRASH DATE"]).reset_index(drop=True)

        # Placeholder for a filtered view based on chosen date range
        self.filtered_df = None

    # =========================
    # DATE RANGE FILTER (HARD-LOCKED)
    # =========================
    def set_date_range(self, start_str, end_str):
        """Set the analysis date range and create a filtered dataframe.

        Dates must be within the hard-locked range and in YYYY-MM-DD format.
        """

        def fix_date(d):
            # Normalize common separators and ensure zero-padded parts
            d = d.strip().replace("/", "-").replace(" ", "-")
            parts = d.split("-")
            if len(parts) == 3:
                y = parts[0]
                m = parts[1].zfill(2)
                da = parts[2].zfill(2)
                return f"{y}-{m}-{da}"
            return d

        # Allowed hard-locked date boundaries
        MIN_DATE = datetime(2023, 1, 1)
        MAX_DATE = datetime(2025, 12, 2)

        # Parse and validate dates
        try:
            start_str = fix_date(start_str)
            end_str = fix_date(end_str)
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
        except Exception as e:
            raise ValueError("Invalid date format. Use YYYY-MM-DD (e.g. 2023-01-01).") from e

        if start > end:
            raise ValueError("Start date must be earlier than or equal to end date.")

        # Enforce fixed allowed date range
        if start < MIN_DATE or end > MAX_DATE:
            raise ValueError(
                f"Dates must be between {MIN_DATE.date()} and {MAX_DATE.date()}."
            )

        # Apply filter and ensure there is data
        mask = (self.df["CRASH DATE"] >= start) & (self.df["CRASH DATE"] <= end)
        self.filtered_df = self.df.loc[mask].copy().reset_index(drop=True)

        if len(self.filtered_df) == 0:
            min_d = self.df["CRASH DATE"].min()
            max_d = self.df["CRASH DATE"].max()
            raise ValueError(
                f"Selected date range contains no records.\n"
                f"Available dataset range: {min_d.date()} to {max_d.date()}"
            )

        # Summary of applied filter
        print("\n Filter Applied:")
        print(f"  Date Range: {start_str}  -  {end_str}")
        print(f"  Rows Included: {len(self.filtered_df):,}\n")

    # =========================
    # SAFE HELPERS
    # =========================
    def _safe_sum(self, column):
        """Return integer sum of a numeric column in filtered_df, 0 if missing."""
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return 0
        return int(pd.to_numeric(self.filtered_df[column], errors="coerce").fillna(0).sum())

    def _safe_value_counts_top(self, column):
        """Return (most_common_value, count) for a column, or (None,0) if unavailable."""
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return (None, 0)
        vc = self.filtered_df[column].fillna("(unknown)").value_counts()
        if len(vc) == 0:
            return (None, 0)
        return (vc.index[0], int(vc.iloc[0]))

    def _safe_value_counts_bottom(self, column):
        """Return (least_common_value, count) for a column, or (None,0) if unavailable."""
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return (None, 0)
        vc = self.filtered_df[column].fillna("(unknown)").value_counts()
        if len(vc) == 0:
            return (None, 0)
        return (vc.index[-1], int(vc.iloc[-1]))

    # =========================
    # ANALYSIS FUNCTIONS
    # =========================
    def total_injured(self):
        """Total persons injured in the filtered range."""
        return self._safe_sum("NUMBER OF PERSONS INJURED")

    def total_killed(self):
        """Total persons killed in the filtered range."""
        return self._safe_sum("NUMBER OF PERSONS KILLED")

    def injured_categories(self):
        """Breakdown of injuries by pedestrian, cyclist, motorist."""
        cols = [
            "NUMBER OF PEDESTRIANS INJURED",
            "NUMBER OF CYCLIST INJURED",
            "NUMBER OF MOTORIST INJURED"
        ]
        return {col: self._safe_sum(col) for col in cols}

    def killed_categories(self):
        """Breakdown of deaths by pedestrian, cyclist, motorist."""
        cols = [
            "NUMBER OF PEDESTRIANS KILLED",
            "NUMBER OF CYCLIST KILLED",
            "NUMBER OF MOTORIST KILLED"
        ]
        return {col: self._safe_sum(col) for col in cols}

    def highest_accident_street(self):
        """Street with the most recorded accidents."""
        return self._safe_value_counts_top("ON STREET NAME")

    def least_accident_street(self):
        """Street with the least recorded accidents (from value_counts ordering)."""
        return self._safe_value_counts_bottom("ON STREET NAME")

    def most_common_vehicle(self):
        """Most common vehicle type in incidents."""
        return self._safe_value_counts_top("VEHICLE TYPE CODE 1")

    def least_common_vehicle(self):
        """Least common vehicle type in incidents (from value_counts ordering)."""
        return self._safe_value_counts_bottom("VEHICLE TYPE CODE 1")

    def accidents_by_month(self):
        """Return a Series of accident counts indexed by month (YYYY-MM)."""
        if self.filtered_df is None:
            return pd.Series(dtype=int)
        df = self.filtered_df.copy()
        df["MONTH"] = df["CRASH DATE"].dt.to_period("M").astype(str)
        return df["MONTH"].value_counts().sort_index()

    # =========================
    # GRAPH GENERATION
    # =========================
    def create_graphs(self, out_prefix=""):
        """Create trend, bar chart, and vehicle pie chart. Return list of saved filenames."""
        if self.filtered_df is None or len(self.filtered_df) == 0:
            print("  No data available to generate graphs!")
            return []

        monthly = self.accidents_by_month()
        saved_files = []

        # Trend line over months
        plt.figure(figsize=(10, 5))
        monthly.plot(kind="line")
        plt.title("Accident Trend Over Time")
        plt.xlabel("Month")
        plt.ylabel("Accident Count")
        plt.tight_layout()
        fname = f"{out_prefix}trend_analysis.png"
        plt.savefig(fname)
        plt.close()
        saved_files.append(fname)

        # Bar chart of monthly accidents
        plt.figure(figsize=(10, 5))
        monthly.plot(kind="bar")
        plt.title("Accidents Per Month")
        plt.xlabel("Month")
        plt.ylabel("Accident Count")
        plt.tight_layout()
        fname = f"{out_prefix}accidents_per_month.png"
        plt.savefig(fname)
        plt.close()
        saved_files.append(fname)

        # Pie chart for top 10 vehicles (if available)
        if "VEHICLE TYPE CODE 1" in self.filtered_df.columns:
            vehicles = self.filtered_df["VEHICLE TYPE CODE 1"].fillna("(unknown)").value_counts().head(10)
            if len(vehicles) > 0:
                plt.figure(figsize=(12, 12))  # larger figure for readability
                vehicles.plot(kind="pie", autopct="%1.1f%%", startangle=90, labels=None)
                plt.title("Top 10 Most Common Vehicle Types")
                plt.legend(vehicles.index, loc="center left", bbox_to_anchor=(1, 0.5))
                plt.ylabel("")
                plt.tight_layout()
                fname = f"{out_prefix}top10_vehicles.png"
                plt.savefig(fname, bbox_inches='tight')
                plt.close()
                saved_files.append(fname)

        # Print summary of saved graphs
        print("\n  Graphs generated:")
        for f in saved_files:
            print(" ", f)

        return saved_files

    # =========================
    # SAVE ANALYSIS TO CSV
    # =========================
    def save_to_csv(self, report_dict, out_dir=".", prefix="analysis_report_"):
        """Save analysis sections to a CSV file with timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"{prefix}{timestamp}.csv")

        sections = []

        # Single-value metrics (non-dict) go in one section
        single_metrics = {k: v for k, v in report_dict.items() if not isinstance(v, dict)}
        if single_metrics:
            df_single = pd.DataFrame(list(single_metrics.items()), columns=["Metric", "Value"])
            sections.append(("Single Metrics", df_single))

        # Known dictionary sections are saved as tables
        if "Injured Categories" in report_dict:
            df_inj = pd.DataFrame(report_dict["Injured Categories"], index=[0])
            sections.append(("Injured Categories", df_inj))

        if "Killed Categories" in report_dict:
            df_kill = pd.DataFrame(report_dict["Killed Categories"], index=[0])
            sections.append(("Killed Categories", df_kill))

        if "Monthly Trend" in report_dict:
            monthly = report_dict["Monthly Trend"]
            if isinstance(monthly, dict):
                df_month = pd.DataFrame(list(monthly.items()), columns=["Month", "Accidents"])
            else:
                df_month = pd.DataFrame(monthly).reset_index()
                df_month.columns = ["Month", "Accidents"]
            sections.append(("Monthly Trend", df_month))

        # Write the assembled sections to CSV (as concatenated parts)
        with open(filename, "w", newline="", encoding="utf-8") as f:
            if not sections:
                f.write("No analysis results to save.\n")
            else:
                for i, (title, df) in enumerate(sections):
                    f.write(f"==== {title} ====\n")
                    df.to_csv(f, index=False)
                    if i < len(sections) - 1:
                        f.write("\n")

        print(f"\n  Report saved as: {filename}\n")
        return filename

    # =========================
    # SAVE FIXED CSV (PROFESSOR)
    # =========================
    def save_to_fixed_csv(self, report_dict, out_dir=".", filename="analysis_report.csv"):
        """Alternative simple CSV serializer: flattens dict sections into rows."""
        try:
            rows = []
            for key, value in report_dict.items():
                if isinstance(value, dict):
                    for subk, subv in value.items():
                        rows.append((f"{key} - {subk}", subv))
                elif isinstance(value, (list, tuple, pd.Series, pd.DataFrame)):
                    rows.append((key, str(value)))
                else:
                    rows.append((key, value))
            df = pd.DataFrame(rows, columns=["Metric", "Value"])
            outpath = os.path.join(out_dir, filename)
            df.to_csv(outpath, index=False)
            print(f"\n  Fixed report saved as: {outpath}\n")
            return outpath
        except Exception as e:
            print(f"  Failed to write fixed CSV: {e}")
            return None

    # =========================
    # PIE CHART FUNCTIONS
    # =========================
    def graph_top_10_streets(self, out_prefix=""):
        """Save a pie chart for the top 10 streets with accidents."""
        if self.filtered_df is None or "ON STREET NAME" not in self.filtered_df.columns:
            print("  ON STREET NAME column not available; cannot create street pie chart.")
            return None

        streets = self.filtered_df["ON STREET NAME"].fillna("(unknown)").value_counts().head(10)
        if len(streets) == 0:
            print("  No street data to plot.")
            return None

        plt.figure(figsize=(12, 8))
        streets.plot(kind="pie", autopct="%1.1f%%", startangle=140, labels=None, pctdistance=0.85)
        plt.title("Top 10 Streets With Most Accidents")
        plt.ylabel("")
        plt.legend(streets.index, loc="center left", bbox_to_anchor=(1, 0.5))
        plt.tight_layout()
        fname = f"{out_prefix}top10_streets.png"
        plt.savefig(fname, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {fname}")
        return fname

    def graph_top_10_vehicles(self, out_prefix=""):
        """Save a pie chart for the top 10 vehicle types."""
        if self.filtered_df is None or "VEHICLE TYPE CODE 1" not in self.filtered_df.columns:
            print("  VEHICLE TYPE CODE 1 column not available; cannot create vehicle pie chart.")
            return None

        vehicles = self.filtered_df["VEHICLE TYPE CODE 1"].fillna("(unknown)").value_counts().head(10)
        if len(vehicles) == 0:
            print("  No vehicle data to plot.")
            return None

        plt.figure(figsize=(12, 8))
        vehicles.plot(kind="pie", autopct="%1.1f%%", startangle=140, labels=None, pctdistance=0.85)
        plt.title("Top 10 Most Common Vehicle Types")
        plt.ylabel("")
        plt.legend(vehicles.index, loc="center left", bbox_to_anchor=(1, 0.5))
        plt.tight_layout()
        fname = f"{out_prefix}top10_vehicles.png"
        plt.savefig(fname, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {fname}")
        return fname

    def graph_top_10_contributing_factors(self, out_prefix=""):
        """Save a pie chart for the top 10 contributing factors to collisions."""
        if self.filtered_df is None:
            print("  No filtered data; cannot create contributing factors pie chart.")
            return None

        col = "CONTRIBUTING FACTOR VEHICLE 1"
        if col not in self.filtered_df.columns:
            print(f"  Column '{col}' not found; cannot create contributing factors pie chart.")
            return None

        factors = self.filtered_df[col].fillna("(unknown)").value_counts().head(10)
        if len(factors) == 0:
            print("  No contributing factor data to plot.")
            return None

        plt.figure(figsize=(12, 8))
        factors.plot(kind="pie", autopct="%1.1f%%", startangle=140, labels=None, pctdistance=0.85)
        plt.title("Top 10 Contributing Factors")
        plt.ylabel("")
        plt.legend(factors.index, loc="center left", bbox_to_anchor=(1, 0.5))
        plt.tight_layout()
        fname = f"{out_prefix}top10_contributing_factors.png"
        plt.savefig(fname, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {fname}")
        return fname


# =======================
# MAIN PROGRAM HELPERS
# =======================
def run_all_analyses(analyzer):
    """Run all main analyses and return collected results as a dict."""
    results = {}
    results["Total Injured"] = analyzer.total_injured()
    results["Total Killed"] = analyzer.total_killed()
    results["Injured Categories"] = analyzer.injured_categories()
    results["Killed Categories"] = analyzer.killed_categories()

    street1, count1 = analyzer.highest_accident_street()
    street2, count2 = analyzer.least_accident_street()
    results["Highest Accident Street"] = f"{street1} ({count1})" if street1 else "N/A"
    results["Least Accident Street"] = f"{street2} ({count2})" if street2 else "N/A"

    veh1, cnt1 = analyzer.most_common_vehicle()
    veh2, cnt2 = analyzer.least_common_vehicle()
    results["Most Common Vehicle"] = f"{veh1} ({cnt1})" if veh1 else "N/A"
    results["Least Common Vehicle"] = f"{veh2} ({cnt2})" if veh2 else "N/A"

    results["Monthly Trend"] = analyzer.accidents_by_month().to_dict()
    return results


# =======================
# GUI WRAPPER
# =======================
def launch_gui():
    if not TK_AVAILABLE:
        print("Tkinter is not available in this Python environment.")
        return

    root = tk.Tk()
    root.title("NYC Collision Analyzer (GUI)")

    analyzer_container = {"analyzer": None, "results": None}

    def gui_log(msg):
        txt_results.configure(state="normal")
        txt_results.insert("end", msg + "\n")
        txt_results.see("end")
        txt_results.configure(state="disabled")

    def load_csv_action():
        # Always load fixed MVCC_final next to this script
        try:
            analyzer = CollisionAnalyzer()
            analyzer_container["analyzer"] = analyzer
            gui_log("Loaded dataset: MVCC_fina.csv (fixed file)")
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            gui_log(f"ERROR loading dataset: {e}")

    def set_date_and_filter():
        analyzer = analyzer_container.get("analyzer")
        if analyzer is None:
            messagebox.showwarning("Not loaded", "Load the fixed MVCC_final.csv file first.")
            return False
        s = ent_start.get().strip()
        e = ent_end.get().strip()
        try:
            analyzer.set_date_range(s, e)
            gui_log(f"Date range set: {s} - {e}  (rows: {len(analyzer.filtered_df)})")
            return True
        except Exception as ex:
            messagebox.showerror("Date error", str(ex))
            gui_log(f"Date error: {ex}")
            return False

    def run_all_action():
        if not set_date_and_filter():
            return
        analyzer = analyzer_container["analyzer"]
        gui_log("Running all analyses...")
        try:
            results = run_all_analyses(analyzer)
            analyzer_container["results"] = results
            # display results
            gui_log("=== Analysis Results ===")
            for k, v in results.items():
                gui_log(f"{k}: {v}")
            gui_log("=== End Results ===")
        except Exception as ex:
            gui_log(f"Analysis error: {ex}")
            messagebox.showerror("Analysis error", str(ex))

    def generate_graphs_action():
        if not set_date_and_filter():
            return
        analyzer = analyzer_container["analyzer"]
        outdir = filedialog.askdirectory(title="Select output directory for graphs") or "."
        prefix = os.path.join(outdir, "")
        try:
            files = analyzer.create_graphs(out_prefix=prefix)
            if files:
                gui_log("Generated graphs:")
                for f in files:
                    gui_log(f"  {f}")
                messagebox.showinfo("Graphs", f"Saved {len(files)} graphs to {outdir}")
            else:
                gui_log("No graphs generated.")
        except Exception as ex:
            gui_log(f"Graph error: {ex}")
            messagebox.showerror("Graph error", str(ex))

    def save_report_action():
        results = analyzer_container.get("results")
        if not results:
            messagebox.showwarning("No results", "Run analyses (Run All) before saving a report.")
            return
        outdir = filedialog.askdirectory(title="Select output directory for report") or "."
        try:
            path = analyzer_container["analyzer"].save_to_csv(results, out_dir=outdir)
            gui_log(f"Report saved: {path}")
            messagebox.showinfo("Saved", f"Report saved: {path}")
        except Exception as ex:
            gui_log(f"Save error: {ex}")
            messagebox.showerror("Save error", str(ex))

    # --- Layout
    frm_top = ttk.Frame(root, padding=8)
    frm_top.pack(fill="x")

    ttk.Label(frm_top, text="CSV File:").grid(row=0, column=0, sticky="w")
    # show fixed filename (no browsing)
    lbl_fixed = ttk.Label(frm_top, text="MVCC_final.csv (fixed)")
    lbl_fixed.grid(row=0, column=1, sticky="w", padx=4)
    btn_load = ttk.Button(frm_top, text="Load MVCC_final.csv", command=load_csv_action)
    btn_load.grid(row=0, column=3, padx=4)

    frm_dates = ttk.Frame(root, padding=8)
    frm_dates.pack(fill="x")
    ttk.Label(frm_dates, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
    ent_start = ttk.Entry(frm_dates, width=15)
    ent_start.grid(row=0, column=1, padx=4, sticky="w")
    ent_start.insert(0, "2023-01-01")
    ttk.Label(frm_dates, text="End Date (YYYY-MM-DD):").grid(row=0, column=2, sticky="w")
    ent_end = ttk.Entry(frm_dates, width=15)
    ent_end.grid(row=0, column=3, padx=4, sticky="w")
    ent_end.insert(0, "2025-12-02")
    btn_set_date = ttk.Button(frm_dates, text="Apply Date Range", command=set_date_and_filter)
    btn_set_date.grid(row=0, column=4, padx=6)

    frm_buttons = ttk.Frame(root, padding=8)
    frm_buttons.pack(fill="x")
    btn_run_all = ttk.Button(frm_buttons, text="Run All Analyses", command=run_all_action)
    btn_run_all.grid(row=0, column=0, padx=4)
    btn_graphs = ttk.Button(frm_buttons, text="Generate Graphs", command=generate_graphs_action)
    btn_graphs.grid(row=0, column=1, padx=4)
    btn_save = ttk.Button(frm_buttons, text="Save Last Report", command=save_report_action)
    btn_save.grid(row=0, column=2, padx=4)
    btn_exit = ttk.Button(frm_buttons, text="Exit", command=root.destroy)
    btn_exit.grid(row=0, column=3, padx=4)

    frm_results = ttk.Frame(root, padding=8)
    frm_results.pack(fill="both", expand=True)
    ttk.Label(frm_results, text="Status / Results:").pack(anchor="w")
    txt_results = tk.Text(frm_results, height=20, wrap="word", state="disabled")
    txt_results.pack(fill="both", expand=True)

    root.mainloop()


# =======================
# ORIGINAL CLI MAIN (unchanged)
# =======================
def main_cli():
    """Interactive CLI: load dataset, ask date range, and run chosen analyses."""
    print("------------------------------------------")
    print("       NYC COLLISION ANALYZER TOOL        ")
    print("------------------------------------------\n")

    try:
        analyzer = CollisionAnalyzer("MVCC_final.csv")
    except Exception as e:
        print("ERROR loading dataset:", e)
        sys.exit(1)

    # Prompt user for date range within allowed bounds
    print("Enter date range (from: 2023-01-01 to: 2025-12-02)\n")
    while True:
        try:
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date   (YYYY-MM-DD): ").strip()
            analyzer.set_date_range(start, end)
            break
        except Exception as e:
            print("Invalid input:", e)
            print("Please try again.\n")

    # Main menu options summary
    print("""
1. Total Injured
2. Total Killed
3. Injured Categories
4. Killed Categories
5. Street With Most Accidents
6. Street With Least Accidents
7. Most Common Vehicle
8. Least Common Vehicle
9. Monthly Trend
10. Generate Graphs
11. Run ALL analyses
12. Pie Chart: Top 10 Streets With Most Accidents
13. Pie Chart: Top 10 Most Common Vehicle Types
14. Pie Chart: Top 10 Contributing Factors
0. Exit
""")

    # Loop to accept multiple choices per run
    while True:
        choices = input("\nEnter choices (e.g., 1,2,3 or 11) or 0 to exit: ").split(",")
        choices = [c.strip() for c in choices if c.strip()]
        if not choices:
            print("No option selected, please enter at least one choice or 0 to exit.")
            continue

        if len(choices) == 1 and choices[0] == "0":
            print("Exiting.")
            break

        results = {}
        graphs_generated = []

        # Process each selected option
        for choice in choices:
            if choice == "1":
                results["Total Injured"] = analyzer.total_injured()
                print("  Total Injured computed.")
            elif choice == "2":
                results["Total Killed"] = analyzer.total_killed()
                print("  Total Killed computed.")
            elif choice == "3":
                results["Injured Categories"] = analyzer.injured_categories()
                print("  Injured Categories computed.")
            elif choice == "4":
                results["Killed Categories"] = analyzer.killed_categories()
                print("  Killed Categories computed.")
            elif choice == "5":
                street, cnt = analyzer.highest_accident_street()
                results["Highest Accident Street"] = f"{street} ({cnt})" if street else "N/A"
                print(f"  Street With Most Accidents: {results['Highest Accident Street']}")
            elif choice == "6":
                street, cnt = analyzer.least_accident_street()
                results["Least Accident Street"] = f"{street} ({cnt})" if street else "N/A"
                print(f"  Street With Least Accidents: {results['Least Accident Street']}")
            elif choice == "7":
                veh, cnt = analyzer.most_common_vehicle()
                results["Most Common Vehicle"] = f"{veh} ({cnt})" if veh else "N/A"
                print(f"  Most Common Vehicle: {results['Most Common Vehicle']}")
            elif choice == "8":
                veh, cnt = analyzer.least_common_vehicle()
                results["Least Common Vehicle"] = f"{veh} ({cnt})" if veh else "N/A"
                print(f"  Least Common Vehicle: {results['Least Common Vehicle']}")
            elif choice == "9":
                results["Monthly Trend"] = analyzer.accidents_by_month().to_dict()
                print("  Monthly Trend computed.")
            elif choice == "10":
                print("\nRunning: Option 10 - Generate Graphs (graphs only).")
                graphs_generated = analyzer.create_graphs()
            elif choice == "11":
                print("\nRunning: Option 11 - ALL analyses.")
                results = run_all_analyses(analyzer)
                graphs_generated = analyzer.create_graphs()
                analyzer.graph_top_10_streets()
                analyzer.graph_top_10_vehicles()
                analyzer.graph_top_10_contributing_factors()
            elif choice == "12":
                analyzer.graph_top_10_streets()
            elif choice == "13":
                analyzer.graph_top_10_vehicles()
            elif choice == "14":
                analyzer.graph_top_10_contributing_factors()
            else:
                print(f"Unknown option: {choice}")

        # Save numeric/text results if any were produced
        if results:
            csv_path = analyzer.save_to_csv(results)
            print(f"Results written to: {csv_path}")
        elif graphs_generated:
            print("\nGraphs generated, no numeric results to save.")
        else:
            print("\nNo results to save.")

        # Ask whether to run another query within same session
        cont = input("\nRun another query? (y/n): ").strip().lower()
        if cont not in ("y", "yes"):
            print("Exiting.")
            break

    print("\n--------------------------------------")
    print("        ANALYSIS COMPLETE!")
    print("--------------------------------------\n")


if __name__ == "__main__":
    # Choose GUI by default, CLI only when --cli provided
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        try:
            while True:
                main_cli()
                cont = input("\nStart a new session and change date range? (y/n): ").strip().lower()
                if cont not in ("y", "yes"):
                    print("Exiting.")
                    break
        except KeyboardInterrupt:
            print("\nExiting.")
            try:
                sys.exit(0)
            except Exception:
                pass
    else:
        launch_gui()
