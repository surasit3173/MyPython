import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12

os.makedirs('11_figures', exist_ok=True)
os.makedirs('12_manuscript', exist_ok=True)

df_qa = pd.read_csv('01_data_audit/station_qa_summary.csv')
df_state_freq = pd.read_csv('02_state_classification/state_frequencies_1961_2019.csv')
df_markov = pd.read_csv('03_markov/markov_order1_matrices.csv')
df_spells = pd.read_csv('05_spells/spell_dynamics_summary.csv')
df_seasonal = pd.read_csv('07_spatial/seasonal_occurrence_probabilities.csv')
df_annual = pd.read_csv('08_temporal/annual_metrics_1961_2019.csv')
df_trend = pd.read_csv('08_temporal/trend_and_period_comparison_results.csv')

# --- FIGURE 1 ---
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
sc = ax.scatter(df_qa['Longitude_DD'], df_qa['Latitude_DD'], c=df_qa['Altitude_m'], cmap='terrain', s=150, edgecolors='black', linewidth=1.5, zorder=5)
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label('Altitude (m, MSL)')

for _, r in df_qa.iterrows():
    ax.annotate(f"{r['Station_ID']}\n({r['Station_Name']})", (r['Longitude_DD'], r['Latitude_DD']),
                xytext=(5, 5), textcoords='offset points', fontsize=8, fontweight='bold')

ax.set_xlabel('Longitude (°E)')
ax.set_ylabel('Latitude (°N)')
ax.set_title('Figure 1. Study Area and TMD Rainfall Station Network across Northeastern Thailand', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('11_figures/Figure1_study_area_network.png')
plt.savefig('11_figures/Figure1_study_area_network.pdf')
plt.close()

# --- FIGURE 2 ---
fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
df_seas_pivot = df_seasonal.pivot(index='Station_ID', columns='Season', values='Freq_R')
df_seas_pivot = df_seas_pivot[['Dry_Season', 'Pre_Monsoon', 'SW_Monsoon_Wet']]
df_seas_pivot.plot(kind='bar', ax=ax, colormap='Blues', edgecolor='black', width=0.8)
ax.set_xlabel('Station ID')
ax.set_ylabel('Rainy-State Occurrence Frequency (Freq_R)')
ax.set_title('Figure 2. Seasonal Rainy-State Occurrence Probabilities across Northeastern Thailand', fontsize=12, fontweight='bold')
ax.legend(['Dry Season (Nov-Feb)', 'Pre-Monsoon (Mar-Apr)', 'SW Monsoon / Wet (May-Oct)'], title='Season')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('11_figures/Figure2_seasonal_occurrence.png')
plt.savefig('11_figures/Figure2_seasonal_occurrence.pdf')
plt.close()

# --- FIGURE 3 ---
fig, axes = plt.subplots(2, 2, figsize=(10, 8), dpi=300)

df_sp_plot = df_qa.merge(df_state_freq, on='Station_ID').merge(df_markov, on='Station_ID')
df_r_spells = df_spells[df_spells['State'] == 'R']
df_sp_plot = df_sp_plot.merge(df_r_spells[['Station_ID', 'Mean_Duration_days']], on='Station_ID')

sns.barplot(data=df_sp_plot, x='Station_ID', y='Freq_R', ax=axes[0,0], color='#2b5c8f', edgecolor='black')
axes[0,0].set_title('A. Rainy-State Frequency (Freq_R)', fontweight='bold')
axes[0,0].tick_params(axis='x', rotation=45)

sns.barplot(data=df_sp_plot, x='Station_ID', y='P_DD', ax=axes[0,1], color='#e08214', edgecolor='black')
axes[0,1].set_title('B. Dry Persistence (P_DD)', fontweight='bold')
axes[0,1].tick_params(axis='x', rotation=45)

sns.barplot(data=df_sp_plot, x='Station_ID', y='P_RR', ax=axes[1,0], color='#41ab5d', edgecolor='black')
axes[1,0].set_title('C. Rainy Persistence (P_RR)', fontweight='bold')
axes[1,0].tick_params(axis='x', rotation=45)

sns.barplot(data=df_sp_plot, x='Station_ID', y='Mean_Duration_days', ax=axes[1,1], color='#88419d', edgecolor='black')
axes[1,1].set_title('D. Mean Rainy-Spell Duration (days)', fontweight='bold')
axes[1,1].tick_params(axis='x', rotation=45)

plt.suptitle('Figure 3. Spatial Heterogeneity of Rainfall Occurrence Regimes', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('11_figures/Figure3_spatial_heterogeneity.png')
plt.savefig('11_figures/Figure3_spatial_heterogeneity.pdf')
plt.close()

# --- FIGURE 4 ---
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)

for st in ['356201', '357201', '403201', '431201']:
    sub_a = df_annual[df_annual['Station_ID'] == int(st)]
    axes[0].plot(sub_a['Year'], sub_a['Freq_R'], label=f"Station {st}")
    axes[1].plot(sub_a['Year'], sub_a['P_DD'], label=f"Station {st}")

axes[0].set_ylabel('Rainy State Frequency (Freq_R)')
axes[0].set_title('Figure 4. Long-Term Evolution of Rainy Frequency (A) and Dry Persistence (B) over 1961–2019', fontweight='bold')
axes[0].legend(loc='upper right', ncol=2)

axes[1].set_ylabel('Dry Persistence (P_DD)')
axes[1].set_xlabel('Year')
axes[1].legend(loc='upper right', ncol=2)

plt.tight_layout()
plt.savefig('11_figures/Figure4_temporal_evolution.png')
plt.savefig('11_figures/Figure4_temporal_evolution.pdf')
plt.close()

# --- FIGURE 5 ---
fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
df_sp_plot['Station_ID_str'] = df_sp_plot['Station_ID'].astype(str)
sc = ax.scatter(df_sp_plot['Freq_R'], df_sp_plot['P_RR'], c=df_sp_plot['State_Entropy_bits'], cmap='viridis', s=200, edgecolors='black', linewidth=1.5, zorder=5)
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label('State Entropy (bits)')

for _, r in df_sp_plot.iterrows():
    ax.annotate(f"{r['Station_ID_str']}\n({r['Station_Name']})", (r['Freq_R'], r['P_RR']),
                xytext=(5, 5), textcoords='offset points', fontsize=8, fontweight='bold')

ax.set_xlabel('Rainy-State Frequency (Freq_R)')
ax.set_ylabel('Rainy Persistence Probability (P_RR)')
ax.set_title('Figure 5. Integrated Rainfall Occurrence Regime Synthesis (Frequency–Persistence–Entropy Space)', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig('11_figures/Figure5_regime_synthesis.png')
plt.savefig('11_figures/Figure5_regime_synthesis.pdf')
plt.close()

print("FIGURES GENERATED SUCCESSFULLY.")
