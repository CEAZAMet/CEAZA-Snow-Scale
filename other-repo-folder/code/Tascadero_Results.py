import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from sklearn.metrics import r2_score, mean_squared_error

# --- Load and parse datetime ---
df = pd.read_csv('tascadero_full.csv', sep=';')
df['Fecha'] = pd.to_datetime(df['Fecha'], format='mixed', dayfirst=True)

# --- Define relevant columns ---
weight_iot = "Tascadero Nodo IOT-Peso de la Nieve1[kg/m²]"
temp_iot = "Tascadero Nodo IOT-Temperatura Sensor1[°C]"
snow_height_col = "Tascadero-Altura de Nieve[cm]"
ref_weight_col = "Tascadero-Peso de la Nieve[kg/m²]"

# --- Thermal correction function ---
def correct_weight(df, weight_col, temp_col, height_col):
    dry_days = df[df[height_col] <= 10].iloc[:7]
    W = dry_days[weight_col].values
    T = dry_days[temp_col].values
    best_shift, best_corr = 0, -np.inf
    for shift in range(-3, 4):
        T_shifted = np.roll(T, shift)
        corr = np.corrcoef(T_shifted, W)[0, 1]
        if corr > best_corr:
            best_corr, best_shift = corr, shift
    T_corrected = np.roll(df[temp_col].values, best_shift)
    T_dry_corrected = np.roll(T, best_shift)
    slope, intercept, *_ = linregress(T_dry_corrected, W)
    W_corrected = df[weight_col] - (slope * T_corrected + intercept)
    return pd.Series(W_corrected).rolling(window=12, center=True, min_periods=1).mean()

# --- Apply correction ---
df['Corrected_Weight_B1'] = correct_weight(df, weight_iot, temp_iot, snow_height_col)

# --- Comparison with reference ---
def analyze_comparison(df, corrected_col, reference_col):
    best_shift, best_corr = 0, -np.inf
    for shift in range(-3, 4):
        shifted = np.roll(df[corrected_col].values, shift)
        corr = np.corrcoef(shifted, df[reference_col].values)[0, 1]
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    corrected = np.roll(df[corrected_col].values, best_shift)
    reference = df[reference_col].values
    mask = ~np.isnan(corrected) & ~np.isnan(reference)
    corrected, reference = corrected[mask], reference[mask]
    avg = (corrected + reference) / 2
    diff = corrected - reference
    stats = {
        "shift": best_shift,
        "r2": r2_score(reference, corrected),
        "rmse": mean_squared_error(reference, corrected, squared=False),
        "bias": np.mean(diff),
        "std_diff": np.std(diff),
        "avg": avg,
        "diff": diff,
        "time": df.loc[mask, 'Fecha']
    }
    return corrected, reference, stats

corrected, reference, stats = analyze_comparison(df, 'Corrected_Weight_B1', ref_weight_col)
time_values = stats["time"]

# --- Time Series Plot with Date ---
fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Snow height
axs[0].plot(time_values, df.loc[time_values.index, snow_height_col], label='Snow Height [cm]', color='purple')
axs[0].set_ylabel('Snow Height [cm]')
axs[0].set_xlabel('Date')
axs[0].set_title('Snow Height Evolution')
axs[0].legend()
axs[0].grid(True)

# SWE Comparison
axs[1].plot(time_values, reference, label='Reference Scale (SSG-2)', linewidth=2)
axs[1].plot(time_values, corrected, label='Tested Scale', linestyle='--', linewidth=2)
axs[1].set_ylabel('SWE [mm]')
axs[1].set_title('SWE Comparison: Reference vs Tested')
axs[1].legend()
axs[1].grid(True)


plt.suptitle('Tascadero Analysis', fontsize=14)
plt.tight_layout()

# Save and show
plt.savefig("Tascadero_Fig_1.png", format="png", dpi=300, bbox_inches='tight')
plt.show()

# --- Bland-Altman Plot ---
upper = stats["bias"] + 1.96 * stats["std_diff"]
lower = stats["bias"] - 1.96 * stats["std_diff"]

plt.figure(figsize=(10, 6))
plt.scatter(stats["avg"], stats["diff"], alpha=0.5)
plt.axhline(stats["bias"], color='red', linestyle='--', label=f'Mean = {stats["bias"]:.2f}')
plt.axhline(upper, color='green', linestyle='--', label=f'+1.96 SD = {upper:.2f}')
plt.axhline(lower, color='green', linestyle='--', label=f'-1.96 SD = {lower:.2f}')
plt.xlabel('Mean of Measurements [mm]')
plt.ylabel('Difference (Tested - Reference) [mm]')
plt.title('Bland-Altman Plot – IoT Balanza 1')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save and show
plt.savefig("Tascadero_Fig_2.png", format="png", dpi=300, bbox_inches='tight')
plt.show()

# --- Summary Output ---
print("\n--- Statistical Summary: IoT Balanza 1 ---")
print(f"Best alignment shift: {stats['shift']} records")
print(f"R²: {stats['r2']:.3f}")
print(f"RMSE: {stats['rmse']:.2f} mm")
print(f"Bias (mean diff): {stats['bias']:.2f} mm")
print(f"Standard deviation: {stats['std_diff']:.2f} mm")
print(f"Limits of agreement: [{lower:.2f}, {upper:.2f}] mm")
