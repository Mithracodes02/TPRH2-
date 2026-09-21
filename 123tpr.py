import io
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import xlrd

st.set_page_config(page_title="TPR Data Processor", layout="wide")
st.title("TPR H2 Data Analysis & Report Generator")

# 1. File Uploader Component
uploaded_file = st.file_uploader(
    "Upload your raw TPR Excel file (.xls)", type=["xls", "xlsx"]
)

if uploaded_file is not None:
    try:
        # Read raw content into xlrd workbook from memory
        file_bytes = uploaded_file.read()
        workbook = xlrd.open_workbook(file_contents=file_bytes)
        sheet = workbook.sheet_by_index(0)

        # Extract Temperature & TCD Signal (Columns 22 and 23)
        data_rows = []
        for r in range(24, sheet.nrows):
            val_temp = sheet.cell_value(r, 22)
            val_tcd = sheet.cell_value(r, 23)
            if isinstance(val_temp, (int, float)) and isinstance(
                val_tcd, (int, float)
            ):
                data_rows.append(
                    {"Temperature (°C)": val_temp, "TCD Signal (a.u.)": val_tcd}
                )

        df = pd.DataFrame(data_rows)

        if not df.empty:
            # Metrics
            max_idx = df["TCD Signal (a.u.)"].idxmax()
            t_max = df.loc[max_idx, "Temperature (°C)"]
            signal_max = df.loc[max_idx, "TCD Signal (a.u.)"]

            col1, col2 = st.columns(2)
            col1.metric("T_max (°C)", f"{t_max:.2f}")
            col2.metric("Max TCD Signal", f"{signal_max:.6f}")

            # Plot
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                df["Temperature (°C)"],
                df["TCD Signal (a.u.)"],
                color="crimson",
                linewidth=1.5,
                label="TCD Signal",
            )
            ax.set_title(
                f"TCD Signal vs. Temperature ({uploaded_file.name})", pad=10
            )
            ax.set_xlabel("Temperature (°C)")
            ax.set_ylabel("TCD Signal (a.u.)")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend()
            st.pyplot(fig)

            # Generate Downloadable Excel Report in Memory
            summary_df = pd.DataFrame(
                [
                    {"Metric": "File Name", "Value": uploaded_file.name},
                    {"Metric": "Data Points Count", "Value": len(df)},
                    {"Metric": "T_max (°C)", "Value": round(t_max, 2)},
                    {
                        "Metric": "Max TCD Signal (a.u.)",
                        "Value": round(signal_max, 6),
                    },
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

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(
                excel_buffer, engine="openpyxl"
            ) as writer:
                summary_df.to_excel(
                    writer, sheet_name="Summary", index=False
                )
                df.to_excel(writer, sheet_name="TPR Data", index=False)

            st.download_button(
                label="📥 Download Excel Report",
                data=excel_buffer.getvalue(),
                file_name=f"Processed_{uploaded_file.name.rsplit('.', 1)[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.error("No valid numeric data found in columns 22 and 23.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload an Excel file to begin.")
