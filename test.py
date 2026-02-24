"""NYC Collision Analyzer Tool"""
# -----------------------
# Imports
# -----------------------
from __future__ import annotations
import os  # os module for filesystem operations
import sys  # sys module for CLI args and exiting
from datetime import datetime  # datetime class for date parsing/comparison
from typing import Dict, List, Optional, Tuple, Any  # typing helpers

import pandas as pd  # pd: pandas for DataFrame handling
import matplotlib.pyplot as plt  # plt: matplotlib pyplot for plotting
from matplotlib.widgets import Button

# show_figure_with_save is defined after tkinter import (uses filedialog/messagebox).

try:  # optional GUI
    import tkinter as tk  # tk: tkinter root and widgets
    from tkinter import ttk, filedialog, messagebox  # ttk: themed widgets, filedialog, messagebox
    TK_AVAILABLE = True  # TK_AVAILABLE: whether tkinter import succeeded
except Exception:
    TK_AVAILABLE = False  # TK_AVAILABLE: fallback when tkinter not available

# -----------------------
# Constants
# -----------------------
FIXED_CSV_NAME = "MVCC_final.csv"  # default CSV filename expected next to script
MIN_DATE = datetime(2023, 1, 1)  # MIN_DATE: earliest allowed analysis date
MAX_DATE = datetime(2025, 12, 2)  # MAX_DATE: latest allowed analysis date

def show_figure_with_save(fig, default_name="chart.png"):
    """Show matplotlib figure with a Save button when tkinter is available, otherwise fallback to plt.show()."""
    if not TK_AVAILABLE:
        plt.show()
        return

    ax_save = fig.add_axes([0.8, 0.01, 0.15, 0.06])  # x, y, w, h
    btn_save = Button(ax_save, "Save")

    def save_event(event):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG Image", "*.png")]
        )
        if path:
            fig.savefig(path, bbox_inches="tight")
            messagebox.showinfo("Saved", f"Chart saved to:\n{path}")

    btn_save.on_clicked(save_event)
    plt.show()


def normalize_date_input(d: str) -> str:
    """Normalize common date separators and zero-pad month/day."""
    d = d.strip().replace("/", "-").replace(" ", "-")  # d: normalized input string
    parts = d.split("-")  # parts: list of date components
    if len(parts) == 3:
        y, m, da = parts[0], parts[1].zfill(2), parts[2].zfill(2)  # y: year, m: month (zero-padded), da: day (zero-padded)
        return f"{y}-{m}-{da}"
    return d


def ensure_dir(path: str) -> str:
    """Return a directory path, defaulting to '.' if empty."""
    # path: user-provided directory string; returns path or "." if empty
    return path if path else "."


def script_path() -> str:
    """Return directory containing this script (robust for frozen apps)."""
    # returns: directory containing this source file
    return os.path.dirname(os.path.abspath(__file__))


# -----------------------
# CollisionAnalyzer
# -----------------------
class CollisionAnalyzer:
    """Load NYC collision CSV and provide analysis utilities."""

    def __init__(self, csv_file: Optional[str] = None) -> None:
        # csv_file: optional path provided by caller (ignored; fixed file next to script used)
        csv_file = csv_file or FIXED_CSV_NAME
        # force use of fixed CSV next to script
        csv_file = os.path.join(script_path(), FIXED_CSV_NAME)  # csv_file: full path to fixed CSV

        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Read dataset
        self.df: pd.DataFrame = pd.read_csv(csv_file, low_memory=False)  # self.df: master dataframe loaded from CSV
        if "CRASH DATE" not in self.df.columns:
            raise KeyError("Required column 'CRASH DATE' not found in dataset.")
        self.df["CRASH DATE"] = pd.to_datetime(self.df["CRASH DATE"], errors="coerce")  # convert crash date to datetime
        self.df = self.df.dropna(subset=["CRASH DATE"]).reset_index(drop=True)  # drop rows without crash date

        # working (filtered) view
        self.filtered_df: Optional[pd.DataFrame] = None  # self.filtered_df: filtered dataframe for selected date range

    # ---- date range filtering ----
    def set_date_range(self, start_str: str, end_str: str) -> None:
        # start_str: start date string from user; end_str: end date string from user
        start_str = normalize_date_input(start_str)
        end_str = normalize_date_input(end_str)
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d")  # start: parsed datetime for range start
            end = datetime.strptime(end_str, "%Y-%m-%d")  # end: parsed datetime for range end
        except Exception as e:
            raise ValueError("Invalid date format. Use YYYY-MM-DD (e.g. 2023-01-01).") from e

        if start > end:
            raise ValueError("Start date must be earlier than or equal to end date.")
        if start < MIN_DATE or end > MAX_DATE:
            raise ValueError(f"Dates must be between {MIN_DATE.date()} and {MAX_DATE.date()}.")

        mask = (self.df["CRASH DATE"] >= start) & (self.df["CRASH DATE"] <= end)  # mask: boolean mask for rows in range
        self.filtered_df = self.df.loc[mask].copy().reset_index(drop=True)  # self.filtered_df: filtered subset for analysis
        if self.filtered_df.empty:
            min_d = self.df["CRASH DATE"].min()  # min_d: earliest date in full dataset
            max_d = self.df["CRASH DATE"].max()  # max_d: latest date in full dataset
            raise ValueError(
                f"Selected date range contains no records.\n"
                f"Available dataset range: {min_d.date()} to {max_d.date()}"
            )

    # ---- safe helpers ----
    def _safe_sum(self, column: str) -> int:
        # column: column name to sum safely in filtered_df
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return 0
        return int(pd.to_numeric(self.filtered_df[column], errors="coerce").fillna(0).sum())

    def _safe_value_counts_top(self, column: str) -> Tuple[Optional[str], int]:
        # column: column name for value counts; returns (most_common_value, count)
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return None, 0
        vc = self.filtered_df[column].fillna("(unknown)").value_counts()  # vc: value counts Series
        if vc.empty:
            return None, 0
        return str(vc.index[0]), int(vc.iloc[0])

    def _safe_value_counts_bottom(self, column: str) -> Tuple[Optional[str], int]:
        # column: column name for value counts; returns (least_common_value, count)
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return None, 0
        vc = self.filtered_df[column].fillna("(unknown)").value_counts()  # vc: value counts Series
        if vc.empty:
            return None, 0
        return str(vc.index[-1]), int(vc.iloc[-1])

    # ---- analysis API ----
    def total_injured(self) -> int:
        # returns total number of injured persons in filtered_df
        return self._safe_sum("NUMBER OF PERSONS INJURED")

    def total_killed(self) -> int:
        # returns total number of killed persons in filtered_df
        return self._safe_sum("NUMBER OF PERSONS KILLED")

    def injured_categories(self) -> Dict[str, int]:
        # returns dict of injured counts by category columns
        cols = [
            "NUMBER OF PEDESTRIANS INJURED",
            "NUMBER OF CYCLIST INJURED",
            "NUMBER OF MOTORIST INJURED",
        ]
        return {c: self._safe_sum(c) for c in cols}

    def killed_categories(self) -> Dict[str, int]:
        # returns dict of killed counts by category columns
        cols = [
            "NUMBER OF PEDESTRIANS KILLED",
            "NUMBER OF CYCLIST KILLED",
            "NUMBER OF MOTORIST KILLED",
        ]
        return {c: self._safe_sum(c) for c in cols}

    def highest_accident_street(self) -> Tuple[Optional[str], int]:
        # returns (street_name, count) with the highest accidents
        return self._safe_value_counts_top("ON STREET NAME")

    def least_accident_street(self) -> Tuple[Optional[str], int]:
        # returns (street_name, count) with the least accidents
        return self._safe_value_counts_bottom("ON STREET NAME")

    def most_common_vehicle(self) -> Tuple[Optional[str], int]:
        # returns (vehicle_type, count) most common in filtered_df
        return self._safe_value_counts_top("VEHICLE TYPE CODE 1")

    def least_common_vehicle(self) -> Tuple[Optional[str], int]:
        # returns (vehicle_type, count) least common in filtered_df
        return self._safe_value_counts_bottom("VEHICLE TYPE CODE 1")

    def accidents_by_month(self) -> pd.Series:
        # returns a Series indexed by month string (YYYY-MM) with accident counts
        if self.filtered_df is None:
            return pd.Series(dtype=int)
        df = self.filtered_df.copy()  # df: local copy for derived calculations
        df["MONTH"] = df["CRASH DATE"].dt.to_period("M").astype(str)  # MONTH: derived month string column
        return df["MONTH"].value_counts().sort_index()

    # ---- graphing ----
    def create_graphs(self, out_prefix: str = "") -> List[str]:
        # out_prefix: directory/prefix to prepend to saved filenames; returns list of saved file paths
        if self.filtered_df is None or self.filtered_df.empty:
            return []
        saved: List[str] = []  # saved: list of saved image filenames
        monthly = self.accidents_by_month()  # monthly: Series of accidents per month

        # trend
        fig = plt.figure(figsize=(10, 5))
        monthly.plot(kind="line")
        plt.title("Accident Trend Over Time")
        plt.xlabel("Month")
        plt.ylabel("Accident Count")
        plt.tight_layout()
        fname = f"{out_prefix}trend_analysis.png"  # fname: filename for trend plot
        show_figure_with_save(fig, "top10_vehicles.png")

        saved.append(fname)

        # bar
        plt.figure(figsize=(10, 5))
        monthly.plot(kind="bar")
        plt.title("Accidents Per Month")
        plt.xlabel("Month")
        plt.ylabel("Accident Count")
        plt.tight_layout()
        fname = f"{out_prefix}accidents_per_month.png"  # fname: filename for bar plot
        plt.savefig(fname)
        plt.close()
        saved.append(fname)

        # vehicles pie (top10)
        if "VEHICLE TYPE CODE 1" in self.filtered_df.columns:
            vehicles = self.filtered_df["VEHICLE TYPE CODE 1"].fillna("(unknown)").value_counts().head(10)  # vehicles: top10 vehicle counts
            if not vehicles.empty:
                plt.figure(figsize=(12, 12))
                vehicles.plot(kind="pie", autopct="%1.1f%%", startangle=90, labels=None)
                plt.title("Top 10 Most Common Vehicle Types")
                plt.legend(vehicles.index, loc="center left", bbox_to_anchor=(1, 0.5))
                plt.tight_layout()
                fname = f"{out_prefix}top10_vehicles.png"  # fname: filename for vehicles pie
                plt.savefig(fname)
                plt.close()
                saved.append(fname)

        return saved

    # dedicated pie charts as class methods
def graph_top_10_streets(self) -> None:
    # 1. Guard clause
    if self.filtered_df is None:
        return

    # 2. Create streets INSIDE the function
    streets = (
        self.filtered_df["ON STREET NAME"]
        .fillna("(unknown)")
        .value_counts()
        .head(10)
    )

    # 3. Empty check
    if streets.empty:
        return

    # 4. Plot
    fig = plt.figure(figsize=(12, 8))
    streets.plot(
        kind="pie",
        autopct="%1.1f%%",
        startangle=140,
        labels=None,
        pctdistance=0.85
    )
    plt.title("Top 10 Streets With Most Accidents")
    plt.ylabel("")
    plt.legend(streets.index, loc="center left", bbox_to_anchor=(1, 0.5))
    plt.tight_layout()

    show_figure_with_save(fig, "top10_streets.png")




def graph_top_10_contributing_factors(self) -> None:
    col: str = "CONTRIBUTING FACTOR VEHICLE 1"

    # Guard clause
    if self.filtered_df is None or col not in self.filtered_df.columns:
        return

    factors = (
        self.filtered_df[col]
        .fillna("(unknown)")
        .value_counts()
        .head(10)
    )

    if factors.empty:
        return

    fig = plt.figure(figsize=(12, 8))
    factors.plot(
        kind="pie",
        autopct="%1.1f%%",
        startangle=140,
        labels=None,
        pctdistance=0.85
    )
    plt.title("Top 10 Contributing Factors")
    plt.ylabel("")
    plt.legend(factors.index, loc="center left", bbox_to_anchor=(1, 0.5))
    plt.tight_layout()

    show_figure_with_save(fig, "top10_contributing_factors.png")



    # ---- exporting ----
    def save_to_csv(self, report: Dict[str, Any], out_dir: str = ".", prefix: str = "analysis_report_") -> str:
        # report: analysis results dict to save; out_dir: output directory; prefix: filename prefix
        out_dir = ensure_dir(out_dir)  # out_dir: validated directory string
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # timestamp: time-based string for filename uniqueness
        outpath = os.path.join(out_dir, f"{prefix}{timestamp}.csv")  # outpath: full path for output CSV

        sections: List[Tuple[str, pd.DataFrame]] = []  # sections: list of (section title, DataFrame) to be written

        # single-value metrics
        singles = {k: v for k, v in report.items() if not isinstance(v, dict)}  # singles: flat key/value metrics
        if singles:
            df_single = pd.DataFrame(list(singles.items()), columns=["Metric", "Value"])  # df_single: DataFrame for single metrics
            sections.append(("Single Metrics", df_single))

        # known dict sections
        if "Injured Categories" in report and isinstance(report["Injured Categories"], dict):
            df_inj = pd.DataFrame(report["Injured Categories"], index=[0])  # df_inj: DataFrame for injured categories
            sections.append(("Injured Categories", df_inj))
        if "Killed Categories" in report and isinstance(report["Killed Categories"], dict):
            df_kill = pd.DataFrame(report["Killed Categories"], index=[0])  # df_kill: DataFrame for killed categories
            sections.append(("Killed Categories", df_kill))
        if "Monthly Trend" in report:
            monthly = report["Monthly Trend"]  # monthly: monthly trend data (dict or Series-like)
            if isinstance(monthly, dict):
                df_month = pd.DataFrame(list(monthly.items()), columns=["Month", "Accidents"])  # df_month: DataFrame from dict
            else:
                df_month = pd.DataFrame(monthly).reset_index()  # df_month: DataFrame created from Series-like
                df_month.columns = ["Month", "Accidents"]
            sections.append(("Monthly Trend", df_month))

        with open(outpath, "w", newline="", encoding="utf-8") as f:
            # f: file handle for writing CSV
            if not sections:
                f.write("No analysis results to save.\n")
            else:
                for i, (title, df) in enumerate(sections):
                    # i: loop index; title: section name; df: DataFrame for section
                    f.write(f"==== {title} ====\n")
                    df.to_csv(f, index=False)
                    if i < len(sections) - 1:
                        f.write("\n")

        return outpath  # returns path to saved CSV file


# -----------------------
# High-level helpers
# -----------------------
def run_all_analyses(analyzer: CollisionAnalyzer) -> Dict[str, Any]:
    # analyzer: CollisionAnalyzer instance to run analyses against
    results: Dict[str, Any] = {}  # results: dictionary to collect analysis outputs
    results["Total Injured"] = analyzer.total_injured()
    results["Total Killed"] = analyzer.total_killed()
    results["Injured Categories"] = analyzer.injured_categories()
    results["Killed Categories"] = analyzer.killed_categories()

    st1, c1 = analyzer.highest_accident_street()  # st1: top street name, c1: its count
    st2, c2 = analyzer.least_accident_street()  # st2: least street name, c2: its count
    results["Highest Accident Street"] = f"{st1} ({c1})" if st1 else "N/A"
    results["Least Accident Street"] = f"{st2} ({c2})" if st2 else "N/A"

    v1, vc1 = analyzer.most_common_vehicle()  # v1: most common vehicle, vc1: its count
    v2, vc2 = analyzer.least_common_vehicle()  # v2: least common vehicle, vc2: its count
    results["Most Common Vehicle"] = f"{v1} ({vc1})" if v1 else "N/A"
    results["Least Common Vehicle"] = f"{v2} ({vc2})" if v2 else "N/A"

    results["Monthly Trend"] = analyzer.accidents_by_month().to_dict()  # Monthly Trend: dict mapping month->count
    return results


def launch_gui():
    root = tk.Tk()
    root.title("NYC Collision Analyzer")

    analyzer_container = {"analyzer": None, "results": None}
    ui = {}

    # ---------- Frames ----------
    frm_options = ttk.Frame(root, padding=8)
    frm_options.pack(fill="both", expand=False)

    ttk.Label(frm_options, text="Options (select one or more):").pack(anchor="w")

    # ---------- Listbox ----------
    listbox_options = tk.Listbox(frm_options, height=12, selectmode="multiple")
    listbox_options.pack(fill="x")

    ui["listbox"] = listbox_options

    # ---------- Results ----------
    frm_results = ttk.Frame(root, padding=8)
    frm_results.pack(fill="both", expand=True)

    txt_results = tk.Text(frm_results, height=20, wrap="word", state="disabled")
    txt_results.pack(fill="both", expand=True)

    ui["results_text"] = txt_results

    root.mainloop()



# -----------------------
# GUI
# -----------------------
def launch_gui():
    root = tk.Tk()
    root.title("NYC Collision Analyzer")

    analyzer_container = {"analyzer": None, "results": None}
    ui = {}

    # ---------------- CALLBACKS ----------------
    def run_selected_action():
        if not set_date_and_filter():
            return

        analyzer = analyzer_container["analyzer"]
        sel = ui["listbox"].curselection()

        if not sel:
            messagebox.showwarning("No selection", "Select one or more options to run.")
            return

        choices = [str(i + 1) for i in sel]
        results: Dict[str, Any] = {}

        for choice in choices:
            if choice == "1":
                results["Total Injured"] = analyzer.total_injured()
            elif choice == "2":
                results["Total Killed"] = analyzer.total_killed()
            elif choice == "10":
                analyzer.graph_top_10_streets()

        if results:
            analyzer_container["results"] = results
            gui_log("=== Analysis Results ===")
            for k, v in results.items():
                gui_log(f"{k}: {v}")
            gui_log("=== End Results ===")

    # ---------------- WIDGETS ----------------
    frm_options = ttk.Frame(root, padding=8)
    frm_options.pack(fill="both")

    listbox_options = tk.Listbox(frm_options, height=12, selectmode="multiple")
    listbox_options.pack(fill="x")

    ui["listbox"] = listbox_options

    ttk.Button(
        frm_options,
        text="Run Selected Options",
        command=run_selected_action
    ).pack(pady=4)

    root.mainloop()





    root = tk.Tk()  # root: main Tk window
    root.title("NYC Collision Analyzer (GUI)")
    analyzer_container: Dict[str, Any] = {"analyzer": None, "results": None}
    # analyzer_container: holds current analyzer instance and last results for GUI callbacks

    def gui_log(msg: str) -> None:
        txt = ui["results_text"]
        txt.configure(state="normal")
        txt.insert("end", msg + "\n")
        txt.see("end")
        txt.configure(state="disabled")

    def load_csv_action() -> None:
        try:
            analyzer = CollisionAnalyzer()  # analyzer: newly created CollisionAnalyzer object
            analyzer_container["analyzer"] = analyzer
            gui_log("Loaded dataset: MVCC_final.csv (fixed file)")
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            gui_log(f"ERROR loading dataset: {e}")

    def set_date_and_filter() -> bool:
        analyzer = analyzer_container.get("analyzer")
        if analyzer is None:
            messagebox.showwarning("Not loaded", "Load the fixed MVCC_final.csv file first.")
        return False

    s = ui["ent_start"].get().strip()
    e = ui["ent_end"].get().strip()

    def set_date_and_filter() -> bool:
    analyzer = analyzer_container.get("analyzer")

    if analyzer is None:
        messagebox.showwarning("Not loaded", "Load the dataset first.")
        return False

    s = ent_start.get().strip()
    e = ent_end.get().strip()

    try:
        analyzer.set_date_range(s, e)
        gui_log(
            f"Date range set: {s} - {e} "
            f"(rows: {len(analyzer.filtered_df)})"
        )
        return True
    except Exception as ex:
        messagebox.showerror("Date error", str(ex))
        gui_log(f"Date error: {ex}")
        return False




    def run_all_action() -> None:
        if not set_date_and_filter():
            return
        analyzer = analyzer_container["analyzer"]
        gui_log("Running all analyses...")
        try:
            results = run_all_analyses(analyzer)  # results: dict of all computed metrics
            analyzer_container["results"] = results
            gui_log("=== Analysis Results ===")
            for k, v in results.items():
                gui_log(f"{k}: {v}")
            gui_log("=== End Results ===")
        except Exception as ex:
            gui_log(f"Analysis error: {ex}")
            messagebox.showerror("Analysis error", str(ex))

    def generate_graphs_action() -> None:
        if not set_date_and_filter():
            return
        analyzer = analyzer_container["analyzer"]
        outdir = filedialog.askdirectory(title="Select output directory for graphs") or "."  # outdir: directory chosen by user
        prefix = os.path.join(outdir, "")  # prefix: directory path string used as prefix for saved files
        try:
            files = analyzer.create_graphs(out_prefix=prefix)  # files: list of generated graph filenames
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

    def save_report_action() -> None:
        results = analyzer_container.get("results")  # results: last computed analysis results dict
        if not results:
            messagebox.showwarning("No results", "Run analyses (Run All) before saving a report.")
            return
        outdir = filedialog.askdirectory(title="Select output directory for report") or "."  # outdir: chosen save directory
        try:
            path = analyzer_container["analyzer"].save_to_csv(results, out_dir=outdir)  # path: saved CSV path
            gui_log(f"Report saved: {path}")
            messagebox.showinfo("Saved", f"Report saved: {path}")
        except Exception as ex:
            gui_log(f"Save error: {ex}")
            messagebox.showerror("Save error", str(ex))

# options for listbox (1..12)
OPTIONS = [
    "1. Total Injured",
    "2. Total Killed",
    "3. Injured Categories",
    "4. Killed Categories",
    "5. Monthly Trend",
    "6. Street With Most Accidents",
    "7. Street With Least Accidents",
    "8. Most Common Vehicle",
    "9. Least Common Vehicle",
    "10. Pie Chart: Top 10 Streets With Most Accidents",
    "11. Pie Chart: Top 10 Most Common Vehicle Types",
    "12. Pie Chart: Top 10 Contributing Factors",
]  # OPTIONS: list of selectable GUI options



# --- build layout ---
def launch_gui() -> None:
    root = tk.Tk()
    root.title("NYC Collision Analyzer")

    analyzer_container = {"analyzer": None, "results": None}

    # ---------- helper / callback functions ----------
    def gui_log(msg: str) -> None:
        txt_results.config(state="normal")
        txt_results.insert("end", msg + "\n")
        txt_results.config(state="disabled")
        txt_results.see("end")

    def load_csv_action(): ...
    def set_date_and_filter(): ...
    def run_all_action(): ...
    def generate_graphs_action(): ...
    def save_report_action(): ...
    def run_selected_action(): ...
    # -------------------------------------------------

    frm_top = ttk.Frame(root, padding=8)
    frm_top.pack(fill="x")
    ttk.Label(frm_top, text="CSV File:").grid(row=0, column=0, sticky="w")
    ttk.Label(frm_top, text=".csv (fixed)").grid(row=0, column=1, sticky="w", padx=4)
    ttk.Button(frm_top, text="Load MVCC_final.csv",
               command=load_csv_action).grid(row=0, column=3, padx=4)

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

    ttk.Button(frm_dates, text="Apply Date Range",
               command=set_date_and_filter).grid(row=0, column=4, padx=6)

    frm_buttons = ttk.Frame(root, padding=8)
    frm_buttons.pack(fill="x")
    ttk.Button(frm_buttons, text="Run All Analyses",
               command=run_all_action).grid(row=0, column=0, padx=4)
    ttk.Button(frm_buttons, text="Generate Graphs",
               command=generate_graphs_action).grid(row=0, column=1, padx=4)
    ttk.Button(frm_buttons, text="Save Last Report",
               command=save_report_action).grid(row=0, column=2, padx=4)
    ttk.Button(frm_buttons, text="Exit",
               command=root.destroy).grid(row=0, column=3, padx=4)

    frm_options = ttk.Frame(root, padding=8)
    frm_options.pack(fill="both")
    ttk.Label(frm_options, text="Options (select one or more):").pack(anchor="w")
    listbox_options = tk.Listbox(frm_options, height=12, selectmode="multiple")
    for opt in OPTIONS:
        listbox_options.insert("end", opt)
    listbox_options.pack(fill="x")
    ttk.Button(frm_options, text="Run Selected Options",
               command=run_selected_action).pack(pady=4, anchor="e")

    frm_results = ttk.Frame(root, padding=8)
    frm_results.pack(fill="both", expand=True)
    ttk.Label(frm_results, text="Status / Results:").pack(anchor="w")
    txt_results = tk.Text(frm_results, height=20, wrap="word", state="disabled")
    txt_results.pack(fill="both", expand=True)

    root.mainloop()


# -----------------------
# CLI
# -----------------------
def main_cli() -> None:
    print("------------------------------------------")
    print("       NYC COLLISION ANALYZER TOOL        ")
    print("------------------------------------------\n")

    try:
        analyzer = CollisionAnalyzer()  # analyzer: CollisionAnalyzer instance used for CLI session
    except Exception as e:
        print("ERROR loading dataset:", e)
        sys.exit(1)

    print("Enter date range (from: 2023-01-01 to: 2025-12-02)\n")
    while True:
        try:
            start = input("Start date (YYYY-MM-DD): ").strip()  # start: user-provided start date string
            end = input("End date   (YYYY-MM-DD): ").strip()  # end: user-provided end date string
            analyzer.set_date_range(start, end)
            break
        except Exception as e:
            print("Invalid input:", e)
            print("Please try again.\n")

    MENU = """
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
"""  # MENU: multiline string shown to the user
    print(MENU)

    while True:
        choices = input("\nEnter choices (e.g., 1,2,3 or 11) or 0 to exit: ").split(",")
        choices = [c.strip() for c in choices if c.strip()]  # choices: cleaned list of input choices
        if not choices:
            print("No option selected, please enter at least one choice or 0 to exit.")
            continue
        if len(choices) == 1 and choices[0] == "0":
            print("Exiting.")
            break

        results: Dict[str, Any] = {}  # results: dict to collect numeric results
        graphs_generated: List[str] = []  # graphs_generated: list to collect generated graph filenames

        for choice in choices:
            if choice == "1":
                results["Total Injured"] = analyzer.total_injured(); print("  Total Injured computed.")
            elif choice == "2":
                results["Total Killed"] = analyzer.total_killed(); print("  Total Killed computed.")
            elif choice == "3":
                results["Injured Categories"] = analyzer.injured_categories(); print("  Injured Categories computed.")
            elif choice == "4":
                results["Killed Categories"] = analyzer.killed_categories(); print("  Killed Categories computed.")
            elif choice == "5":
                st, cnt = analyzer.highest_accident_street(); results["Highest Accident Street"] = f"{st} ({cnt})" if st else "N/A"; print(f"  Street With Most Accidents: {results['Highest Accident Street']}")
            elif choice == "6":
                st, cnt = analyzer.least_accident_street(); results["Least Accident Street"] = f"{st} ({cnt})" if st else "N/A"; print(f"  Street With Least Accidents: {results['Least Accident Street']}")
            elif choice == "7":
                v, cnt = analyzer.most_common_vehicle(); results["Most Common Vehicle"] = f"{v} ({cnt})" if v else "N/A"; print(f"  Most Common Vehicle: {results['Most Common Vehicle']}")
            elif choice == "8":
                v, cnt = analyzer.least_common_vehicle(); results["Least Common Vehicle"] = f"{v} ({cnt})" if v else "N/A"; print(f"  Least Common Vehicle: {results['Least Common Vehicle']}")
            elif choice == "9":
                results["Monthly Trend"] = analyzer.accidents_by_month().to_dict(); print("  Monthly Trend computed.")
            elif choice == "10":
                print("\nRunning: Option 10 - Generate Graphs (graphs only).")
                graphs_generated = analyzer.create_graphs()  # graphs_generated: list of created graph filenames
            elif choice == "11":
                print("\nRunning: Option 11 - ALL analyses.")
                results = run_all_analyses(analyzer)  # results: dict with full analysis
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

        if results:
            csv_path = analyzer.save_to_csv(results)  # csv_path: path where report was saved
            print(f"Results written to: {csv_path}")
        elif graphs_generated:
            print("\nGraphs generated, no numeric results to save.")
        else:
            print("\nNo results to save.")

        cont = input("\nRun another query? (y/n): ").strip().lower()  # cont: user choice to continue
        if cont not in ("y", "yes"):
            print("Exiting.")
            break

    print("\n--------------------------------------")
    print("        ANALYSIS COMPLETE!")
    print("--------------------------------------\n")


# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        try:
            while True:
                main_cli()
                cont = input("\nStart a new session and change date range? (y/n): ").strip().lower()  # cont: whether to run another CLI session
                if cont not in ("y", "yes"):
                    break
        except KeyboardInterrupt:
            pass
    else:
        launch_gui()
