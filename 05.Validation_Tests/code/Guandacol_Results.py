import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# --- Load data ---
df = pd.read_csv("Guandacol_Data_FROM_CEAZAMET.csv", delimiter=';')
df.columns = ["Timestamp", "Temp_IOT_C", "Weight_IOT_kgm2", "Weight_Ref_kgm2", "Snow_Depth_cm"]
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%d-%m-%Y %H:%M")

# --- Preprocessing ---
df.loc[df["Weight_IOT_kgm2"] < -10, "Weight_IOT_kgm2"] = np.nan
df["Converted_Snow_Depth"] = 25 - df["Snow_Depth_cm"]
df["Snow_Depth_Smoothed"] = savgol_filter(df["Converted_Snow_Depth"], window_length=13, polyorder=2, mode='interp')

# --- Identify dry period ---
start_date = df["Timestamp"].min()
end_date = start_date + pd.Timedelta(days=7)
dry_days = df[(df["Timestamp"] >= start_date) & (df["Timestamp"] < end_date) & (df["Snow_Depth_Smoothed"] < 15)]

# --- Find optimal lag ---
def find_best_lag(temp, weight, lags):
    results = []
    for lag in lags:
        shifted_temp = temp.shift(-lag) if lag < 0 else temp
        shifted_weight = weight if lag < 0 else weight.shift(lag)
        valid = shifted_temp.notna() & shifted_weight.notna()
        if valid.sum() > 0:
            r2 = r2_score(shifted_temp[valid], shifted_weight[valid])
            results.append((lag, r2))
    return results

lags = range(-3, 4)
best_lag = max(find_best_lag(dry_days["Temp_IOT_C"], dry_days["Weight_IOT_kgm2"], lags), key=lambda x: x[1])[0]

# --- Thermal correction ---
df["Temp_IOT_Lagged"] = df["Temp_IOT_C"].shift(best_lag)
model = LinearRegression().fit(
    dry_days["Temp_IOT_C"].dropna().values.reshape(-1, 1),
    dry_days["Weight_IOT_kgm2"].dropna().values
)
thermal_bias = model.predict(df["Temp_IOT_Lagged"].bfill().values.reshape(-1, 1))
df["Weight_IOT_Corrected"] = df["Weight_IOT_kgm2"] - thermal_bias
df["Weight_IOT_12h"] = df["Weight_IOT_Corrected"].rolling(window=12, min_periods=1).mean()

# --- Calibration against reference ---
ref_series = df["Weight_Ref_kgm2"]
iot_series = df["Weight_IOT_12h"]
mask = (~ref_series.isna()) & (~iot_series.isna())
ref_clean = ref_series[mask]
iot_clean = iot_series[mask]
time_clean = df["Timestamp"][mask]

calibration_model = LinearRegression()
calibration_model.fit(iot_clean.values.reshape(-1, 1), ref_clean.values)
iot_calibrated = calibration_model.predict(iot_clean.values.reshape(-1, 1))

# --- Align snow depth ---
snow_depth_aligned = df.loc[time_clean.index, "Snow_Depth_Smoothed"]
valid = ~snow_depth_aligned.isna()
ref_final = ref_clean[valid]
iot_final = iot_calibrated[valid]
snow_final = snow_depth_aligned[valid]
time_final = time_clean[valid]

# --- Statistics ---
r2 = r2_score(ref_final, iot_final)
rmse = np.sqrt(mean_squared_error(ref_final, iot_final))
mae = mean_absolute_error(ref_final, iot_final)
pearson_corr = np.corrcoef(ref_final, iot_final)[0, 1]

print("\n--- Statistical Analysis ---")
print(f"R²: {r2:.4f}")
print(f"RMSE: {rmse:.2f} mm")
print(f"MAE: {mae:.2f} mm")
print(f"Pearson Correlation: {pearson_corr:.4f}")

# --- Time Series Plot ---
fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

axs[0].plot(time_final, snow_final, label='Smoothed Snow Depth (cm)', color='purple', linewidth=1.8)
axs[0].set_xlabel("Date")
axs[0].set_ylabel("Snow Depth [cm]")
axs[0].legend()
axs[0].grid(True)
axs[0].set_title("Snow Depth (Smoothed)")

axs[1].plot(time_final, ref_final, label='Reference Scale (SSG-2)', linewidth=2)
axs[1].plot(time_final, iot_final, label='Tested Scale', linestyle='-.', linewidth=2)
axs[1].set_ylabel("SWE [mm]")
axs[1].legend()
axs[1].grid(True)
axs[1].set_title("SWE Comparison: Reference vs Calibrated IoT")


fig.suptitle("Time Series Comparison – Guandacol", fontsize=14)
plt.tight_layout()

# Save and show
plt.savefig("Guandacol_Fig_1.png", format="png", dpi=300, bbox_inches='tight')
plt.show()

# --- Scatter Plot + Trend Line ---
slope, intercept = np.polyfit(ref_final, iot_final, 1)
plt.figure(figsize=(8, 6))
plt.scatter(ref_final, iot_final, alpha=0.6, label="Data points")
plt.plot(ref_final, slope * ref_final + intercept, color="red",
         label=f"Trend line (R² = {r2:.2f})")
plt.xlabel("Reference SWE (mm)")
plt.ylabel("Calibrated IoT SWE (mm)")
plt.title("Scatter Plot: Reference vs IoT (Calibrated)")
plt.grid(True)
plt.legend()
plt.axis('equal')
plt.tight_layout()
plt.show()

# --- Bland-Altman Analysis ---
diff = ref_final - iot_final
mean_values = (ref_final + iot_final) / 2
mean_diff = np.mean(diff)
std_diff = np.std(diff)
loa_upper = mean_diff + 1.96 * std_diff
loa_lower = mean_diff - 1.96 * std_diff
outliers = ((diff > loa_upper) | (diff < loa_lower)).sum()
percent_outliers = 100 * outliers / len(diff)

print("\n--- Bland-Altman Results ---")
print(f"Mean Difference: {mean_diff:.2f} mm")
print(f"Upper LoA: {loa_upper:.2f} mm")
print(f"Lower LoA: {loa_lower:.2f} mm")
print(f"Outliers beyond LoA: {outliers} ({percent_outliers:.2f}%)")

# --- Bland-Altman Plot ---
plt.figure(figsize=(10, 5))
plt.scatter(mean_values, diff, alpha=0.5)
plt.axhline(mean_diff, color='red', linestyle='--', label=f"Mean: {mean_diff:.2f} mm")
plt.axhline(loa_upper, color='green', linestyle='--', label=f"+1.96 SD: {loa_upper:.2f} mm")
plt.axhline(loa_lower, color='green', linestyle='--', label=f"-1.96 SD: {loa_lower:.2f} mm")
plt.xlabel("Mean of Measurements (mm)")
plt.ylabel("Difference (Reference - IoT) (mm)")
plt.title("Bland-Altman Plot")
plt.grid(True)
plt.legend()
plt.tight_layout()

# Save and show
plt.savefig("Guandacol_Fig_2.png", format="png", dpi=300, bbox_inches='tight')
plt.show()
