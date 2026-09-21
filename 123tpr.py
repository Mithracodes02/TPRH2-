import io
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl.drawing.image import Image as OpenPyxlImage
import pandas as pd
import scipy.integrate as spi
import streamlit as st
import xlrd

st.set_page_config(page_title="TPR Data Processor", layout="wide")
st.title("TPR H₂ Data Analysis & Reducibility Report Generator")

# 1. Sidebar Parameters for Quantification
st.sidebar.header("Quantification Parameters")
sample_mass_mg = st.sidebar.number_input(
    "Sample Mass (mg)", value=50.0, step=1.0
)
cuo_wt_pct = st.sidebar.number_input(
    "CuO Content (wt%)", value=95.0, step=1.0
)
calib_factor = st.sidebar.number_input(
    "Calibration Factor K (a.u.·°C / µmol H₂)",
    value=1.0,
    format="%.4f",
    help="Calibration constant relating TCD area to hydrogen consumption.",
)

# 2. File Uploader
uploaded_file = st.file_uploader(
    "Upload raw TPR file (.xls / .xlsx)", type=["xls", "xlsx"]
)

if uploaded_file is not None:
    try:
        # Load workbook from memory
        file_bytes = uploaded_file.read()
        workbook = xlrd.open_workbook(file_contents=file_bytes)
        sheet = workbook.sheet_by_index(0)

        # Extract Temperature & TCD Signal (Columns 22 & 23)
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
            # Baseline subtraction (Linear baseline between min & max temp)
            baseline = np.linspace(
                df["TCD Signal (a.u.)"].iloc[0],
                df["TCD Signal (a.u.)"].iloc[-1],
                len(df),
            )
            df["Corrected Signal (a.u.)"] = np.maximum(
                0, df["TCD Signal (a.u.)"] - baseline
            )

            # Calculations
            max_idx = df["TCD Signal (a.u.)"].idxmax()
            t_max = df.loc[max_idx, "Temperature (°C)"]
            signal_max = df.loc[max_idx, "TCD Signal (a.u.)"]

            # Peak Area Integration (Trapezoidal integration over Temperature)
            peak_area = spi.trapezoid(
                df["Corrected Signal (a.u.)"], x=df["Temperature (°C)"]
            )

            # Hydrogen Consumption & Reducibility Calculations
            h2_consumed_umol = peak_area / calib_factor
            cuo_mass_g = (sample_mass_mg / 1000.0) * (cuo_wt_pct / 100.0)
            molar_mass_cuo = 79.545  # g/mol
            cuo_theoretical_umol = (cuo_mass_g / molar_mass_cuo) * 1e6

            reducibility_pct = (
                (h2_consumed_umol / cuo_theoretical_umol) * 100
                if cuo_theoretical_umol > 0
                else 0.0
            )

            # Display Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("T_max (°C)", f"{t_max:.2f}")
            m2.metric("Peak Area (a.u.·°C)", f"{peak_area:.2f}")
            m3.metric("H₂ Consumed (µmol/g)", f"{(h2_consumed_umol / (sample_mass_mg/1000)):.2f}")
            m4.metric("% Reducibility", f"{reducibility_pct:.2f} %")

            # Plotting Graph
            fig, ax = plt.subplots(figsize=(9, 4.5))
            ax.plot(
                df["Temperature (°C)"],
                df["TCD Signal (a.u.)"],
                color="crimson",
                linewidth=1.5,
                label="Raw TCD Signal",
            )
            ax.fill_between(
                df["Temperature (°C)"],
                df["TCD Signal (a.u.)"],
                alpha=0.2,
                color="crimson",
            )
            ax.axvline(
                x=t_max,
                color="gray",
                linestyle="--",
                alpha=0.7,
                label=f"T_max: {t_max:.1f}°C",
            )
            ax.set_title(
                f"H₂-TPR Profile ({uploaded_file.name})", fontsize=12, pad=10
            )
            ax.set_xlabel("Temperature (°C)")
            ax.set_ylabel("TCD Signal (a.u.)")
            ax.grid(True, linestyle="--", alpha=0.5)
            ax.legend(loc="upper right")
            st.pyplot(fig)

            # Build Ready-to-Download Report Tables
            summary_table = pd.DataFrame(
                [
                    {"Parameter": "File Name", "Value": uploaded_file.name},
                    {"Parameter": "Sample Mass (mg)", "Value": sample_mass_mg},
                    {"Parameter": "CuO Content (wt%)", "Value": cuo_wt_pct},
                    {"Parameter": "Calibration Factor K", "Value": calib_factor},
                    {"Parameter": "T_max (°C)", "Value": round(t_max, 2)},
                    {
                        "Parameter": "Integrated Area (a.u.·°C)",
                        "Value": round(peak_area, 4),
                    },
                    {
                        "Parameter": "Total H₂ Consumed (µmol)",
                        "Value": round(h2_consumed_umol, 2),
                    },
                    {
                        "Parameter": "Specific H₂ Consumption (µmol/g)",
                        "Value": round(
                            h2_consumed_umol / (sample_mass_mg / 1000), 2
                        ),
                    },
                    {
                        "Parameter": "% Reducibility",
                        "Value": round(reducibility_pct, 2),
                    },
                ]
            )

            st.subheader("Calculated Results Summary")
            st.dataframe(summary_table, use_container_width=True)

            # Export Excel with Embedded Plot
            plot_img_bytes = io.BytesIO()
            fig.savefig(plot_img_bytes, format="png", dpi=200, bbox_inches="tight")
            plot_img_bytes.seek(0)

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(
                excel_buffer, engine="openpyxl"
            ) as writer:
                summary_table.to_excel(
                    writer, sheet_name="Summary & Reducibility", index=False
                )
                df[
                    [
                        "Temperature (°C)",
                        "TCD Signal (a.u.)",
                        "Corrected Signal (a.u.)",
                    ]
                ].to_excel(writer, sheet_name="TPR Profiles", index=False)

                # Embed Image in Excel Sheet
                ws = writer.sheets["Summary & Reducibility"]
                img = OpenPyxlImage(plot_img_bytes)
                img.anchor = "E2"
                ws.add_image(img)

            st.download_button(
                label="📥 Download Full Excel Report (With Graph & Reducibility)",
                data=excel_buffer.getvalue(),
                file_name=f"TPR_Report_{uploaded_file.name.rsplit('.', 1)[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Upload your `.xls` file to view reducibility calculations and download the report.")
