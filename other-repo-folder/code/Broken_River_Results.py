# --- Import libraries ---
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score, mean_squared_error

# --- Load and preprocess CRD data ---
column_names = ["TIMESTAMP", "RECORD", "Ground_Det", "Reference_Det", "AR", "ARF", "SWEmm_Intvl", "SWEmm_Avg"]
br_crd = pd.read_csv('BR_CRD.dat', skiprows=4, names=column_names)

# Convert columns to numeric and datetime
br_crd['Ground_Det'] = pd.to_numeric(br_crd['Ground_Det'], errors='coerce')
br_crd['Reference_Det'] = pd.to_numeric(br_crd['Reference_Det'], errors='coerce')
br_crd['TIMESTAMP'] = pd.to_datetime(br_crd['TIMESTAMP'])

# Filter valid CRD readings
crd_data = br_crd[(br_crd['Ground_Det'].between(25000, 40000)) & 
                  (br_crd['Reference_Det'].between(15000, 22000))].copy()

# Calculate raw and normalized ratio
crd_data['Raw_Ratio'] = crd_data['Reference_Det'] / crd_data['Ground_Det']
dry_period = crd_data[(crd_data['TIMESTAMP'] >= '2023-12-01') & (crd_data['TIMESTAMP'] <= '2023-12-31')]
mean_raw_ratio_dry = dry_period['Raw_Ratio'].mean()
target_ratio = 0.5356
crd_data['Normalized_Ratio'] = crd_data['Raw_Ratio'] / mean_raw_ratio_dry * target_ratio

# Apply CRD SWE formula
AF = 1829  # Calibration constant
crd_data['SWE_CRD_raw'] = AF * (crd_data['Normalized_Ratio'] / target_ratio - 1)
crd_data['SWE_CRD_12h'] = crd_data['SWE_CRD_raw'].rolling(window=48, center=True, min_periods=1).mean()

# --- Load and preprocess Snow Scale data ---
iot_raw = []
with open('BR_IOT.csv', 'r') as file:
    lines = file.readlines()
    for line in lines:
        elements = line.strip().split(',')
        if len(elements) % 2 == 0:
            record = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}
            iot_raw.append(record)

iot_df = pd.DataFrame(iot_raw)
iot_df['dt'] = pd.to_datetime(iot_df['dt'], errors='coerce')
iot_df['sh'] = pd.to_numeric(iot_df['sh'], errors='coerce')
iot_df['sw'] = pd.to_numeric(iot_df['sw'], errors='coerce')
iot_df['swt'] = pd.to_numeric(iot_df['swt'], errors='coerce')
iot_df['Snow_Height_cm'] = 200 - iot_df['sh']

# Convert scale SWE to kg/m² using scale area
scale_area_m2 = 0.28 * 0.28
iot_df['SWE_Scale_kg_m2'] = iot_df['sw'] / scale_area_m2

# --- Merge datasets ---
iot_df.rename(columns={'dt': 'timestamp_scale'}, inplace=True)
crd_data.rename(columns={'TIMESTAMP': 'timestamp_crd'}, inplace=True)
iot_df['timestamp_scale'] = iot_df['timestamp_scale'].dt.tz_localize(None)

iot_filtered = iot_df[(iot_df['timestamp_scale'] >= '2023-06-06') & (iot_df['timestamp_scale'] <= '2023-12-31')]
crd_filtered = crd_data[(crd_data['timestamp_crd'] >= '2023-06-06') & (crd_data['timestamp_crd'] <= '2023-12-31')]

merged = pd.merge_asof(
    iot_filtered.sort_values('timestamp_scale'),
    crd_filtered.sort_values('timestamp_crd'),
    left_on='timestamp_scale',
    right_on='timestamp_crd',
    direction='nearest',
    tolerance=pd.Timedelta('30min')
)

# Apply 12-hour moving average to scale SWE (10-minute resolution = 72 samples)
merged['SWE_Scale_12h'] = merged['SWE_Scale_kg_m2'].rolling(window=72, center=True, min_periods=1).mean()

# Final filtered dataframe
merged_final = merged[['timestamp_scale', 'Snow_Height_cm', 'sw', 'SWE_Scale_kg_m2', 'swt', 'SWE_CRD_12h', 'SWE_Scale_12h']]
merged_final = merged_final[(merged_final['SWE_Scale_kg_m2'] >= 0) & (merged_final['SWE_Scale_kg_m2'] <= 500)]

# --- Analysis ---
valid_data = merged_final.dropna(subset=['SWE_Scale_12h', 'SWE_CRD_12h'])
swe_scale_vals = valid_data['SWE_Scale_12h'].values
swe_crd_vals = valid_data['SWE_CRD_12h'].values

# Metrics
r2 = r2_score(swe_scale_vals, swe_crd_vals)
rmse = np.sqrt(mean_squared_error(swe_scale_vals, swe_crd_vals))
mean_vals = (swe_scale_vals + swe_crd_vals) / 2
diff_vals = swe_scale_vals - swe_crd_vals
mean_diff = np.mean(diff_vals)
std_diff = np.std(diff_vals)
loa_upper = mean_diff + 1.96 * std_diff
loa_lower = mean_diff - 1.96 * std_diff
percent_outside_loa = 100 * ((diff_vals < loa_lower) | (diff_vals > loa_upper)).sum() / len(diff_vals)

# --- SWE Comparison + Snow Height Plot (Aligned) ---
# Filter and smooth snow height
snow_height_filtered = valid_data[valid_data['Snow_Height_cm'] <= 60].copy()
snow_height_filtered['Snow_Height_12h'] = snow_height_filtered['Snow_Height_cm'].rolling(
    window=48, center=True, min_periods=1).mean()

# Create aligned figure
fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Snow height subplot
axs[0].plot(snow_height_filtered['timestamp_scale'], snow_height_filtered['Snow_Height_12h'],
            label='Snow Height (12h avg)', color='purple', alpha=0.8)
axs[0].set_xlabel("Date")
axs[0].set_ylabel("Snow Height [cm]")
axs[0].legend()
axs[0].grid(True)

# SWE subplot: scale vs CRD
axs[1].plot(valid_data['timestamp_scale'], valid_data['SWE_Scale_12h'], label='SWE Scale (Tested)', color='orange', alpha=0.8)
axs[1].plot(valid_data['timestamp_scale'], valid_data['SWE_CRD_12h'], label='SWE CRD (Reference)', color='blue', alpha=0.8)
axs[1].set_ylabel("SWE [mm]")
axs[1].legend()
axs[1].grid(True)

fig.suptitle("Aligned SWE (Scale & CRD) and Snow Height – June 2023 to March 2024")
plt.tight_layout()

# Save and show
plt.savefig("Broken_River_Fig_1.png", format="png", dpi=300, bbox_inches='tight')
plt.show()

# --- Bland-Altman Plot ---
plt.figure(figsize=(10, 6))
plt.scatter(mean_vals, diff_vals, alpha=0.5)
plt.axhline(mean_diff, color='red', linestyle='--', label=f'Mean: {mean_diff:.2f} mm')
plt.axhline(loa_upper, color='green', linestyle='--', label=f'Upper LOA: {loa_upper:.2f} mm')
plt.axhline(loa_lower, color='green', linestyle='--', label=f'Lower LOA: {loa_lower:.2f} mm')
plt.xlabel('Average of Measurements (mm)')
plt.ylabel('Difference (Scale - CRD) (mm)')
plt.title('Bland-Altman Plot')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save and show
plt.savefig("Broken_River_Fig_2.png", format="png", dpi=300, bbox_inches='tight')
plt.show()

# --- Print Results ---
print(f"R²: {r2:.3f}")
print(f"RMSE: {rmse:.3f} mm")
print(f"Mean difference: {mean_diff:.3f} mm")
print(f"Standard deviation of differences: {std_diff:.3f} mm")
print(f"Lower LOA: {loa_lower:.3f} mm")
print(f"Upper LOA: {loa_upper:.3f} mm")
print(f"Percentage outside LOA: {percent_outside_loa:.2f}%")
