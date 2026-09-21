import os
import matplotlib.pyplot as plt
import pandas as pd
import xlrd


def process_tpr_data(input_file_path, output_excel_path, plot_image_path):
    # 1. Read raw sheet using xlrd
    workbook = xlrd.open_workbook(input_file_path)
    sheet = workbook.sheet_by_index(0)

    # 2. Extract Data Rows for Temperature vs TCD Signal (Columns 22 & 23 in raw block)
    data_rows = []
    for r in range(24, sheet.nrows):
        val_temp = sheet.cell_value(r, 22)
        val_tcd = sheet.cell_value(r, 23)
        if isinstance(val_temp, (int, float)) and isinstance(val_tcd, (int, float)):
            data_rows.append({"Temperature (°C)": val_temp, "TCD Signal (a.u.)": val_tcd})

    df = pd.DataFrame(data_rows)

    # 3. Calculate Key Metrics
    max_idx = df["TCD Signal (a.u.)"].idxmax()
    t_max = df.loc[max_idx, "Temperature (°C)"]
    signal_max = df.loc[max_idx, "TCD Signal (a.u.)"]

    summary_df = pd.DataFrame(
        [
            {"Metric": "Sample Name", "Value": "Inv95Cu5Zr 02.07.2026"},
            {"Metric": "Data Points Count", "Value": len(df)},
            {"Metric": "T_max (°C)", "Value": round(t_max, 2)},
            {"Metric": "Max TCD Signal (a.u.)", "Value": round(signal_max, 6)},
            {
                "Metric": "Min Temperature (°C)",
                "Value": round(df["Temperature (°C)"].min(), 2),
            },
            {
                "Metric": "Max Temperature (°C)",
                "Value": round(df["Temperature (°C)"].max(), 2),
            },
        ]
    )

    # 4. Generate Plot
    plt.figure(figsize=(10, 5))
    plt.plot(
        df["Temperature (°C)"],
        df["TCD Signal (a.u.)"],
        color="crimson",
        linewidth=1.5,
        label="TCD Signal",
    )
    plt.title(
        "TCD Signal (a.u.) vs. Temperature (°C)\nSample: Inv95Cu5Zr 02.07.2026",
        fontsize=12,
        pad=10,
    )
    plt.xlabel("Temperature (°C)", fontsize=11)
    plt.ylabel("TCD Signal (a.u.)", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(plot_image_path, dpi=300)
    plt.close()

    # 5. Export Ready-to-Download Excel File
    with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="TPR Data", index=False)

    print(f"Report generated successfully:\n- Excel: {output_excel_path}\n- Plot: {plot_image_path}")
    return df


# Example Execution
if __name__ == "__main__":
    input_file = "Inv 95Cu5ZrO2 02.07.26.xls"
    output_excel = "Inv95Cu5ZrO2_TPR_Report.xlsx"
    plot_file = "tcd_vs_temperature.png"

    process_tpr_data(input_file, output_excel, plot_file)
