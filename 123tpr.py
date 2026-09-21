import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

st.set_page_config(page_title="H2-TPR Data Analyzer", layout="wide")

st.title("🧪 Advanced H₂-TPR Data Analyzer")
st.markdown("Upload Excel or CSV data, extract TCD and Temperature columns, plot TPR profiles, and calculate reduction degree and Cu dispersion.")

# Sidebar - Data Import
st.sidebar.header("1. Data Import")
uploaded_file = st.sidebar.file_uploader("Upload Data File (.xlsx, .xls, .csv, .txt, .dat)", type=["xlsx", "xls", "csv", "txt", "dat"])

if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()
    df = None
    
    try:
        # Attempt to read Excel files
        if file_ext in ["xlsx", "xls"]:
            try:
                uploaded_file.seek(0)
                excel_file = pd.ExcelFile(uploaded_file, engine="openpyxl")
                sheet_name = st.sidebar.selectbox("Select Excel Sheet", excel_file.sheet_names)
                skiprows = st.sidebar.number_input("Header Lines to Skip", min_value=0, value=0)
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=skiprows, engine="openpyxl")
            except Exception:
                # Fallback to CSV parser if the file is an ASCII text file with an .xlsx extension
                uploaded_file.seek(0)
                st.sidebar.warning("Unable to read as native Excel. Attempting text/CSV parsing fallback...")
                delimiter = st.sidebar.selectbox("Fallback Delimiter", [r"\s+", ",", ";", r"\t"], index=0)
                skiprows = st.sidebar.number_input("Header Lines to Skip", min_value=0, value=0)
                df = pd.read_csv(
                    uploaded_file, 
                    sep=delimiter, 
                    skiprows=skiprows, 
                    engine="python", 
                    encoding="latin1",
                    on_bad_lines="skip"
                )
        else:
            # Standard CSV / Text / DAT file parsing
            uploaded_file.seek(0)
            delimiter = st.sidebar.selectbox("Delimiter", [r"\s+", ",", ";", r"\t"], index=0)
            skiprows = st.sidebar.number_input("Header Lines to Skip", min_value=0, value=0)
            df = pd.read_csv(
                uploaded_file, 
                sep=delimiter, 
                skiprows=skiprows, 
                engine="python", 
                encoding="latin1",
                on_bad_lines="skip"
            )
        
        st.sidebar.success("File loaded successfully!")
        
        # Column Selection
        st.sidebar.header("2. Map Columns")
        columns = df.columns.tolist()
        temp_col = st.sidebar.selectbox("Temperature Column (°C)", columns, index=0 if len(columns) > 0 else 0)
        signal_col = st.sidebar.selectbox("TCD Signal Column (a.u. / mV)", columns, index=1 if len(columns) > 1 else 0)
        
        # Extract and Clean Data
        df_clean = df[[temp_col, signal_col]].dropna()
        x = pd.to_numeric(df_clean[temp_col], errors='coerce').values
        y = pd.to_numeric(df_clean[signal_col], errors='coerce').values
        
        # Filter out NaN rows (e.g. residual text headers or footers)
        valid_idx = ~np.isnan(x) & ~np.isnan(y)
        x = x[valid_idx]
        y = y[valid_idx]
        
        if len(x) == 0:
            st.error("No numeric data found. Adjust 'Header Lines to Skip' or check Delimiter setting in the sidebar.")
        else:
            # Baseline Correction
            st.sidebar.header("3. Baseline Correction")
            apply_baseline = st.sidebar.checkbox("Apply Linear Baseline Subtraction", value=True)
            if apply_baseline:
                poly_fit = np.polyfit([x[0], x[-1]], [y[0], y[-1]], 1)
                baseline = np.polyval(poly_fit, x)
                y_corrected = y - baseline
                y_corrected = np.maximum(y_corrected, 0)
            else:
                y_corrected = y

            # Catalyst & Chemisorption Parameters
            st.sidebar.header("4. Catalyst & Quantitative Parameters")
            sample_mass_mg = st.sidebar.number_input("Sample Mass (mg)", min_value=0.1, value=50.0, step=1.0)
            cu_wt_pct = st.sidebar.number_input("Cu Loading (wt%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5)
            calib_factor = st.sidebar.number_input("Calibration Factor (μmol H₂ / (a.u. · °C))", min_value=1e-8, value=1.0, format="%.6f")
            stoich_ratio = st.sidebar.selectbox("Cu Oxidation State Mode", ["CuO -> Cu (1 H2 : 1 Cu)", "Cu2O -> Cu (0.5 H2 : 1 Cu)"], index=0)

            # Main Dashboard Display
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("📊 TPR Profile & Reduction Temperatures")
                
                # Peak Finding Sensitivity
                prominence = st.sidebar.slider("Peak Detection Sensitivity", 0.0, float(np.ptp(y_corrected)), float(np.ptp(y_corrected) * 0.05))
                peaks, _ = find_peaks(y_corrected, prominence=prominence)
                
                # Plot
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.plot(x, y_corrected, label="Corrected TCD Signal", color="crimson", lw=1.8)
                ax.plot(x[peaks], y_corrected[peaks], "ro", markersize=6, label="Reduction Maxima ($T_m$)")
                
                for p in peaks:
                    ax.annotate(f"{x[p]:.1f} °C", (x[p], y_corrected[p]), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
                
                ax.set_xlabel("Temperature (°C)", fontsize=11)
                ax.set_ylabel("TCD Signal (a.u.)", fontsize=11)
                ax.grid(True, linestyle="--", alpha=0.5)
                ax.legend(frameon=True)
                st.pyplot(fig)

            with col2:
                st.subheader("📌 Peak Temperatures ($T_m$)")
                if len(peaks) > 0:
                    peak_df = pd.DataFrame({
                        "Peak": [f"Peak {i+1}" for i in range(len(peaks))],
                        "T_m (°C)": x[peaks],
                        "Intensity": y_corrected[peaks]
                    })
                    st.dataframe(peak_df, hide_index=True)
                else:
                    st.info("No reduction peaks detected. Lower sensitivity slider in sidebar.")

                # Quantitative Calculations
                st.subheader("🧮 Quantitative Analysis")
                
                total_area = np.trapz(y_corrected, x)
                exp_h2_consumed_umol = total_area * calib_factor
                exp_h2_per_g = (exp_h2_consumed_umol / sample_mass_mg) * 1000  # μmol H2 / g_cat
                
                cu_moles_per_g = (cu_wt_pct / 100.0) / 63.546  # mol Cu / g_cat
                stoich_factor = 1.0 if "CuO" in stoich_ratio else 0.5
                theo_h2_per_g = cu_moles_per_g * stoich_factor * 1e6  # μmol H2 / g_cat
                
                reduction_pct = min((exp_h2_per_g / theo_h2_per_g) * 100.0, 100.0) if theo_h2_per_g > 0 else 0.0
                dispersion_pct = min((exp_h2_per_g / theo_h2_per_g) * 100.0, 100.0) if theo_h2_per_g > 0 else 0.0

                st.metric("Total Integrated Area", f"{total_area:.2f}")
                st.metric("Exp. H₂ Consumed", f"{exp_h2_per_g:.2f} μmol/g_cat")
                st.metric("Theo. H₂ Limit", f"{theo_h2_per_g:.2f} μmol/g_cat")
                st.metric("Degree of Reduction (%)", f"{reduction_pct:.2f} %")
                st.metric("Cu Dispersion (%)", f"{dispersion_pct:.2f} %")

    except Exception as e:
        st.error(f"Error processing dataset: {e}")

else:
    st.info("Please upload an Excel or CSV/text file in the sidebar to begin.")
