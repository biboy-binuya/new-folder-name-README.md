import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any

def launch_gui():
    root = tk.Tk()
    root.title("NYC Collision Analyzer")

    analyzer_container = {"analyzer": None, "results": None}
    ui = {}

    # ---------- Helper / Callback functions ----------
    def gui_log(msg: str) -> None:
        """Logs messages in the result text area."""
        txt_results.config(state="normal")
        txt_results.insert("end", msg + "\n")
        txt_results.config(state="disabled")
        txt_results.see("end")

    def load_csv_action() -> None:
        """Loads the CSV file into the analyzer."""
        try:
            analyzer = CollisionAnalyzer()  # analyzer: newly created CollisionAnalyzer object
            analyzer_container["analyzer"] = analyzer
            gui_log("Loaded dataset: MVCC_final.csv (fixed file)")
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            gui_log(f"ERROR loading dataset: {e}")

    def set_date_and_filter() -> bool:
        """Sets the date range and filters the dataset."""
        analyzer = analyzer_container.get("analyzer")
        if analyzer is None:
            messagebox.showwarning("Not loaded", "Load the dataset first.")
            return False

        s = ent_start.get().strip()  # Get start date
        e = ent_end.get().strip()  # Get end date

        try:
            analyzer.set_date_range(s, e)  # Set the date range
            gui_log(f"Date range set: {s} - {e} (rows: {len(analyzer.filtered_df)})")
            return True
        except Exception as ex:
            messagebox.showerror("Date error", str(ex))
            gui_log(f"Date error: {ex}")
            return False

    def run_all_action() -> None:
        """Runs all analyses and logs the results."""
        if not set_date_and_filter():  # Ensure date filter is set
            return
        analyzer = analyzer_container["analyzer"]
        gui_log("Running all analyses...")
        try:
            results = run_all_analyses(analyzer)  # Run all analyses
            analyzer_container["results"] = results
            gui_log("=== Analysis Results ===")
            for k, v in results.items():
                gui_log(f"{k}: {v}")
            gui_log("=== End Results ===")
        except Exception as ex:
            gui_log(f"Analysis error: {ex}")
            messagebox.showerror("Analysis error", str(ex))

    def generate_graphs_action() -> None:
        """Generates and saves the analysis graphs."""
        if not set_date_and_filter():  # Ensure date filter is set
            return
        analyzer = analyzer_container["analyzer"]
        outdir = filedialog.askdirectory(title="Select output directory for graphs") or "."  # Directory to save graphs
        prefix = os.path.join(outdir, "")  # Prefix for filenames
        try:
            files = analyzer.create_graphs(out_prefix=prefix)  # Generate graphs
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
        """Saves the current analysis results to a CSV report."""
        results = analyzer_container.get("results")  # Get the last computed results
        if not results:
            messagebox.showwarning("No results", "Run analyses (Run All) before saving a report.")
            return
        outdir = filedialog.askdirectory(title="Select output directory for report") or "."  # Choose output directory
        try:
            path = analyzer_container["analyzer"].save_to_csv(results, out_dir=outdir)  # Save to CSV
            gui_log(f"Report saved: {path}")
            messagebox.showinfo("Saved", f"Report saved: {path}")
        except Exception as ex:
            gui_log(f"Save error: {ex}")
            messagebox.showerror("Save error", str(ex))

    # ---------- GUI Layout ----------
    frm_top = ttk.Frame(root, padding=8)
    frm_top.pack(fill="x")
    ttk.Label(frm_top, text="CSV File:").grid(row=0, column=0, sticky="w")
    ttk.Label(frm_top, text=".csv (fixed)").grid(row=0, column=1, sticky="w", padx=4)
    ttk.Button(frm_top, text="Load MVCC_final.csv", command=load_csv_action).grid(row=0, column=3, padx=4)

    # Date range entry
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

    ttk.Button(frm_dates, text="Apply Date Range", command=set_date_and_filter).grid(row=0, column=4, padx=6)

    # Action buttons
    frm_buttons = ttk.Frame(root, padding=8)
    frm_buttons.pack(fill="x")
    ttk.Button(frm_buttons, text="Run All Analyses", command=run_all_action).grid(row=0, column=0, padx=4)
    ttk.Button(frm_buttons, text="Generate Graphs", command=generate_graphs_action).grid(row=0, column=1, padx=4)
    ttk.Button(frm_buttons, text="Save Last Report", command=save_report_action).grid(row=0, column=2, padx=4)
    ttk.Button(frm_buttons, text="Exit", command=root.destroy).grid(row=0, column=3, padx=4)

    # Options for the listbox (1..12)
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
    ]

    frm_options = ttk.Frame(root, padding=8)
    frm_options.pack(fill="both")
    ttk.Label(frm_options, text="Options (select one or more):").pack(anchor="w")
    listbox_options = tk.Listbox(frm_options, height=12, selectmode="multiple")
    for opt in OPTIONS:
        listbox_options.insert("end", opt)
    listbox_options.pack(fill="x")
    ttk.Button(frm_options, text="Run Selected Options", command=lambda: run_selected_action(listbox_options, analyzer_container)).pack(pady=4, anchor="e")

    # Results text area
    frm_results = ttk.Frame(root, padding=8)
    frm_results.pack(fill="both", expand=True)
    ttk.Label(frm_results, text="Status / Results:").pack(anchor="w")
    txt_results = tk.Text(frm_results, height=20, wrap="word", state="disabled")
    txt_results.pack(fill="both", expand=True)

    root.mainloop()

# Add this helper for selected options
def run_selected_action(listbox_options, analyzer_container):
    """Handle the selected options from the listbox."""
    selected = listbox_options.curselection()
    analyzer = analyzer_container.get("analyzer")
    if not selected or analyzer is None:
        return
    # For simplicity, just log the selected options here
    for idx in selected:
        gui_log(f"Option {idx + 1} selected")
