import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

# Publication Quality Settings
plt.rcParams['font.sans-serif'] = 'Helvetica'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 12

os.makedirs('11_figures', exist_ok=True)

# Load data
df_qa = pd.read_csv('01_data_audit/station_qa_summary.csv')
df_state_freq = pd.read_csv('02_state_classification/state_frequencies_1961_2019.csv')
df_markov = pd.read_csv('03_markov/markov_order1_matrices.csv')
df_spells = pd.read_csv('05_spells/spell_dynamics_summary.csv')
df_seasonal = pd.read_csv('07_spatial/seasonal_occurrence_probabilities.csv')
df_annual = pd.read_csv('08_temporal/annual_metrics_1961_2019.csv')

# --- FIGURE 1: Study Area & Station Network ---
fig, ax = plt.subplots(figsize=(6.5, 5.2), dpi=600)
sc = ax.scatter(df_qa['Longitude_DD'], df_qa['Latitude_DD'], c=df_qa['Altitude_m'],
                cmap='terrain', s=140, edgecolors='black', linewidth=1.2, zorder=5)

cbar = plt.colorbar(sc, ax=ax, pad=0.02, shrink=0.85)
cbar.set_label('Elevation (m MSL)', fontsize=9.5)

# Place labels cleanly without overlap
offsets = {
    '353201': (6, -4), '354201': (6, 4), '356201': (6, 4), '357201': (-45, 6),
    '381201': (6, -4), '403201': (6, -8), '405201': (6, 4), '407501': (-45, -12),
    '431201': (6, 4), '432201': (6, -8)
}

for _, r in df_qa.iterrows():
    st_id = str(r['Station_ID'])
    off = offsets.get(st_id, (5, 5))
    ax.annotate(f"{st_id}\n{r['Station_Name']}", (r['Longitude_DD'], r['Latitude_DD']),
                xytext=off, textcoords='offset points', fontsize=7.5, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

ax.set_xlabel('Longitude (°E)')
ax.set_ylabel('Latitude (°N)')
ax.set_xlim(101.2, 105.5)
ax.set_ylim(14.3, 17.8)
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('11_figures/Figure1_study_area_network.png', dpi=600)
plt.savefig('11_figures/Figure1_study_area_network.pdf')
plt.close()

# --- FIGURE 2: Seasonal Occurrence ---
fig, ax = plt.subplots(figsize=(7.0, 4.5), dpi=600)
df_seas_pivot = df_seasonal.pivot(index='Station_ID', columns='Season', values='Freq_R')
df_seas_pivot = df_seas_pivot[['Dry_Season', 'Pre_Monsoon', 'SW_Monsoon_Wet']]

# Palette: Navy for monsoon, sky blue for pre-monsoon, goldenrod for dry
colors = ['#d95f02', '#7570b3', '#1b9e77']
df_seas_pivot.plot(kind='bar', ax=ax, color=colors, edgecolor='black', linewidth=0.8, width=0.75)

ax.set_xlabel('Station ID')
ax.set_ylabel('Rainy-State Frequency ($Freq_R$)')
ax.set_ylim(0, 0.42)
ax.grid(True, linestyle='--', alpha=0.4, axis='y')
ax.legend(['Dry Season (Nov–Feb)', 'Pre-Monsoon (Mar–Apr)', 'SW Monsoon (May–Oct)'],
          title='Season', frameon=True, facecolor='white', edgecolor='none')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('11_figures/Figure2_seasonal_occurrence.png', dpi=600)
plt.savefig('11_figures/Figure2_seasonal_occurrence.pdf')
plt.close()

# --- FIGURE 3: Spatial Heterogeneity 4-Panel (a, b, c, d) ---
fig, axes = plt.subplots(2, 2, figsize=(7.5, 6.2), dpi=600)

df_sp_plot = df_qa.merge(df_state_freq, on='Station_ID').merge(df_markov, on='Station_ID')
df_r_spells = df_spells[df_spells['State'] == 'R']
df_sp_plot = df_sp_plot.merge(df_r_spells[['Station_ID', 'Mean_Duration_days']], on='Station_ID')
df_sp_plot['Station_ID_str'] = df_sp_plot['Station_ID'].astype(str)

# Panel (a)
sns.barplot(data=df_sp_plot, x='Station_ID_str', y='Freq_R', ax=axes[0,0], color='#2b5c8f', edgecolor='black', linewidth=0.8)
axes[0,0].set_title('(a) Rainy-State Frequency ($Freq_R$)', fontweight='bold', loc='left')
axes[0,0].set_xlabel('')
axes[0,0].set_ylabel('Frequency')
axes[0,0].tick_params(axis='x', rotation=45)

# Panel (b)
sns.barplot(data=df_sp_plot, x='Station_ID_str', y='P_DD', ax=axes[0,1], color='#e08214', edgecolor='black', linewidth=0.8)
axes[0,1].set_title('(b) Dry Persistence ($P_{DD}$)', fontweight='bold', loc='left')
axes[0,1].set_xlabel('')
axes[0,1].set_ylabel('Probability')
axes[0,1].tick_params(axis='x', rotation=45)

# Panel (c)
sns.barplot(data=df_sp_plot, x='Station_ID_str', y='P_RR', ax=axes[1,0], color='#41ab5d', edgecolor='black', linewidth=0.8)
axes[1,0].set_title('(c) Rainy Persistence ($P_{RR}$)', fontweight='bold', loc='left')
axes[1,0].set_xlabel('Station ID')
axes[1,0].set_ylabel('Probability')
axes[1,0].tick_params(axis='x', rotation=45)

# Panel (d)
sns.barplot(data=df_sp_plot, x='Station_ID_str', y='Mean_Duration_days', ax=axes[1,1], color='#88419d', edgecolor='black', linewidth=0.8)
axes[1,1].set_title('(d) Mean Rainy-Spell Duration (days)', fontweight='bold', loc='left')
axes[1,1].set_xlabel('Station ID')
axes[1,1].set_ylabel('Duration (days)')
axes[1,1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('11_figures/Figure3_spatial_heterogeneity.png', dpi=600)
plt.savefig('11_figures/Figure3_spatial_heterogeneity.pdf')
plt.close()

# --- FIGURE 4: Temporal Evolution 2-Panel (a, b) ---
fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.5), sharex=True, dpi=600)

line_styles = {'356201': ('#2b5c8f', '-'), '357201': ('#41ab5d', '--'), '403201': ('#d95f02', '-.'), '431201': ('#7570b3', ':')}

for st, (color, ls) in line_styles.items():
    sub_a = df_annual[df_annual['Station_ID'] == int(st)]
    axes[0].plot(sub_a['Year'], sub_a['Freq_R'], label=f"Station {st}", color=color, linestyle=ls, linewidth=1.5)
    axes[1].plot(sub_a['Year'], sub_a['P_DD'], label=f"Station {st}", color=color, linestyle=ls, linewidth=1.5)

axes[0].set_ylabel('Rainy State Frequency ($Freq_R$)')
axes[0].set_title('(a) Long-Term Evolution of Rainy State Frequency (1961–2019)', fontweight='bold', loc='left')
axes[0].legend(loc='upper right', ncol=2, frameon=True, facecolor='white')

axes[1].set_ylabel('Dry Persistence ($P_{DD}$)')
axes[1].set_title('(b) Long-Term Evolution of Dry State Persistence (1961–2019)', fontweight='bold', loc='left')
axes[1].set_xlabel('Year')
axes[1].legend(loc='upper right', ncol=2, frameon=True, facecolor='white')

plt.tight_layout()
plt.savefig('11_figures/Figure4_temporal_evolution.png', dpi=600)
plt.savefig('11_figures/Figure4_temporal_evolution.pdf')
plt.close()

# --- FIGURE 5: Integrated Synthesis ---
fig, ax = plt.subplots(figsize=(6.5, 5.0), dpi=600)
sc = ax.scatter(df_sp_plot['Freq_R'], df_sp_plot['P_RR'], c=df_sp_plot['State_Entropy_bits'],
                cmap='viridis', s=180, edgecolors='black', linewidth=1.2, zorder=5)

cbar = plt.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label('State Shannon Entropy ($H_{state}$, bits)', fontsize=9.5)

# Offsets for scatter labels
sc_offsets = {
    '353201': (6, -2), '354201': (6, 4), '356201': (-35, 8), '357201': (-40, -12),
    '381201': (6, -4), '403201': (6, -6), '405201': (6, 4), '407501': (-40, 8),
    '431201': (-45, -10), '432201': (6, -6)
}

for _, r in df_sp_plot.iterrows():
    st_id = str(r['Station_ID_str'])
    off = sc_offsets.get(st_id, (5, 5))
    ax.annotate(f"{st_id} ({r['Station_Name']})", (r['Freq_R'], r['P_RR']),
                xytext=off, textcoords='offset points', fontsize=7.5, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

ax.set_xlabel('Rainy-State Frequency ($Freq_R$)')
ax.set_ylabel('Rainy Persistence Probability ($P_{RR}$)')
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('11_figures/Figure5_regime_synthesis.png', dpi=600)
plt.savefig('11_figures/Figure5_regime_synthesis.pdf')
plt.close()

print("Q1 PUBLICATION FIGURES REDESIGNED AND EXPORTED IN 600 DPI PNG AND VECTOR PDF!")
