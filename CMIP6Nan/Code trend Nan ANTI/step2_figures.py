#!/usr/bin/env python3
"""
Publication-quality figures for Nan Province Rainfall Trend Analysis
Target: Q1-Q2 journals (600 dpi, no overlapping elements, clear legends)
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib import gridspec
from pathlib import Path
import json
from scipy import stats

# ─── Style configuration ─────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':      'Times New Roman',
    'font.size':        10,
    'axes.titlesize':   11,
    'axes.labelsize':   10,
    'xtick.labelsize':  9,
    'ytick.labelsize':  9,
    'legend.fontsize':  8.5,
    'legend.framealpha': 0.85,
    'axes.spines.top':  False,
    'axes.spines.right':False,
    'axes.linewidth':   0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'lines.linewidth':  1.2,
    'figure.dpi':       150,   # screen preview; saved at 600
    'savefig.dpi':      600,
    'savefig.bbox':     'tight',
    'savefig.pad_inches': 0.05,
})

BASE    = Path(r'C:\MyPython\CMIP6Nan')
OUT_D   = BASE / 'trend_analysis_output'
FIG_D   = OUT_D / 'figures'
FIG_D.mkdir(exist_ok=True)

MODELS  = ['ACCESS-ESM1-5','CESM2','CanESM5','EC-Earth3',
           'FGOALS-g3','MIROC6','MRI-ESM2-0']
MODEL_SHORT = {'ACCESS-ESM1-5':'ACCESS','CESM2':'CESM2',
               'CanESM5':'CanESM5','EC-Earth3':'EC-Earth3',
               'FGOALS-g3':'FGOALS','MIROC6':'MIROC6',
               'MRI-ESM2-0':'MRI-ESM2'}

# Colour palette: 7 models + observed (8 colours total)
MODEL_COLORS = {
    'ACCESS-ESM1-5': '#1f77b4',
    'CESM2':         '#d62728',
    'CanESM5':       '#2ca02c',
    'EC-Earth3':     '#ff7f0e',
    'FGOALS-g3':     '#9467bd',
    'MIROC6':        '#8c564b',
    'MRI-ESM2-0':    '#e377c2',
    'Observed':      '#000000',
    'MME':           '#17becf',
}
SSP_COLOR = {'ssp245': '#2196F3', 'ssp585': '#F44336'}
SSP_LABEL = {'ssp245': 'SSP2-4.5', 'ssp585': 'SSP5-8.5'}
MK_COLOR  = {'increasing': '#d73027', 'decreasing': '#4575b4',
              'no trend':   '#bababa', 'insufficient': '#f0f0f0'}

# ─── Load data ───────────────────────────────────────────────────────────────
print("Loading data ...")
timeline = pd.read_csv(OUT_D / 'timeline_series.csv')
trend_df = pd.read_csv(OUT_D / 'trend_results_all.csv')
mme_df   = pd.read_csv(OUT_D / 'mme_series.csv')
with open(OUT_D / 'ita_data.json') as f:
    ita_data = json.load(f)

STA_F    = BASE / 'Station_latitude_longitude.csv'
sta_df   = pd.read_csv(STA_F)
NAN_STA  = [str(s) for s in sta_df['Station_ID'].tolist()]
print("Data loaded OK")

# ─── Smoothing helper ────────────────────────────────────────────────────────
def smooth(series, window=11):
    """Centered rolling mean, min_periods=5."""
    return pd.Series(series).rolling(window, center=True, min_periods=5).mean()

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Timeline: Annual Rainfall (Observed + all 7 models + MME)
# Two panels: SSP2-4.5 (top) and SSP5-8.5 (bottom)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_timeline_annual():
    print("  Figure 2: Annual timeline ...")
    obs = timeline[(timeline['model']=='Observed') & (timeline['scale']=='annual')]

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.0), sharex=True,
                             constrained_layout=True)
    for ax, ssp in zip(axes, ['ssp245','ssp585']):
        # Shaded MME IQR
        mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']=='annual')]
        ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                        color=SSP_COLOR[ssp], alpha=0.15, label='MME IQR (25–75%)')
        # Each model (thin, semi-transparent)
        for model in MODELS:
            ms = timeline[(timeline['model']==model) &
                          (timeline['scenario']==ssp) &
                          (timeline['scale']=='annual')]
            if ms.empty: continue
            ax.plot(ms['year'], smooth(ms['regional_mean'].values),
                    color=MODEL_COLORS[model], lw=0.8, alpha=0.65,
                    label=MODEL_SHORT[model])
        # MME median (thick)
        ax.plot(mm['year'], smooth(mm['mme_median'].values),
                color=SSP_COLOR[ssp], lw=2.2, label='MME Median', zorder=5)
        # Observed (black)
        ax.plot(obs['year'], obs['regional_mean'],
                color='black', lw=1.5, ls='-', label='Observed', zorder=6)
        # Vertical line at 2015
        ax.axvline(2015, color='gray', lw=1.0, ls='--', alpha=0.8)
        ax.text(2015.3, ax.get_ylim()[1]*0.98 if ax.get_ylim()[1]>0 else 1800,
                '2015', fontsize=7.5, color='gray', va='top')

        ax.set_ylabel('Annual Rainfall (mm)', labelpad=4)
        ax.set_title(f'({["a","b"][list(axes).index(ax)]}) {SSP_LABEL[ssp]}',
                     loc='left', fontweight='bold')
        ax.set_xlim(1981, 2100)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(200))
        ax.grid(axis='y', lw=0.4, ls=':', color='#cccccc')

        # Legend: avoid duplicates, place outside
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, ncol=3, fontsize=7.5,
                  loc='upper left', framealpha=0.85)

    axes[-1].set_xlabel('Year', labelpad=4)
    fig.suptitle('Regional Mean Annual Rainfall — Nan Province, Thailand\n'
                 '(Observed 1981–2014; CMIP6 Bias-Corrected 1981–2100)',
                 fontsize=10.5, fontweight='bold', y=1.01)
    fig.savefig(FIG_D / 'Fig2_Annual_Timeline.png')
    plt.close(fig)
    print("    saved Fig2_Annual_Timeline.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Timeline: Seasonal (Wet / Dry) × SSP — 4 panels
# ═══════════════════════════════════════════════════════════════════════════════
def fig_timeline_seasonal():
    print("  Figure 3: Seasonal timeline ...")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.0), sharex=True,
                             constrained_layout=True)
    panel_labels = [['(a)','(b)'],['(c)','(d)']]
    season_title = {'wet': 'Wet Season (May–Oct)', 'dry': 'Dry Season (Nov–Apr)'}

    for ci, ssp in enumerate(['ssp245','ssp585']):
        for ri, season in enumerate(['wet','dry']):
            ax = axes[ri][ci]
            obs_s = timeline[(timeline['model']=='Observed') &
                             (timeline['scale']==season)]
            mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']==season)]

            ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                            color=SSP_COLOR[ssp], alpha=0.15)
            for model in MODELS:
                ms = timeline[(timeline['model']==model) &
                              (timeline['scenario']==ssp) &
                              (timeline['scale']==season)]
                if ms.empty: continue
                ax.plot(ms['year'], smooth(ms['regional_mean'].values),
                        color=MODEL_COLORS[model], lw=0.8, alpha=0.6,
                        label=MODEL_SHORT[model])
            ax.plot(mm['year'], smooth(mm['mme_median'].values),
                    color=SSP_COLOR[ssp], lw=2.0, label='MME Median', zorder=5)
            if not obs_s.empty:
                ax.plot(obs_s['year'], obs_s['regional_mean'],
                        color='black', lw=1.4, label='Observed', zorder=6)
            ax.axvline(2015, color='gray', lw=0.9, ls='--', alpha=0.7)
            ax.set_title(f'{panel_labels[ri][ci]} {season_title[season]}\n{SSP_LABEL[ssp]}',
                         loc='left', fontweight='bold', fontsize=9)
            ax.set_xlim(1981, 2100)
            ax.grid(axis='y', lw=0.4, ls=':', color='#cccccc')
            ax.yaxis.set_major_locator(mticker.MultipleLocator(200))
            if ci == 0:
                ax.set_ylabel('Seasonal Rainfall (mm)', labelpad=4)
            if ri == 1:
                ax.set_xlabel('Year', labelpad=4)
            if ri == 0 and ci == 1:
                ax.legend(ncol=2, fontsize=7, loc='upper right', framealpha=0.85)

    fig.suptitle('Regional Mean Seasonal Rainfall — Nan Province, Thailand',
                 fontsize=10.5, fontweight='bold', y=1.01)
    fig.savefig(FIG_D / 'Fig3_Seasonal_Timeline.png')
    plt.close(fig)
    print("    saved Fig3_Seasonal_Timeline.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Mann-Kendall Trend Results: bar chart by model × period
# ═══════════════════════════════════════════════════════════════════════════════
def fig_mk_trends():
    print("  Figure 4: MK trend summary ...")
    # Extract regional mean results
    df = trend_df[trend_df['station'] == 'REGIONAL_MEAN'].copy()
    periods_order = ['1981-2014','historical','near_future','mid_future','far_future']

    fig, axes = plt.subplots(3, 2, figsize=(7.2, 9.0), constrained_layout=True)
    panel_idx = 0
    for ri, scale in enumerate(['annual','wet','dry']):
        for ci, ssp in enumerate(['ssp245','ssp585']):
            ax = axes[ri][ci]
            sub = df[(df['scale']==scale)]
            if ssp == 'ssp245':
                sub = sub[(sub['scenario'].isin(['observed','ssp245']))]
            else:
                sub = sub[(sub['scenario'].isin(['observed','ssp585']))]

            # One bar per model per period
            all_models = ['observed'] + MODELS
            y_pos = []
            bar_colors = []
            bar_widths = []
            slopes = []
            significances = []
            labels = []
            y = 0
            for model in all_models:
                m_sub = sub[sub['model'] == model if model != 'observed'
                            else sub['model'] == 'observed']
                for period in periods_order:
                    p_sub = m_sub[m_sub['period'] == period]
                    if p_sub.empty: continue
                    sl = p_sub['mk_slope'].values[0]
                    pv = p_sub['mk_p_value'].values[0]
                    tr = p_sub['mk_trend'].values[0] if 'mk_trend' in p_sub.columns else 'no trend'
                    slopes.append(sl if not np.isnan(sl) else 0)
                    bar_colors.append(MK_COLOR.get(tr, '#bababa'))
                    significances.append('*' if pv < 0.05 else '')
                    labels.append(f"{MODEL_SHORT.get(model, model[:6])}/{period[:4]}")
                    y_pos.append(y)
                    y += 1
                y += 0.5  # gap between models

            bars = ax.barh(y_pos, slopes, color=bar_colors, height=0.7,
                           edgecolor='white', linewidth=0.4)
            for yp, sig, slope in zip(y_pos, significances, slopes):
                if sig:
                    x_sig = slope + (0.3 if slope >= 0 else -0.3)
                    ax.text(x_sig, yp, '*', ha='center', va='center',
                            fontsize=9, color='#333333', fontweight='bold')
            ax.axvline(0, color='black', lw=0.7)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=6.5)
            scale_label = {'annual':'Annual','wet':'Wet Season','dry':'Dry Season'}[scale]
            ssp_lbl = SSP_LABEL.get(ssp, ssp)
            ax.set_title(f'({chr(97+panel_idx)}) {scale_label} / {ssp_lbl}',
                         loc='left', fontweight='bold', fontsize=8.5)
            ax.set_xlabel("Sen's Slope (mm yr⁻¹)", fontsize=8.5)
            ax.grid(axis='x', lw=0.4, ls=':', color='#cccccc')
            panel_idx += 1

    # Legend
    legend_patches = [mpatches.Patch(color=MK_COLOR[t], label=t.capitalize())
                      for t in ['increasing','decreasing','no trend']]
    legend_patches.append(Line2D([0],[0], marker='*', color='#333333',
                                  linestyle='None', markersize=7, label='p<0.05'))
    fig.legend(handles=legend_patches, loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5, framealpha=0.9)
    fig.suptitle("Mann-Kendall Trend Analysis — Nan Province Regional Mean\n"
                 "(* significant at p<0.05; Sen's slope in mm yr⁻¹)",
                 fontsize=10.5, fontweight='bold')
    fig.savefig(FIG_D / 'Fig4_MK_Trends.png')
    plt.close(fig)
    print("    saved Fig4_MK_Trends.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5 — Sen's Slope per Station × Model (heatmap style)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_sens_slope():
    print("  Figure 5: Sen's Slope heatmap ...")
    df = trend_df[(trend_df['station'] != 'REGIONAL_MEAN') &
                  (trend_df['period'] == 'full') &
                  (trend_df['scale'] == 'annual')].copy()

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.5), constrained_layout=True)
    for ax, ssp in zip(axes, ['ssp245','ssp585']):
        sub = df[df['scenario'] == ssp]
        if sub.empty:
            sub = df[df['model'] == 'observed']
        pivot = sub.pivot_table(index='station', columns='model',
                                values='mk_slope', aggfunc='mean')
        # Add observed column
        obs_sub = trend_df[(trend_df['station'] != 'REGIONAL_MEAN') &
                           (trend_df['period'] == '1981-2014') &
                           (trend_df['scale'] == 'annual') &
                           (trend_df['model'] == 'observed')]
        obs_piv = obs_sub.set_index('station')['mk_slope']
        pivot.insert(0, 'Observed', obs_piv)

        vmax = max(abs(pivot.values[np.isfinite(pivot.values)]).max(), 1)
        im = ax.imshow(pivot.values, aspect='auto', cmap='RdBu_r',
                       vmin=-vmax, vmax=vmax)
        ax.set_xticks(range(pivot.shape[1]))
        ax.set_xticklabels([MODEL_SHORT.get(c,c[:6]) for c in pivot.columns],
                           rotation=40, ha='right', fontsize=7)
        ax.set_yticks(range(pivot.shape[0]))
        ax.set_yticklabels(pivot.index.tolist(), fontsize=7)
        ax.set_title(f'({["a","b"][list(axes).index(ax)]}) {SSP_LABEL.get(ssp,ssp)}',
                     loc='left', fontweight='bold')

        # Significance asterisks
        sig_sub = sub if not sub.empty else pd.DataFrame()
        for ri, sta in enumerate(pivot.index):
            for ci, col in enumerate(pivot.columns):
                if col == 'Observed':
                    pv_row = trend_df[(trend_df['station']==sta) &
                                      (trend_df['period']=='1981-2014') &
                                      (trend_df['model']=='observed') &
                                      (trend_df['scale']=='annual')]
                else:
                    pv_row = sig_sub[(sig_sub['station']==sta) &
                                     (sig_sub['model']==col)]
                if pv_row.empty: continue
                pv = pv_row['mk_p_value'].values[0]
                if not np.isnan(pv) and pv < 0.05:
                    ax.text(ci, ri, '✦', ha='center', va='center',
                            fontsize=7, color='white')

        plt.colorbar(im, ax=ax, label="Sen's Slope (mm yr⁻¹)", shrink=0.85)

    fig.suptitle("Sen's Slope — Annual Rainfall per Station and Model (Full Period)\n"
                 "(✦ significant at p<0.05)", fontsize=10.5, fontweight='bold')
    fig.savefig(FIG_D / 'Fig5_Sens_Slope_Heatmap.png')
    plt.close(fig)
    print("    saved Fig5_Sens_Slope_Heatmap.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6 — ITA (Innovative Trend Analysis) scatter plots
# 1 row × 3 panels: Annual, Wet, Dry  (SSP2-4.5 and SSP5-8.5 overlaid)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_ita():
    print("  Figure 6: ITA plots ...")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.2), constrained_layout=True)
    scale_labels = {'annual':'(a) Annual','wet':'(b) Wet Season (May–Oct)',
                    'dry':'(c) Dry Season (Nov–Apr)'}
    for ax, scale in zip(axes, ['annual','wet','dry']):
        ax.set_aspect('equal')
        # 1:1 line
        all_vals = []
        plot_items = []
        for item in ita_data:
            if item['scale'] != scale: continue
            x = np.array(item['x']); y = np.array(item['y'])
            if len(x) == 0: continue
            all_vals.extend(x.tolist() + y.tolist())
            plot_items.append(item)

        if not all_vals:
            ax.set_title(scale_labels[scale], loc='left')
            continue
        vmin, vmax = min(all_vals)*0.95, max(all_vals)*1.05
        ax.plot([vmin, vmax],[vmin, vmax], 'k--', lw=0.8, alpha=0.6, label='1:1 line')

        for item in plot_items:
            x = np.array(item['x']); y = np.array(item['y'])
            ssp = item['scenario']
            model = item['model']
            if model == 'observed':
                ax.scatter(x, y, c='black', s=14, zorder=6, label='Observed', alpha=0.9)
            elif model == 'MME':
                c = SSP_COLOR.get(ssp, 'gray')
                ax.scatter(x, y, c=c, s=16, zorder=5, alpha=0.85,
                           label=f'MME {SSP_LABEL.get(ssp,ssp)}', edgecolors='white',
                           linewidths=0.4)

        ax.set_xlabel('First Half (sorted, mm)', fontsize=8.5)
        ax.set_ylabel('Second Half (sorted, mm)', fontsize=8.5)
        ax.set_title(scale_labels[scale], loc='left', fontweight='bold', fontsize=9)
        ax.set_xlim(vmin, vmax); ax.set_ylim(vmin, vmax)
        ax.grid(lw=0.4, ls=':', color='#cccccc')

        # Annotations
        ax.text(0.97, 0.03, 'Above 1:1: Increasing trend\nBelow 1:1: Decreasing trend',
                transform=ax.transAxes, fontsize=6.5, ha='right', va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    handles, labels = axes[1].get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        if l not in seen:
            seen[l] = h
    fig.legend(list(seen.values()), list(seen.keys()),
               loc='upper center', ncol=4, fontsize=7.5,
               bbox_to_anchor=(0.5, 1.04), framealpha=0.9)
    fig.suptitle('Innovative Trend Analysis (ITA) — Nan Province Regional Mean',
                 fontsize=10, fontweight='bold', y=1.10)
    fig.savefig(FIG_D / 'Fig6_ITA.png')
    plt.close(fig)
    print("    saved Fig6_ITA.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 7 — Future projection 2015-2100: MME ± IQR (both SSPs, 3 scales)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_future_projection():
    print("  Figure 7: Future projection ...")
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.5), sharex=True,
                             constrained_layout=True)
    scale_info = {'annual':('Annual Rainfall (mm)','(a) Annual'),
                  'wet':   ('Wet Season Rainfall (mm)','(b) Wet Season (May–Oct)'),
                  'dry':   ('Dry Season Rainfall (mm)','(c) Dry Season (Nov–Apr)')}
    for ax, scale in zip(axes, ['annual','wet','dry']):
        ylabel, title = scale_info[scale]
        # Observed baseline
        obs_s = timeline[(timeline['model']=='Observed') & (timeline['scale']==scale)]
        if not obs_s.empty:
            ax.plot(obs_s['year'], obs_s['regional_mean'],
                    color='black', lw=1.4, ls='-', label='Observed', zorder=10)
            # Observed mean line
            obs_mean = obs_s['regional_mean'].mean()
            ax.axhline(obs_mean, color='black', lw=0.8, ls=':', alpha=0.5)
        for ssp in ['ssp245','ssp585']:
            mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']==scale)]
            mm = mm[mm['year'] >= 2015]
            if mm.empty: continue
            c = SSP_COLOR[ssp]
            ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                            color=c, alpha=0.20)
            ax.fill_between(mm['year'], mm['mme_min'], mm['mme_max'],
                            color=c, alpha=0.08)
            ax.plot(mm['year'], smooth(mm['mme_median'].values, 21),
                    color=c, lw=2.2, label=f'{SSP_LABEL[ssp]} MME Median', zorder=6)
            # Individual models thin
            for model in MODELS:
                ms = timeline[(timeline['model']==model) &
                              (timeline['scenario']==ssp) &
                              (timeline['scale']==scale)]
                ms = ms[ms['year'] >= 2015]
                if ms.empty: continue
                ax.plot(ms['year'], smooth(ms['regional_mean'].values, 21),
                        color=MODEL_COLORS[model], lw=0.7, alpha=0.55)
        ax.axvline(2015, color='gray', lw=1.0, ls='--', alpha=0.8)
        ax.set_ylabel(ylabel, labelpad=4)
        ax.set_title(title, loc='left', fontweight='bold')
        ax.set_xlim(1981, 2100)
        ax.grid(axis='y', lw=0.4, ls=':', color='#cccccc')
        ax.yaxis.set_major_locator(mticker.MultipleLocator(200))
        if scale == 'annual':
            ax.legend(fontsize=8, ncol=2, loc='upper left', framealpha=0.85)

    axes[-1].set_xlabel('Year', labelpad=4)
    fig.suptitle('CMIP6 Projected Rainfall Change — Nan Province, Thailand\n'
                 '(Shaded: IQR 25–75% and full model range; lines: 21-yr smoothed MME median)',
                 fontsize=10.5, fontweight='bold')
    fig.savefig(FIG_D / 'Fig7_Future_Projection.png')
    plt.close(fig)
    print("    saved Fig7_Future_Projection.png")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 8 — Model spread: box plots per period × SSP
# ═══════════════════════════════════════════════════════════════════════════════
def fig_model_spread():
    print("  Figure 8: Model spread ...")
    PERIOD_COLS = {'historical':'1981–2014',
                   'near_future':'2021–2050',
                   'mid_future': '2051–2080',
                   'far_future': '2081–2100'}
    scales_to_plot = ['annual','wet','dry']
    fig, axes = plt.subplots(len(scales_to_plot), 2,
                             figsize=(7.2, 8.0), constrained_layout=True)
    scale_labels = {'annual':'Annual','wet':'Wet Season','dry':'Dry Season'}

    for ri, scale in enumerate(scales_to_plot):
        for ci, ssp in enumerate(['ssp245','ssp585']):
            ax = axes[ri][ci]
            box_data = []
            box_labels = []
            for period, plabel in PERIOD_COLS.items():
                sub = trend_df[(trend_df['station']=='REGIONAL_MEAN') &
                               (trend_df['scale']==scale) &
                               (trend_df['period']==period) &
                               (trend_df['model'].isin(MODELS)) &
                               (trend_df['scenario']==ssp)]['mk_slope'].dropna()
                if sub.empty: continue
                box_data.append(sub.values)
                box_labels.append(plabel)

            if not box_data:
                ax.set_visible(False); continue

            bp = ax.boxplot(box_data, patch_artist=True, widths=0.45,
                            medianprops=dict(color='black', lw=1.5),
                            whiskerprops=dict(lw=0.8),
                            capprops=dict(lw=0.8),
                            flierprops=dict(marker='o', markersize=4,
                                            markerfacecolor='gray', alpha=0.5))
            colors = [SSP_COLOR[ssp]] * len(box_data)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color); patch.set_alpha(0.5)

            # Overlay individual model points
            for xi, (sub_vals, period, plabel) in enumerate(
                    zip(box_data, list(PERIOD_COLS.keys()), box_labels), start=1):
                jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(sub_vals))
                for j, v in zip(jitter, sub_vals):
                    ax.scatter(xi + j, v, s=20, zorder=5,
                               color='#444444', alpha=0.7)

            ax.axhline(0, color='gray', lw=0.8, ls='--', alpha=0.6)
            ax.set_xticks(range(1, len(box_labels)+1))
            ax.set_xticklabels(box_labels, rotation=20, ha='right', fontsize=7.5)
            ax.set_ylabel("Sen's Slope (mm yr⁻¹)", fontsize=8.5)
            ax.set_title(f'({chr(97 + ri*2+ci)}) {scale_labels[scale]} / {SSP_LABEL[ssp]}',
                         loc='left', fontweight='bold', fontsize=8.5)
            ax.grid(axis='y', lw=0.4, ls=':', color='#cccccc')

    fig.suptitle("Model Spread in Rainfall Trend (Sen's Slope) by Period\n"
                 "(Dots: individual models; box: 25–75% range)",
                 fontsize=10.5, fontweight='bold')
    fig.savefig(FIG_D / 'Fig8_Model_Spread.png')
    plt.close(fig)
    print("    saved Fig8_Model_Spread.png")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=== Generating Publication-Quality Figures ===\n")
    fig_timeline_annual()
    fig_timeline_seasonal()
    fig_mk_trends()
    fig_sens_slope()
    fig_ita()
    fig_future_projection()
    fig_model_spread()
    print(f"\n=== ALL FIGURES DONE → {FIG_D} ===")
