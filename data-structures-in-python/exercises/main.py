"""
collision_analyzer.py

Usage:
    python collision_analyzer.py
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import sys
import os

# =======================
# COLLISION ANALYZER CLASS
# =======================
class CollisionAnalyzer:
    def __init__(self, csv_file="MVCC_final.csv"):
        print("\n------------------------------")
        print("   LOADING COLLISION DATASET  ")
        print("------------------------------\n")

        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Read dataset
        self.df = pd.read_csv(csv_file, low_memory=False)
        print("Dataset loaded successfully!\n")

        # Ensure crash date exists then parse and drop invalid
        if "CRASH DATE" not in self.df.columns:
            raise KeyError("Required column 'CRASH DATE' not found in dataset.")

        self.df["CRASH DATE"] = pd.to_datetime(self.df["CRASH DATE"], errors="coerce")
        self.df = self.df.dropna(subset=["CRASH DATE"]).reset_index(drop=True)

        self.filtered_df = None

    # =========================
    # DATE RANGE FILTER (HARD-LOCKED)
    # =========================
    def set_date_range(self, start_str, end_str):
        def fix_date(d):
            d = d.strip().replace("/", "-").replace(" ", "-")
            parts = d.split("-")
            if len(parts) == 3:
                y = parts[0]
                m = parts[1].zfill(2)
                da = parts[2].zfill(2)
                return f"{y}-{m}-{da}"
            return d

        # Hard-locked allowed range
        MIN_DATE = datetime(2023, 1, 1)
        MAX_DATE = datetime(2025, 12, 2)

        try:
            start_str = fix_date(start_str)
            end_str = fix_date(end_str)
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
        except Exception as e:
            raise ValueError("Invalid date format. Use YYYY-MM-DD (e.g. 2023-01-01).") from e

        if start > end:
            raise ValueError("Start date must be earlier than or equal to end date.")

        # Enforce hard-locked range
        if start < MIN_DATE or end > MAX_DATE:
            raise ValueError(
                f"Dates must be between {MIN_DATE.date()} and {MAX_DATE.date()}."
            )

        mask = (self.df["CRASH DATE"] >= start) & (self.df["CRASH DATE"] <= end)
        self.filtered_df = self.df.loc[mask].copy().reset_index(drop=True)

        if len(self.filtered_df) == 0:
            min_d = self.df["CRASH DATE"].min()
            max_d = self.df["CRASH DATE"].max()
            raise ValueError(
                f"Selected date range contains no records.\n"
                f"Available dataset range: {min_d.date()} to {max_d.date()}"
            )

        print("\n Filter Applied:")
        print(f"  Date Range: {start_str}  -  {end_str}")
        print(f"  Rows Included: {len(self.filtered_df):,}\n")

    # =========================
    # SAFE HELPERS
    # =========================
    def _safe_sum(self, column):
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return 0
        return int(pd.to_numeric(self.filtered_df[column], errors="coerce").fillna(0).sum())

    def _safe_value_counts_top(self, column):
        if self.filtered_df is None or column not in self.filtered_df.columns:
            return (None, 0)
        vc = self.filtered_df[column].fillna("(unknown)").value_counts()
        if len(vc) == 0:
            return (None, 0)
        return (vc.index[0], int(vc.iloc[0]))

    def _safe_value_counts_bottom(self, column):
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
        return self._safe_sum("NUMBER OF PERSONS INJURED")

    def total_killed(self):
        return self._safe_sum("NUMBER OF PERSONS KILLED")

    def injured_categories(self):
        cols = [
            "NUMBER OF PEDESTRIANS INJURED",
            "NUMBER OF CYCLIST INJURED",
            "NUMBER OF MOTORIST INJURED"
        ]
        return {col: self._safe_sum(col) for col in cols}

    def killed_categories(self):
        cols = [
            "NUMBER OF PEDESTRIANS KILLED",
            "NUMBER OF CYCLIST KILLED",
            "NUMBER OF MOTORIST KILLED"
        ]
        return {col: self._safe_sum(col) for col in cols}

    def highest_accident_street(self):
        return self._safe_value_counts_top("ON STREET NAME")

    def least_accident_street(self):
        return self._safe_value_counts_bottom("ON STREET NAME")

    def most_common_vehicle(self):
        return self._safe_value_counts_top("VEHICLE TYPE CODE 1")

    def least_common_vehicle(self):
        return self._safe_value_counts_bottom("VEHICLE TYPE CODE 1")

    def accidents_by_month(self):
        if self.filtered_df is None:
            return pd.Series(dtype=int)
        df = self.filtered_df.copy()
        df["MONTH"] = df["CRASH DATE"].dt.to_period("M").astype(str)
        return df["MONTH"].value_counts().sort_index()

    # =========================
    # GRAPH GENERATION
    # =========================
    def create_graphs(self, out_prefix=""):
        if self.filtered_df is None or len(self.filtered_df) == 0:
            print("  No data available to generate graphs!")
            return []

        monthly = self.accidents_by_month()
        saved_files = []

        # Trend Line
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

        # Bar Chart
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

        # Vehicle Pie Chart (top 10)
        if "VEHICLE TYPE CODE 1" in self.filtered_df.columns:
            vehicles = self.filtered_df["VEHICLE TYPE CODE 1"].fillna("(unknown)").value_counts().head(10)
            if len(vehicles) > 0:
                plt.figure(figsize=(8, 8))
                vehicles.plot(kind="pie", autopct="%1.1f%%", startangle=90)
                plt.title("Top 10 Vehicle Types Involved in Accidents")
                plt.tight_layout()
                fname = f"{out_prefix}vehicle_distribution.png"
                plt.savefig(fname)
                plt.close()
                saved_files.append(fname)

        print("\n  Graphs generated:")
        for f in saved_files:
            print(" ", f)

        return saved_files

    # =========================
    # SAVE ANALYSIS TO CSV
    # =========================
    def save_to_csv(self, report_dict, out_dir=".", prefix="analysis_report_"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"{prefix}{timestamp}.csv")

        sections = []

        # Single-value metrics (non dict values)
        single_metrics = {k: v for k, v in report_dict.items() if not isinstance(v, dict)}
        if single_metrics:
            df_single = pd.DataFrame(list(single_metrics.items()), columns=["Metric", "Value"])
            sections.append(("Single Metrics", df_single))

        # Known dict sections
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

        # Write CSV
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
        if self.filtered_df is None or "ON STREET NAME" not in self.filtered_df.columns:
            print("  ON STREET NAME column not available; cannot create street pie chart.")
            return None
        streets = self.filtered_df["ON STREET NAME"].fillna("(unknown)").value_counts().head(10)
        if len(streets) == 0:
            print("  No street data to plot.")
            return None
        plt.figure(figsize=(8, 8))
        streets.plot(kind="pie", autopct="%1.1f%%", startangle=90)
        plt.title("Top 10 Streets With Most Accidents")
        plt.ylabel("")
        plt.tight_layout()
        fname = f"{out_prefix}top10_streets.png"
        plt.savefig(fname)
        plt.close()
        print(f"  Saved: {fname}")
        return fname

    def graph_top_10_vehicles(self, out_prefix=""):
        if self.filtered_df is None or "VEHICLE TYPE CODE 1" not in self.filtered_df.columns:
            print("  VEHICLE TYPE CODE 1 column not available; cannot create vehicle pie chart.")
            return None
        vehicles = self.filtered_df["VEHICLE TYPE CODE 1"].fillna("(unknown)").value_counts().head(10)
        if len(vehicles) == 0:
            print("  No vehicle data to plot.")
            return None
        plt.figure(figsize=(8, 8))
        vehicles.plot(kind="pie", autopct="%1.1f%%", startangle=90)
        plt.title("Top 10 Most Common Vehicle Types")
        plt.ylabel("")
        plt.tight_layout()
        fname = f"{out_prefix}top10_vehicles.png"
        plt.savefig(fname)
        plt.close()
        print(f"  Saved: {fname}")
        return fname

    def graph_top_10_contributing_factors(self, out_prefix=""):
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
        plt.figure(figsize=(8, 8))
        factors.plot(kind="pie", autopct="%1.1f%%", startangle=90)
        plt.title("Top 10 Contributing Factors")
        plt.ylabel("")
        plt.tight_layout()
        fname = f"{out_prefix}top10_contributing_factors.png"
        plt.savefig(fname)
        plt.close()
        print(f"  Saved: {fname}")
        return fname


# =======================
# MAIN PROGRAM HELPERS
# =======================
def run_all_analyses(analyzer):
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
# MAIN PROGRAM
# =======================
def main():
    print("------------------------------------------")
    print("       NYC COLLISION ANALYZER TOOL        ")
    print("------------------------------------------\n")

    try:
        analyzer = CollisionAnalyzer("MVCC_final.csv")
    except Exception as e:
        print("ERROR loading dataset:", e)
        sys.exit(1)

    # Ask for date range (hard-locked)
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

    # Menu
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

        if results:
            csv_path = analyzer.save_to_csv(results)
            print(f"Results written to: {csv_path}")
        elif graphs_generated:
            print("\nGraphs generated, no numeric results to save.")
        else:
            print("\nNo results to save.")

        cont = input("\nRun another query? (y/n): ").strip().lower()
        if cont not in ("y", "yes"):
            print("Exiting.")
            break

    print("\n--------------------------------------")
    print("        ANALYSIS COMPLETE!")
    print("--------------------------------------\n")


if __name__ == "__main__":
    main()
    #fix pie chart appearance
    #seperate in different files
    