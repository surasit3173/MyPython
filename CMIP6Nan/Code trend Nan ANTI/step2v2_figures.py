#!/usr/bin/env python3
"""
Publication-quality figures v2 — Nature-journal standard
Nan Province Rainfall Trend Analysis
600 dpi, Times New Roman, crisp, no overlap
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
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path
import json
from scipy import stats

# ─── Style: Nature/Science level ─────────────────────────────────────────────
plt.rcParams.update({
    'font.family':        'Times New Roman',
    'font.size':          11,
    'axes.titlesize':     11,
    'axes.labelsize':     10.5,
    'xtick.labelsize':    9.5,
    'ytick.labelsize':    9.5,
    'legend.fontsize':    9,
    'legend.framealpha':  0.92,
    'legend.edgecolor':   '#cccccc',
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.linewidth':     0.9,
    'xtick.major.width':  0.9,
    'ytick.major.width':  0.9,
    'xtick.major.size':   4,
    'ytick.major.size':   4,
    'lines.linewidth':    1.4,
    'figure.dpi':         150,
    'savefig.dpi':        600,
    'savefig.bbox':       'tight',
    'savefig.pad_inches': 0.08,
    'axes.grid':          False,
})

BASE  = Path(r'C:\MyPython\CMIP6Nan\Code trend Nan ANTI')
OUT_D = BASE / 'trend_analysis_output'
FIG_D = OUT_D / 'figures'
FIG_D.mkdir(exist_ok=True)

MODELS = ['ACCESS-ESM1-5','CESM2','CanESM5','EC-Earth3',
          'FGOALS-g3','MIROC6','MRI-ESM2-0']
MODEL_SHORT = {
    'ACCESS-ESM1-5': 'ACCESS-ESM1-5',
    'CESM2':         'CESM2',
    'CanESM5':       'CanESM5',
    'EC-Earth3':     'EC-Earth3',
    'FGOALS-g3':     'FGOALS-g3',
    'MIROC6':        'MIROC6',
    'MRI-ESM2-0':    'MRI-ESM2-0',
}

# Colour palette — ColorBrewer / Nature-style
MODEL_COLORS = {
    'ACCESS-ESM1-5': '#E69F00',
    'CESM2':         '#56B4E9',
    'CanESM5':       '#009E73',
    'EC-Earth3':     '#F0E442',
    'FGOALS-g3':     '#0072B2',
    'MIROC6':        '#D55E00',
    'MRI-ESM2-0':    '#CC79A7',
    'Observed':      '#000000',
    'MME':           '#333333',
}
MODEL_LS = {
    'ACCESS-ESM1-5': '-',
    'CESM2':         '--',
    'CanESM5':       '-.',
    'EC-Earth3':     ':',
    'FGOALS-g3':     (0,(5,2)),
    'MIROC6':        (0,(3,1,1,1)),
    'MRI-ESM2-0':    (0,(5,1)),
}

SSP_COLOR = {'ssp245': '#2166ac', 'ssp585': '#d6604d'}
SSP_LABEL = {'ssp245': 'SSP2-4.5', 'ssp585': 'SSP5-8.5'}
MK_COLOR  = {
    'increasing':   '#d73027',
    'decreasing':   '#4575b4',
    'no trend':     '#d9d9d9',
    'insufficient': '#f0f0f0',
}

# ─── Load data ────────────────────────────────────────────────────────────────
print("Loading data ...")
timeline = pd.read_csv(OUT_D / 'timeline_series.csv')
trend_df = pd.read_csv(OUT_D / 'trend_results_all.csv')
mme_df   = pd.read_csv(OUT_D / 'mme_series.csv')
with open(OUT_D / 'ita_data.json') as f:
    ita_data = json.load(f)
sta_df  = pd.read_csv(Path(r'C:\MyPython\CMIP6Nan') / 'Station_latitude_longitude.csv')
NAN_STA = [str(s) for s in sta_df['Station_ID'].tolist()]
print("Data loaded OK")

# ─── Helpers ─────────────────────────────────────────────────────────────────
def smooth(series, window=11):
    return pd.Series(series).rolling(window, center=True, min_periods=5).mean()

def add_panel_letter(ax, letter, x=0.01, y=0.97):
    ax.text(x, y, letter, transform=ax.transAxes,
            fontsize=12, fontweight='bold', va='top', ha='left')

def add_vline_2015(ax, ymax_frac=0.97):
    ax.axvline(2015, color='#555555', lw=1.0, ls='--', alpha=0.9, zorder=2)
    ylims = ax.get_ylim()
    ypos  = ylims[0] + (ylims[1]-ylims[0])*ymax_frac
    ax.text(2015.5, ypos, 'Historical/\nProjection',
            fontsize=8, color='#555555', va='top', ha='left')

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Annual Timeline (2 panels: SSP2-4.5 / SSP5-8.5)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_timeline_annual():
    print("  Figure 2: Annual timeline ...")
    obs = timeline[(timeline['model']=='Observed') & (timeline['scale']=='annual')]

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 7.2), sharex=True,
                             gridspec_kw={'hspace': 0.08})
    panel_letters = ['(a)', '(b)']
    for idx, (ax, ssp) in enumerate(zip(axes, ['ssp245','ssp585'])):
        mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']=='annual')]

        # Full range shading (very faint)
        ax.fill_between(mm['year'], mm['mme_min'], mm['mme_max'],
                        color=SSP_COLOR[ssp], alpha=0.07, zorder=1)
        # IQR shading
        ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                        color=SSP_COLOR[ssp], alpha=0.18, zorder=2,
                        label='MME IQR (25–75%)')

        # Each model (thin, distinct style)
        for model in MODELS:
            ms = timeline[(timeline['model']==model) &
                          (timeline['scenario']==ssp) &
                          (timeline['scale']=='annual')]
            if ms.empty: continue
            ax.plot(ms['year'], smooth(ms['regional_mean'].values, 11),
                    color=MODEL_COLORS[model],
                    lw=0.85, alpha=0.7,
                    linestyle=MODEL_LS[model],
                    label=MODEL_SHORT[model])

        # MME median (thick, scenario colour)
        ax.plot(mm['year'], smooth(mm['mme_median'].values, 11),
                color=SSP_COLOR[ssp], lw=2.5,
                label=f'MME Median ({SSP_LABEL[ssp]})', zorder=6)

        # Observed (solid black, no smoothing)
        if not obs.empty:
            ax.plot(obs['year'], obs['regional_mean'],
                    color='#000000', lw=1.8, ls='-',
                    label='Observed', zorder=8)

        # Vertical 2015 line
        ax.axvline(2015, color='#666666', lw=0.9, ls='--', alpha=0.9, zorder=3)
        ylims = ax.get_ylim()
        ax.text(2015.3, ylims[1]*0.99,
                '2015', fontsize=8, color='#666666', va='top')

        ax.set_ylabel('Annual Rainfall (mm yr\u207b\u00b9)', labelpad=5)
        ax.set_xlim(1981, 2100)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(250))
        ax.yaxis.set_minor_locator(mticker.MultipleLocator(50))
        ax.xaxis.set_major_locator(mticker.MultipleLocator(20))
        ax.tick_params(axis='both', direction='out')

        # Y-axis grid only
        ax.yaxis.grid(True, lw=0.35, ls=':', color='#cccccc', zorder=0)

        # SSP label in top-right corner
        ax.text(0.98, 0.96, SSP_LABEL[ssp],
                transform=ax.transAxes, ha='right', va='top',
                fontsize=11, fontweight='bold',
                color=SSP_COLOR[ssp],
                bbox=dict(boxstyle='round,pad=0.3',
                          facecolor='white', edgecolor=SSP_COLOR[ssp],
                          alpha=0.85))

        add_panel_letter(ax, panel_letters[idx])

        # Legend — outside right
        handles, labels = ax.get_legend_handles_labels()
        # De-duplicate
        seen = {}
        for h, l in zip(handles, labels):
            if l not in seen: seen[l] = h
        ax.legend(list(seen.values()), list(seen.keys()),
                  loc='upper left', fontsize=8,
                  ncol=2, framealpha=0.9,
                  edgecolor='#cccccc',
                  handlelength=2.0)

    axes[-1].set_xlabel('Year', labelpad=5)
    fig.suptitle('Regional Mean Annual Rainfall — Nan Province, Thailand\n'
                 '(Observed 1981–2014; CMIP6 Bias-Corrected Projections 1981–2100)',
                 fontsize=11, fontweight='bold', y=1.01)
    fig.savefig(FIG_D / 'Fig2_Annual_Timeline.png')
    plt.close(fig)
    print("    saved Fig2_Annual_Timeline.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Seasonal Timeline (2×2: Wet/Dry × SSP)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_timeline_seasonal():
    print("  Figure 3: Seasonal timeline ...")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.0),
                             sharex=True,
                             gridspec_kw={'hspace': 0.06, 'wspace': 0.22})
    panel_labels = [['(a)', '(b)'], ['(c)', '(d)']]
    season_title = {
        'wet': 'Wet Season (May–Oct)',
        'dry': 'Dry Season (Nov–Apr)',
    }
    for ri, season in enumerate(['wet','dry']):
        for ci, ssp in enumerate(['ssp245','ssp585']):
            ax = axes[ri][ci]
            obs_s = timeline[(timeline['model']=='Observed') &
                             (timeline['scale']==season)]
            mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']==season)]

            ax.fill_between(mm['year'], mm['mme_min'], mm['mme_max'],
                            color=SSP_COLOR[ssp], alpha=0.07, zorder=1)
            ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                            color=SSP_COLOR[ssp], alpha=0.18, zorder=2)

            for model in MODELS:
                ms = timeline[(timeline['model']==model) &
                              (timeline['scenario']==ssp) &
                              (timeline['scale']==season)]
                if ms.empty: continue
                ax.plot(ms['year'], smooth(ms['regional_mean'].values, 11),
                        color=MODEL_COLORS[model], lw=0.85, alpha=0.65,
                        linestyle=MODEL_LS[model])

            ax.plot(mm['year'], smooth(mm['mme_median'].values, 11),
                    color=SSP_COLOR[ssp], lw=2.4, zorder=6,
                    label=f'MME Median ({SSP_LABEL[ssp]})')

            if not obs_s.empty:
                ax.plot(obs_s['year'], obs_s['regional_mean'],
                        color='#000000', lw=1.8, zorder=8, label='Observed')

            ax.axvline(2015, color='#666666', lw=0.9, ls='--', alpha=0.8, zorder=3)
            ax.set_xlim(1981, 2100)
            ax.yaxis.grid(True, lw=0.35, ls=':', color='#cccccc', zorder=0)
            ax.yaxis.set_major_locator(mticker.MultipleLocator(200))
            ax.xaxis.set_major_locator(mticker.MultipleLocator(30))
            ax.tick_params(axis='both', direction='out')

            # Panel title (season inside box)
            ax.text(0.98, 0.97,
                    f'{SSP_LABEL[ssp]}',
                    transform=ax.transAxes, ha='right', va='top',
                    fontsize=9.5, fontweight='bold', color=SSP_COLOR[ssp])
            add_panel_letter(ax, panel_labels[ri][ci])

            if ri == 0:
                ax.set_title(f'{season_title[season]}', fontsize=10)
            if ci == 0:
                ax.set_ylabel('Seasonal Rainfall (mm)', labelpad=4)
            if ri == 1:
                ax.set_xlabel('Year', labelpad=4)

    # Shared legend at bottom
    model_handles = [Line2D([0],[0], color=MODEL_COLORS[m], lw=1.4,
                            linestyle=MODEL_LS[m],
                            label=MODEL_SHORT[m]) for m in MODELS]
    obs_handle    = Line2D([0],[0], color='black', lw=2, label='Observed')
    ssp_handles   = [mpatches.Patch(color=SSP_COLOR[s], alpha=0.6,
                                    label=f'MME IQR {SSP_LABEL[s]}')
                     for s in ['ssp245','ssp585']]
    all_handles = model_handles + [obs_handle] + ssp_handles
    fig.legend(handles=all_handles,
               loc='lower center', ncol=5, fontsize=7.5,
               bbox_to_anchor=(0.5, -0.06), framealpha=0.92,
               edgecolor='#cccccc', handlelength=2.2)

    fig.suptitle('Regional Mean Seasonal Rainfall — Nan Province, Thailand',
                 fontsize=11, fontweight='bold')
    fig.savefig(FIG_D / 'Fig3_Seasonal_Timeline.png')
    plt.close(fig)
    print("    saved Fig3_Seasonal_Timeline.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Mann-Kendall results: horizontal bar chart (3×2)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_mk_trends():
    print("  Figure 4: MK trend summary ...")
    df = trend_df[trend_df['station'] == 'REGIONAL_MEAN'].copy()
    periods_order = ['1981-2014','historical','near_future','mid_future','far_future']
    period_labels = {
        '1981-2014':   'Obs 1981–2014',
        'historical':  'Hist 1981–2014',
        'near_future': 'Near 2021–2050',
        'mid_future':  'Mid 2051–2080',
        'far_future':  'Far 2081–2100',
    }

    fig, axes = plt.subplots(3, 2, figsize=(7.2, 10.5),
                             constrained_layout=True)
    panel_idx = 0
    for ri, scale in enumerate(['annual','wet','dry']):
        for ci, ssp in enumerate(['ssp245','ssp585']):
            ax = axes[ri][ci]
            sub = df[df['scale']==scale]
            sub = sub[sub['scenario'].isin(['observed', ssp])]

            all_models = ['observed'] + MODELS
            y_pos, bar_colors, slopes, significances, labels = [], [], [], [], []
            y = 0
            for model in all_models:
                m_sub = sub[sub['model'] == model]
                for period in periods_order:
                    p_sub = m_sub[m_sub['period'] == period]
                    if p_sub.empty: continue
                    sl  = p_sub['mk_slope'].values[0]
                    pv  = p_sub['mk_p_value'].values[0]
                    tr  = p_sub['mk_trend'].values[0] if 'mk_trend' in p_sub.columns else 'no trend'
                    slopes.append(float(sl) if not np.isnan(sl) else 0.0)
                    bar_colors.append(MK_COLOR.get(tr, '#d9d9d9'))
                    significances.append('*' if pv < 0.05 else '')
                    labels.append(f"{MODEL_SHORT.get(model, model[:8])[:8]}/{period_labels.get(period,period)[:4]}")
                    y_pos.append(y); y += 1
                y += 0.6  # gap between models

            if not slopes:
                ax.set_visible(False); panel_idx += 1; continue

            ax.barh(y_pos, slopes, color=bar_colors, height=0.75,
                    edgecolor='white', linewidth=0.3)
            for yp, sig, slope in zip(y_pos, significances, slopes):
                if sig:
                    xoff = max(abs(slope)*0.08, 0.3) * np.sign(slope) if slope != 0 else 0.3
                    ax.text(slope + xoff, yp, sig, ha='center', va='center',
                            fontsize=8, color='#111111', fontweight='bold')

            ax.axvline(0, color='black', lw=0.8, zorder=5)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=6.0)
            scale_label = {'annual':'Annual','wet':'Wet Season','dry':'Dry Season'}[scale]
            ax.set_title(f'({chr(97+panel_idx)}) {scale_label} / {SSP_LABEL[ssp]}',
                         loc='left', fontweight='bold', fontsize=8.5)
            ax.set_xlabel("Sen's Slope (mm yr\u207b\u00b9)", fontsize=8.5)
            ax.xaxis.grid(True, lw=0.35, ls=':', color='#cccccc', zorder=0)
            panel_idx += 1

    legend_patches = [
        mpatches.Patch(color=MK_COLOR['increasing'],   label='Increasing'),
        mpatches.Patch(color=MK_COLOR['decreasing'],   label='Decreasing'),
        mpatches.Patch(color=MK_COLOR['no trend'],     label='No trend'),
        Line2D([0],[0], marker='*', color='#111111', linestyle='None',
               markersize=10, label='p<0.05'),
    ]
    fig.legend(handles=legend_patches, loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.01), fontsize=9, framealpha=0.92)
    fig.suptitle("Mann-Kendall Trend Analysis — Nan Province Regional Mean\n"
                 "(Sen's Slope mm yr\u207b\u00b9; ★ p<0.05)",
                 fontsize=11, fontweight='bold')
    fig.savefig(FIG_D / 'Fig4_MK_Trends.png')
    plt.close(fig)
    print("    saved Fig4_MK_Trends.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5 — Sen's Slope heatmap per station × model (full period)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_sens_slope():
    print("  Figure 5: Sen's Slope heatmap ...")
    periods = [('1981-2014', 'observed'), ('full','ssp245'), ('full','ssp585')]
    period_labels = {
        '1981-2014': "Obs 1981–2014",
        'full_ssp245': "CMIP6 SSP2-4.5\n(full 1981–2100)",
        'full_ssp585': "CMIP6 SSP5-8.5\n(full 1981–2100)",
    }

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 5.2), constrained_layout=True)

    for ax, ssp in zip(axes, ['ssp245','ssp585']):
        # Get model data (full period)
        sub = trend_df[
            (trend_df['station'] != 'REGIONAL_MEAN') &
            (trend_df['period'] == 'full') &
            (trend_df['scale'] == 'annual') &
            (trend_df['scenario'] == ssp)
        ].copy()

        # Get observed data
        obs_sub = trend_df[
            (trend_df['station'] != 'REGIONAL_MEAN') &
            (trend_df['period'] == '1981-2014') &
            (trend_df['scale'] == 'annual') &
            (trend_df['model'] == 'observed')
        ].copy()

        pivot = sub.pivot_table(index='station', columns='model',
                                values='mk_slope', aggfunc='mean')
        obs_piv = obs_sub.set_index('station')['mk_slope']
        pivot.insert(0, 'Observed', obs_piv)

        # Sort stations by latitude (south→north)
        sta_lat = sta_df.set_index('Station_ID')['latitude'].to_dict()
        pivot.index = [int(s) for s in pivot.index]
        pivot = pivot.sort_index(key=lambda idx: [sta_lat.get(i, 0) for i in idx])
        pivot.index = [str(s) for s in pivot.index]

        fin_vals = pivot.values[np.isfinite(pivot.values)]
        vmax = float(np.percentile(np.abs(fin_vals), 95)) if len(fin_vals) > 0 else 5
        norm = TwoSlopeNorm(vcenter=0, vmin=-vmax, vmax=vmax)

        im = ax.imshow(pivot.values, aspect='auto', cmap='RdBu_r', norm=norm)
        ax.set_xticks(range(pivot.shape[1]))
        ax.set_xticklabels(
            ['Obs'] + [MODEL_SHORT.get(c, c[:8]) for c in pivot.columns[1:]],
            rotation=45, ha='right', fontsize=7.5
        )
        ax.set_yticks(range(pivot.shape[0]))
        ax.set_yticklabels(pivot.index.tolist(), fontsize=8)
        ax.set_title(f'({["a","b"][list(axes).index(ax)]}) {SSP_LABEL.get(ssp,ssp)}',
                     loc='left', fontweight='bold')

        # Significance markers
        for ri, sta in enumerate(pivot.index):
            for ci2, col in enumerate(pivot.columns):
                if col == 'Observed':
                    pv_row = obs_sub[obs_sub['station'] == sta]
                else:
                    pv_row = sub[(sub['station']==sta) & (sub['model']==col)]
                if pv_row.empty: continue
                pv = pv_row['mk_p_value'].values[0]
                if not np.isnan(pv) and pv < 0.05:
                    ax.text(ci2, ri, '*', ha='center', va='center',
                            fontsize=10, color='white', fontweight='bold')

        cbar = plt.colorbar(im, ax=ax, shrink=0.88, pad=0.02)
        cbar.set_label("Sen's Slope (mm yr\u207b\u00b9)", fontsize=9)
        cbar.ax.tick_params(labelsize=8)
        ax.set_xlabel('Model', labelpad=5)
        ax.set_ylabel('Station ID (S→N)', labelpad=5)

    fig.suptitle("Sen's Slope — Annual Rainfall per Station × Model\n"
                 "(Full Period; ★ = p<0.05; sorted south→north)",
                 fontsize=11, fontweight='bold')
    fig.savefig(FIG_D / 'Fig5_Sens_Slope_Heatmap.png')
    plt.close(fig)
    print("    saved Fig5_Sens_Slope_Heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6 — ITA scatter plots (Annual, Wet, Dry) — 1×3 panels
# ═══════════════════════════════════════════════════════════════════════════════
def fig_ita():
    print("  Figure 6: ITA plots ...")
    scale_labels = {
        'annual': '(a) Annual',
        'wet':    '(b) Wet Season\n(May–Oct)',
        'dry':    '(c) Dry Season\n(Nov–Apr)',
    }
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.4), constrained_layout=True)

    for ax, scale in zip(axes, ['annual','wet','dry']):
        ax.set_aspect('equal', adjustable='box')

        all_vals = []
        plot_obs   = []
        plot_mme   = {ssp: [] for ssp in ['ssp245','ssp585']}

        for item in ita_data:
            if item['scale'] != scale: continue
            x = np.array(item['x']); y = np.array(item['y'])
            if len(x) == 0: continue
            all_vals.extend(x.tolist() + y.tolist())
            model = item.get('model','')
            ssp   = item.get('scenario','')
            if model == 'observed':
                plot_obs.append((x, y))
            elif model == 'MME':
                if ssp in plot_mme:
                    plot_mme[ssp].append((x, y))

        if not all_vals:
            ax.set_title(scale_labels[scale], loc='left', fontweight='bold')
            continue

        vmin = min(all_vals) * 0.93
        vmax = max(all_vals) * 1.07
        ax.plot([vmin,vmax],[vmin,vmax], 'k--', lw=1.0, alpha=0.55,
                label='1:1 (no trend)')

        # Shaded zones
        ax.fill_between([vmin,vmax],[vmin,vmax],[vmax,vmax],
                        color='#d6604d', alpha=0.05)
        ax.fill_between([vmin,vmax],[vmin,vmin],[vmin,vmax],
                        color='#4575b4', alpha=0.05)

        # Observed
        for x, y in plot_obs:
            ax.scatter(x, y, c='#000000', s=22, zorder=8,
                       label='Observed', alpha=0.9, edgecolors='none')

        # MME per SSP
        for ssp, pairs in plot_mme.items():
            for x, y in pairs:
                ax.scatter(x, y, c=SSP_COLOR[ssp], s=20, zorder=7,
                           alpha=0.85, edgecolors='white', linewidths=0.3,
                           label=f'MME {SSP_LABEL[ssp]}')

        ax.set_xlabel('First half (sorted, mm)', fontsize=9)
        ax.set_ylabel('Second half (sorted, mm)', fontsize=9)
        ax.set_title(scale_labels[scale], loc='left', fontweight='bold', fontsize=9.5)
        ax.set_xlim(vmin, vmax); ax.set_ylim(vmin, vmax)
        ax.xaxis.grid(True, lw=0.35, ls=':', color='#cccccc')
        ax.yaxis.grid(True, lw=0.35, ls=':', color='#cccccc')

        ax.text(0.97, 0.03,
                'Above 1:1:\nIncreasing\n\nBelow 1:1:\nDecreasing',
                transform=ax.transAxes, fontsize=7, ha='right', va='bottom',
                color='#333333',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                          edgecolor='#cccccc', alpha=0.85))

        add_panel_letter(ax, scale_labels[scale].split('\n')[0][:3])

    handles, labels = axes[0].get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        if l not in seen: seen[l] = h
    fig.legend(list(seen.values()), list(seen.keys()),
               loc='lower center', ncol=4, fontsize=8.5,
               bbox_to_anchor=(0.5, -0.06), framealpha=0.92,
               edgecolor='#cccccc')
    fig.suptitle('Innovative Trend Analysis (ITA) — Nan Province Regional Mean',
                 fontsize=11, fontweight='bold')
    fig.savefig(FIG_D / 'Fig6_ITA.png')
    plt.close(fig)
    print("    saved Fig6_ITA.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 7 — Future Projections 2015–2100 (3 panels: Annual, Wet, Dry)
# Both SSPs on same panel, MME median + IQR + model range
# ═══════════════════════════════════════════════════════════════════════════════
def fig_future_projection():
    print("  Figure 7: Future projection ...")
    scale_info = {
        'annual': ('Annual Rainfall (mm yr\u207b\u00b9)', '(a) Annual'),
        'wet':    ('Wet Season Rainfall (mm)',          '(b) Wet Season (May–Oct)'),
        'dry':    ('Dry Season Rainfall (mm)',          '(c) Dry Season (Nov–Apr)'),
    }

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 9.0), sharex=True,
                             gridspec_kw={'hspace': 0.08})

    for ax, scale in zip(axes, ['annual','wet','dry']):
        ylabel, title = scale_info[scale]

        # Observed (all years up to 2014)
        obs_s = timeline[(timeline['model']=='Observed') & (timeline['scale']==scale)]
        if not obs_s.empty:
            ax.plot(obs_s['year'], obs_s['regional_mean'],
                    color='#000000', lw=1.8, ls='-', label='Observed', zorder=10)
            obs_mean = obs_s['regional_mean'].mean()
            ax.axhline(obs_mean, color='#000000', lw=0.75, ls=':',
                       alpha=0.5, zorder=2)

        for ssp in ['ssp245','ssp585']:
            mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']==scale)]
            mm = mm[mm['year'] >= 2015].copy()
            if mm.empty: continue
            c = SSP_COLOR[ssp]

            # Full model range (very faint)
            ax.fill_between(mm['year'], mm['mme_min'], mm['mme_max'],
                            color=c, alpha=0.07, zorder=1)
            # IQR 25–75%
            ax.fill_between(mm['year'], mm['q25'], mm['q75'],
                            color=c, alpha=0.22, zorder=2,
                            label=f'{SSP_LABEL[ssp]} IQR')

            # Individual model traces (very thin)
            for model in MODELS:
                ms = timeline[(timeline['model']==model) &
                              (timeline['scenario']==ssp) &
                              (timeline['scale']==scale)]
                ms = ms[ms['year'] >= 2015]
                if ms.empty: continue
                ax.plot(ms['year'], smooth(ms['regional_mean'].values, 21),
                        color=MODEL_COLORS[model], lw=0.65, alpha=0.45,
                        linestyle=MODEL_LS[model])

            # MME median (thick)
            ax.plot(mm['year'], smooth(mm['mme_median'].values, 21),
                    color=c, lw=2.5,
                    label=f'{SSP_LABEL[ssp]} MME Median', zorder=7)

            # Decade mean markers
            for period_start, period_end in [(2021,2050),(2051,2080),(2081,2100)]:
                sub_mm = mm[(mm['year']>=period_start) & (mm['year']<=period_end)]
                if sub_mm.empty: continue
                pmean = sub_mm['mme_median'].mean()
                pmid  = (period_start + period_end) / 2
                ax.scatter(pmid, pmean, s=50, color=c, zorder=9,
                           edgecolors='white', linewidths=0.8, marker='D')

        # Historical/projection boundary
        ax.axvline(2015, color='#555555', lw=1.0, ls='--', alpha=0.85, zorder=4)
        ax.text(2015.4, ax.get_ylim()[1]*0.99,
                '2015', fontsize=8, color='#555555', va='top')

        ax.set_ylabel(ylabel, labelpad=5)
        add_panel_letter(ax, title[:3])
        ax.text(0.02, 0.96, title[4:], transform=ax.transAxes,
                fontsize=10, va='top', ha='left', fontweight='bold')
        ax.set_xlim(1981, 2100)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(200))
        ax.xaxis.set_major_locator(mticker.MultipleLocator(20))
        ax.tick_params(axis='both', direction='out')
        ax.yaxis.grid(True, lw=0.35, ls=':', color='#cccccc', zorder=0)

        if scale == 'annual':
            handles, labels = ax.get_legend_handles_labels()
            seen = {}
            for h, l in zip(handles, labels):
                if l not in seen: seen[l] = h
            ax.legend(list(seen.values()), list(seen.keys()),
                      loc='upper right', fontsize=8, ncol=2,
                      framealpha=0.92, edgecolor='#cccccc')

    axes[-1].set_xlabel('Year', labelpad=5)
    fig.suptitle('CMIP6 Projected Rainfall — Nan Province, Thailand\n'
                 '(Shaded: IQR 25–75%; solid: 21-yr smoothed MME median; ◆: period mean)',
                 fontsize=11, fontweight='bold', y=1.01)
    fig.savefig(FIG_D / 'Fig7_Future_Projection.png')
    plt.close(fig)
    print("    saved Fig7_Future_Projection.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 8 — Model Spread: box plots per period (3 scales × 2 SSP = 6 panels)
# ═══════════════════════════════════════════════════════════════════════════════
def fig_model_spread():
    print("  Figure 8: Model spread ...")
    PERIOD_COLS = {
        'historical':  '1981–2014',
        'near_future': '2021–2050',
        'mid_future':  '2051–2080',
        'far_future':  '2081–2100',
    }
    scales_to_plot = ['annual','wet','dry']
    scale_labels   = {'annual':'Annual','wet':'Wet Season','dry':'Dry Season'}

    fig, axes = plt.subplots(len(scales_to_plot), 2,
                             figsize=(7.2, 8.5), constrained_layout=True)

    rng = np.random.default_rng(42)

    for ri, scale in enumerate(scales_to_plot):
        for ci, ssp in enumerate(['ssp245','ssp585']):
            ax = axes[ri][ci]
            box_data, box_labels, box_model_names = [], [], []
            for period, plabel in PERIOD_COLS.items():
                sub = trend_df[
                    (trend_df['station']=='REGIONAL_MEAN') &
                    (trend_df['scale']==scale) &
                    (trend_df['period']==period) &
                    (trend_df['model'].isin(MODELS)) &
                    (trend_df['scenario']==ssp)
                ]['mk_slope'].dropna()
                if sub.empty: continue
                box_data.append(sub.values)
                box_labels.append(plabel)
                sub_models = trend_df[
                    (trend_df['station']=='REGIONAL_MEAN') &
                    (trend_df['scale']==scale) &
                    (trend_df['period']==period) &
                    (trend_df['model'].isin(MODELS)) &
                    (trend_df['scenario']==ssp)
                ][['model','mk_slope']].dropna()
                box_model_names.append(sub_models)

            if not box_data:
                ax.set_visible(False); continue

            c = SSP_COLOR[ssp]
            bp = ax.boxplot(box_data, patch_artist=True, widths=0.45,
                            medianprops=dict(color='black', lw=2.0),
                            whiskerprops=dict(lw=0.9, color='#555555'),
                            capprops=dict(lw=0.9, color='#555555'),
                            flierprops=dict(marker='o', markersize=4,
                                            markerfacecolor='#888888',
                                            markeredgecolor='none', alpha=0.5))
            for patch in bp['boxes']:
                patch.set_facecolor(c); patch.set_alpha(0.45)

            # Individual model dots with distinct colours + legend
            for xi, (sub_vals, sub_models_df) in enumerate(
                    zip(box_data, box_model_names), start=1):
                for _, row in sub_models_df.iterrows():
                    m     = row['model']
                    v     = row['mk_slope']
                    jitter = rng.uniform(-0.12, 0.12)
                    ax.scatter(xi + jitter, v, s=28, zorder=5,
                               color=MODEL_COLORS.get(m,'#444'),
                               edgecolors='white', linewidths=0.5,
                               marker='o', alpha=0.85)

            ax.axhline(0, color='#555555', lw=0.75, ls='--', alpha=0.7)
            ax.set_xticks(range(1, len(box_labels)+1))
            ax.set_xticklabels(box_labels, rotation=25, ha='right', fontsize=8.5)
            ax.set_ylabel("Sen's Slope (mm yr\u207b\u00b9)", fontsize=9)
            ax.set_title(
                f'({chr(97 + ri*2+ci)}) {scale_labels[scale]} / {SSP_LABEL[ssp]}',
                loc='left', fontweight='bold', fontsize=9)
            ax.yaxis.grid(True, lw=0.35, ls=':', color='#cccccc', zorder=0)

    # Shared legend (model colours)
    model_handles = [
        Line2D([0],[0], marker='o', color='w',
               markerfacecolor=MODEL_COLORS[m], markersize=7,
               label=MODEL_SHORT[m])
        for m in MODELS
    ]
    fig.legend(handles=model_handles,
               loc='lower center', ncol=4, fontsize=8,
               bbox_to_anchor=(0.5, -0.03), framealpha=0.92,
               edgecolor='#cccccc', handletextpad=0.4)
    fig.suptitle("Model Spread in Rainfall Trend (Sen's Slope) by Period\n"
                 "(Box: 25–75%; coloured dots: individual models; line: median)",
                 fontsize=11, fontweight='bold')
    fig.savefig(FIG_D / 'Fig8_Model_Spread.png')
    plt.close(fig)
    print("    saved Fig8_Model_Spread.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== Generating Nature-level Figures (v2) ===\n")
    fig_timeline_annual()
    fig_timeline_seasonal()
    fig_mk_trends()
    fig_sens_slope()
    fig_ita()
    fig_future_projection()
    fig_model_spread()
    print(f"\nDONE. Figures saved to: {FIG_D}")
