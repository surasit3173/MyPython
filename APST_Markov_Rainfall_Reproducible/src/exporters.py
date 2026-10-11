import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


def export_analysis_tables(output_dir, markov_df, spells_df, stability_df, meta_df=None):
    """Export summary tables to CSV and Excel."""
    os.makedirs(output_dir, exist_ok=True)

    excel_path = os.path.join(output_dir, 'Markov_Rainfall_Analysis_Summary.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        if meta_df is not None:
            meta_df.to_excel(writer, sheet_name='Station_Metadata', index=False)
        markov_df.to_excel(writer, sheet_name='Markov_Transitions', index=False)
        spells_df.to_excel(writer, sheet_name='Spell_Statistics', index=False)
        if stability_df is not None:
            stability_df.to_excel(writer, sheet_name='Temporal_Stability', index=False)

    markov_df.to_csv(os.path.join(output_dir, 'Table1_Markov_Transitions.csv'), index=False)
    spells_df.to_csv(os.path.join(output_dir, 'Table2_Spell_Statistics.csv'), index=False)
    if stability_df is not None:
        stability_df.to_csv(os.path.join(output_dir, 'Table3_Temporal_Stability.csv'), index=False)


def generate_publication_figures(output_dir, markov_df, spells_df, stability_df, meta_df=None, dpi=300):
    """Generate high-resolution figures for paper manuscript."""
    fig_dir = os.path.join(output_dir, 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # Figure 1: Spatial Transition Probabilities P01 and P11 across Stations
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(markov_df))
    width = 0.35

    ax.bar(x - width/2, markov_df['p01'], width, label='P01 (Dry -> Wet)', color='#2b5c8f')
    ax.bar(x + width/2, markov_df['p11'], width, label='P11 (Wet -> Wet)', color='#d95f02')

    ax.set_xlabel('Station ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Probability', fontsize=12, fontweight='bold')
    ax.set_title('Spatial Distribution of Markov Transition Probabilities', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(markov_df['station_id'], rotation=45)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(fig_dir, 'Figure1_Markov_Transition_Probabilities.png'), dpi=dpi)
    fig.savefig(os.path.join(fig_dir, 'Figure1_Markov_Transition_Probabilities.pdf'), dpi=dpi)
    plt.close(fig)

    # Figure 2: Mean Dry vs Wet Spell Length
    fig, ax = plt.subplots(figsize=(10, 6))
    x_spells = np.arange(len(spells_df))
    ax.plot(x_spells, spells_df['dry_mean'], marker='o', linewidth=2, color='#e41a1c', label='Mean Dry Spell (days)')
    ax.plot(x_spells, spells_df['wet_mean'], marker='s', linewidth=2, color='#377eb8', label='Mean Wet Spell (days)')

    ax.set_xlabel('Station ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Spell Length (Days)', fontsize=12, fontweight='bold')
    ax.set_title('Mean Dry and Wet Spell Lengths across Stations', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x_spells)
    ax.set_xticklabels(spells_df['station_id'], rotation=45)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(fig_dir, 'Figure2_Spell_Length_Comparison.png'), dpi=dpi)
    fig.savefig(os.path.join(fig_dir, 'Figure2_Spell_Length_Comparison.pdf'), dpi=dpi)
    plt.close(fig)

    # Figure 3: Sub-period Stability Comparison (1961-1990 vs 1991-2020)
    if stability_df is not None:
        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(stability_df))
        ax.plot(x, stability_df['P1_P01'], marker='o', label='Period 1 (1961-1990) P01', color='#1b9e77', linestyle='--')
        ax.plot(x, stability_df['P2_P01'], marker='s', label='Period 2 (1991-2020) P01', color='#d95f02', linestyle='-')

        ax.set_xlabel('Station ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('P01 (Dry -> Wet Probability)', fontsize=12, fontweight='bold')
        ax.set_title('Temporal Stability of P01 across Sub-Periods', fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(stability_df['station_id'], rotation=45)
        ax.legend(fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        fig.savefig(os.path.join(fig_dir, 'Figure3_Temporal_Stability_P01.png'), dpi=dpi)
        fig.savefig(os.path.join(fig_dir, 'Figure3_Temporal_Stability_P01.pdf'), dpi=dpi)
        plt.close(fig)
