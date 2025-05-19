import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from sklearn.metrics import mean_squared_error
import scipy.stats as stats

# Load the data
file_path = 'tapado_full.csv'
data = pd.read_csv(file_path, sep=';')

# Rename columns for easier handling
data.rename(columns={
    "El Tapado-Altura de Nieve[cm]": "Snow_Height_cm",
    "El Tapado-Peso de la Nieve[kg/m²]": "Snow_Weight_kg_m2",
    "El Tapado-Temperatura Sensor[°C]": "Sensor_Temperature_C",
    "El Tapado-Agua equivalente[mm]": "Water_Equivalent_mm"
}, inplace=True)

# Ensure date column is datetime type
data["Fecha"] = pd.to_datetime(data["Fecha"], format="%d-%m-%Y %H:%M")

# Identify dry days (snow height <= 10 cm)
dry_days = data[data["Snow_Height_cm"] <= 10].dropna(subset=["Sensor_Temperature_C", "Snow_Weight_kg_m2"]).reset_index(drop=True)

# Select the first 7 dry days
dry_days_sample_7 = dry_days.iloc[:7]
T_dry_7 = dry_days_sample_7["Sensor_Temperature_C"].values
W_dry_7 = dry_days_sample_7["Snow_Weight_kg_m2"].values

# Full variable series
T = data["Sensor_Temperature_C"].values
W = data["Snow_Weight_kg_m2"].values

# Compute cross-correlation
valid_indices = ~(np.isnan(T) | np.isnan(W))
T_valid = T[valid_indices]
W_valid = W[valid_indices]
lags = np.arange(-3, 4)
correlations = []
for lag in lags:
    if lag > 0:
        corr = np.corrcoef(T_valid[:-lag], W_valid[lag:])[0, 1]
    elif lag < 0:
        corr = np.corrcoef(T_valid[-lag:], W_valid[:lag])[0, 1]
    else:
        corr = np.corrcoef(T_valid, W_valid)[0, 1]
    correlations.append(corr)

optimal_lag = lags[np.argmax(correlations)]

# Apply optimal lag to temperature
T_corr = np.roll(T, optimal_lag)

# Fit linear regression on dry days
slope, intercept, _, _, _ = linregress(T_dry_7, W_dry_7)

# Apply thermal correction
W_final = W - (slope * T_corr + intercept)

# Smooth with 12-hour moving average
W_final_smoothed = pd.Series(W_final).rolling(window=12, center=True, min_periods=1).mean()

# Add results to dataframe
data["Corrected_Snow_Weight"] = W_final_smoothed

# Cross-correlation between corrected weight and water equivalent
corrected_weight_clean = data["Corrected_Snow_Weight"].dropna()
water_equivalent_clean = data.loc[corrected_weight_clean.index, "Water_Equivalent_mm"].dropna()
min_length = min(len(corrected_weight_clean), len(water_equivalent_clean))
corrected_weight_clean = corrected_weight_clean.iloc[:min_length]
water_equivalent_clean = water_equivalent_clean.iloc[:min_length]

lags_corr = np.arange(-24, 25)
correlations_corr = []
for lag in lags_corr:
    if lag > 0:
        corr = np.corrcoef(corrected_weight_clean[:-lag], water_equivalent_clean[lag:])[0, 1]
    elif lag < 0:
        corr = np.corrcoef(corrected_weight_clean[-lag:], water_equivalent_clean[:lag])[0, 1]
    else:
        corr = np.corrcoef(corrected_weight_clean, water_equivalent_clean)[0, 1]
    correlations_corr.append(corr)

optimal_lag_corr = lags_corr[np.argmax(correlations_corr)]

# Apply optimal lag
corrected_weight_shifted = corrected_weight_clean.shift(-optimal_lag_corr)

# Create aligned DataFrame
comparison_df = pd.DataFrame({
    "Date": data["Fecha"],
    "Shifted_Corrected_Weight": corrected_weight_shifted,
    "Water_Equivalent": water_equivalent_clean
})

# Drop rows with NaNs for exact alignment
comparison_df = comparison_df.dropna()

# Snow height during the study period
Date_shifted = data['Fecha'].shift(-optimal_lag_corr)



# Align Snow Height with comparison_df
snow_height_aligned = data.loc[comparison_df.index, "Snow_Height_cm"]

fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot Snow Height
axs[0].plot(comparison_df["Date"], snow_height_aligned,
            label="Snow Height [cm]", color='purple', alpha=0.8)
axs[0].set_xlabel("Date")
axs[0].set_ylabel("Snow Height [cm]")
axs[0].legend()
axs[0].grid(True)

# Plot SWE (both corrected and measured)
axs[1].plot(comparison_df["Date"], comparison_df["Shifted_Corrected_Weight"],
            label="Snow Scale (Tested)", color='blue', alpha=0.9)
axs[1].plot(comparison_df["Date"], comparison_df["Water_Equivalent"],
            label="CS725 (Reference)", color='orange', alpha=0.7)
axs[1].set_ylabel("SWE [mm]")
axs[1].legend()
axs[1].grid(True)


fig.suptitle("Aligned Time Series: SWE (Corrected & Measured) and Snow Height - El Tapado")
plt.tight_layout()

# Save and show
plt.savefig("Tapado_Fig_1.png", format="png", dpi=300, bbox_inches='tight')
plt.show()




# --- RMSE and corrected MAPE ---
rmse = np.sqrt(mean_squared_error(comparison_df["Water_Equivalent"], comparison_df["Shifted_Corrected_Weight"]))

# Avoid division by zero in MAPE
non_zero_indices = comparison_df["Water_Equivalent"] != 0
mape_corrected = (
    np.mean(
        np.abs(
            (comparison_df.loc[non_zero_indices, "Shifted_Corrected_Weight"] - comparison_df.loc[non_zero_indices, "Water_Equivalent"])
            / comparison_df.loc[non_zero_indices, "Water_Equivalent"]
        )
    ) * 100
)

print(f"RMSE: {rmse:.2f} mm")
print(f"Corrected MAPE: {mape_corrected:.2f}%")

# --- Bland-Altman Analysis ---
means = (comparison_df["Shifted_Corrected_Weight"] + comparison_df["Water_Equivalent"]) / 2
differences = comparison_df["Shifted_Corrected_Weight"] - comparison_df["Water_Equivalent"]

mean_diff = np.mean(differences)
std_diff = np.std(differences)
loa_upper = mean_diff + 1.96 * std_diff
loa_lower = mean_diff - 1.96 * std_diff

# Plot Bland-Altman
plt.figure(figsize=(10, 6))
plt.scatter(means, differences, alpha=0.5)
plt.axhline(mean_diff, color='red', linestyle='--', label=f"Mean: {mean_diff:.2f}")
plt.axhline(loa_upper, color='green', linestyle='--', label=f"Upper limit: {loa_upper:.2f}")
plt.axhline(loa_lower, color='green', linestyle='--', label=f"Lower limit: {loa_lower:.2f}")
plt.xlabel("Average of Measurements (mm)")
plt.ylabel("Difference in Measurements (mm)")
plt.title("Bland-Altman Plot\nCorrected Weight vs Water Equivalent")
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save and show
plt.savefig("Tapado_Fig_2.png", format="png", dpi=300, bbox_inches='tight')
plt.show()


# Points outside limits of agreement
out_of_bounds = np.sum((differences < loa_lower) | (differences > loa_upper))
total_points = len(differences)
percentage_out_of_bounds = (out_of_bounds / total_points) * 100

print(f"Points outside limits of agreement: {out_of_bounds} out of {total_points} ({percentage_out_of_bounds:.2f}%)")

# --- Mean Absolute Error (MAE) ---
mae = np.mean(np.abs(comparison_df["Shifted_Corrected_Weight"] - comparison_df["Water_Equivalent"]))

# --- Coefficient of Determination (R²) ---
r_value = np.corrcoef(comparison_df["Shifted_Corrected_Weight"], comparison_df["Water_Equivalent"])[0, 1]
r_squared = r_value ** 2

# --- Final Results ---
print("\n--- Analysis Results ---")
print(f"RMSE: {rmse:.2f} kg/m²")
print(f"MAE: {mae:.2f} kg/m²")
print(f"Corrected MAPE: {mape_corrected:.2f}%")
print(f"Coefficient of Determination (R²): {r_squared:.3f}")

print("\n--- Bland-Altman Analysis Results ---")
print(f"Mean difference: {mean_diff:.2f} kg/m²")
print(f"Upper agreement limit (+1.96σ): {loa_upper:.2f} kg/m²")
print(f"Lower agreement limit (-1.96σ): {loa_lower:.2f} kg/m²")
print(f"Points outside agreement limits: {out_of_bounds} out of {total_points} ({percentage_out_of_bounds:.2f}%)")

