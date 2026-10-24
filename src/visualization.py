"""
CHART-GENERIERUNGS-MODULE FÜR COMPOUNDER ANALYZER
=================================================
Ergänzung für visualize_results.py
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import re
from datetime import datetime
from pathlib import Path
from typing import cast

from evaluate_statistics import CompoundAnalyzer


class ChartGenerator:
    """Generiert alle Visualisierungen aus den Analyzer-Daten"""

    def __init__(self, analyzer):
        """
        Initialisiert Chart-Generator mit Analyzer-Instanz

        Args:
            analyzer: CompoundAnalyzer Instanz
        """
        self.analyzer = analyzer
        self.df = analyzer.df
        self.output_dir = Path("../charts")
        self.output_dir.mkdir(exist_ok=True)

        # Matplotlib Einstellungen
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")

    def _get_quality_colors(self, quality: str) -> str:
        """Gibt Farbe basierend auf Qualität zurück"""
        color_map = {
            'Exzellenter Compounder': '#2ecc71',  # Grün
            'Guter Compounder': '#3498db',  # Blau
            'Moderater Compounder': '#f39c12',  # Orange
            'Schwacher Compounder': '#e74c3c',  # Rot
        }
        return color_map.get(quality, '#95a5a6')  # Grau Fallback

    # ========================================================================
    # CHART 1: SCATTER - Rank-Score vs. Erfüllte Kriterien
    # ========================================================================

    def create_scatter_score_vs_criteria(self) -> str:
        """
        Erstellt Scatter Plot: Rank-Score vs. Erfüllte Kriterien
        """
        fig, ax = plt.subplots(figsize=(12, 8))

        # Gruppiere nach Qualität für Färbung
        for quality in self.df['Quality'].unique():
            subset = self.df[self.df['Quality'] == quality]
            color = self._get_quality_colors(quality)
            ax.scatter(
                subset['Rank_Score'],
                subset['Erfuellte_Kriterien'],
                s=150,
                alpha=0.7,
                label=quality,
                color=color,
                edgecolors='black',
                linewidth=0.5
            )

        # Labels für Top 15
        top_15 = self.df.nlargest(15, 'Rank_Score')
        for idx, row in top_15.iterrows():
            ax.annotate(
                row['Symbol'],
                (row['Rank_Score'], row['Erfuellte_Kriterien']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8,
                alpha=0.8
            )

        # Formatierung
        ax.set_xlabel('Rank-Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('Erfüllte Kriterien (von 6)', fontsize=12, fontweight='bold')
        ax.set_title('Rank-Score vs. Erfüllte Kriterien - Alle 40 Unternehmen',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(-0.05, 0.6)
        ax.set_ylim(-0.5, 4.5)

        # Reference Line bei 4 Kriterien (Investment-Threshold)
        ax.axhline(y=3.5, color='red', linestyle='--', linewidth=2, alpha=0.5,
                   label='Investment Threshold (4 Kriterien)')

        # Grid
        ax.grid(True, alpha=0.3)
        ax.legend(loc='lower right', fontsize=10)

        # Speichere
        filename = self.output_dir / "01_scatter_score_vs_criteria.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 1 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # CHART 2: BAR - Durchschnittlicher Score pro Kriterien-Gruppe
    # ========================================================================

    def create_bar_avg_score_by_criteria(self) -> str:
        """
        Erstellt Bar Chart: Durchschnittlicher Score pro Kriterien-Gruppe
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Berechne durchschnittliche Scores pro Gruppe
        criteria_groups = sorted(self.df['Erfuellte_Kriterien'].unique(), reverse=True)
        avg_scores = []
        counts = []
        colors = []
        labels = []

        color_map = {4: '#2ecc71', 3: '#f39c12', 2: '#e67e22', 1: '#e74c3c', 0: '#95a5a6'}

        for criteria in criteria_groups:
            group = self.df[self.df['Erfuellte_Kriterien'] == criteria]
            avg_scores.append(group['Rank_Score'].mean())
            counts.append(len(group))
            colors.append(color_map.get(cast(int, criteria), '#95a5a6'))
            labels.append(f"{criteria}/6 Kriterien")

        # Bar Chart
        bars = ax.barh(labels, avg_scores, color=colors, edgecolor='black', linewidth=1.5)

        # Wert-Labels auf Bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height() / 2,
                    f'{width:.3f}\n(n={count})',
                    ha='left', va='center', fontweight='bold', fontsize=10)

        # Formatierung
        ax.set_xlabel('Durchschnittlicher Rank-Score', fontsize=12, fontweight='bold')
        ax.set_title('Durchschnittlicher Rank-Score pro Kriterien-Gruppe',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(0, 0.6)
        ax.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        filename = self.output_dir / "02_bar_avg_score_by_criteria.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 2 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # CHART 3: BOX - Score-Verteilung pro Kriterien-Gruppe
    # ========================================================================

    def create_boxplot_score_distribution(self) -> str:
        """
        Erstellt Box Plot: Score-Verteilung pro Kriterien-Gruppe
        """
        fig, ax = plt.subplots(figsize=(12, 7))

        # Daten vorbereiten
        criteria_order = sorted(self.df['Erfuellte_Kriterien'].unique())
        criteria_labels = [f"{c}/6" for c in criteria_order]

        data_to_plot = [self.df[self.df['Erfuellte_Kriterien'] == c]['Rank_Score'].values
                        for c in criteria_order]

        # Box Plot
        bp = ax.boxplot(data_to_plot, tick_labels=criteria_labels, patch_artist=True,
                        notch=True, showmeans=True)

        # Färbe Boxes
        color_map = {0: '#95a5a6', 1: '#e74c3c', 2: '#e67e22', 3: '#f39c12', 4: '#2ecc71'}
        for patch, criteria in zip(bp['boxes'], criteria_order):
            patch.set_facecolor(color_map.get(cast(int, criteria), '#95a5a6'))
            patch.set_alpha(0.7)

        # Formatierung
        ax.set_xlabel('Erfüllte Kriterien', fontsize=12, fontweight='bold')
        ax.set_ylabel('Rank-Score', fontsize=12, fontweight='bold')
        ax.set_title('Rank-Score Verteilung pro Kriterien-Gruppe',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        filename = self.output_dir / "03_boxplot_score_distribution.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 3 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # CHART 4: HISTOGRAM - Score-Verteilung
    # ========================================================================

    def create_histogram_score_distribution(self) -> str:
        """
        Erstellt Histogram: Verteilung der Rank-Scores
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Histogram mit gestapeltem Kriterien-Filter
        criteria_order = sorted(self.df['Erfuellte_Kriterien'].unique(), reverse=True)
        color_map = {4: '#2ecc71', 3: '#f39c12', 2: '#e67e22', 1: '#e74c3c', 0: '#95a5a6'}

        bottom = np.zeros(20)  # 20 Bins

        for criteria in criteria_order:
            subset = self.df[self.df['Erfuellte_Kriterien'] == criteria]
            counts, bins = np.histogram(subset['Rank_Score'], bins=20, range=(0, 0.6))

            ax.bar(bins[:-1], counts, width=np.diff(bins),
                   label=f"{criteria}/6 Kriterien",
                   color=color_map.get(cast(int, criteria), '#95a5a6'),
                   alpha=0.7, edgecolor='black', linewidth=0.5)

        # Formatierung
        ax.set_xlabel('Rank-Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('Anzahl Unternehmen', fontsize=12, fontweight='bold')
        ax.set_title('Score-Verteilung - Gestapelt nach Kriterien',
                     fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        filename = self.output_dir / "04_histogram_score_distribution.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 4 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # CHART 5: BUBBLE - Score vs. Kriterien mit Performance
    # ========================================================================

    def create_bubble_score_performance(self) -> str:
        """
        Erstellt Bubble Chart: Score, Kriterien, Performance
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Bubble Chart
        for quality in self.df['Quality'].unique():
            subset = self.df[self.df['Quality'] == quality]
            color = self._get_quality_colors(quality)

            scatter = ax.scatter(
                subset['Rank_Score'],
                subset['Erfuellte_Kriterien'],
                s=subset['Durchschn_Performance'] * 1000,  # Größe = Performance
                alpha=0.6,
                label=quality,
                color=color,
                edgecolors='black',
                linewidth=1
            )

        # Labels für Top 10
        top_10 = self.df.nlargest(10, 'Rank_Score')
        for idx, row in top_10.iterrows():
            ax.annotate(
                row['Symbol'],
                (row['Rank_Score'], row['Erfuellte_Kriterien']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9,
                fontweight='bold',
                alpha=0.9
            )

        # Formatierung
        ax.set_xlabel('Rank-Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('Erfüllte Kriterien', fontsize=12, fontweight='bold')
        ax.set_title('Bubble Chart: Score, Kriterien & Performance',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlim(-0.05, 0.6)
        ax.set_ylim(-0.5, 4.5)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='lower right', fontsize=10)

        # Performance-Legende
        sizes = [0.3, 0.6, 1.0]
        labels = ['30%', '60%', '100%']
        legend_bubbles = [ax.scatter([], [], s=s * 1000, c='gray', alpha=0.6,
                                     edgecolors='black', linewidth=1)
                          for s in sizes]

        first_legend = ax.legend(loc='lower right', fontsize=10, title='Qualität')
        ax.add_artist(first_legend)

        second_legend = ax.legend(legend_bubbles, labels,
                                  scatterpoints=1, title='Performance',
                                  loc='upper left', fontsize=9, framealpha=0.9)

        plt.tight_layout()
        filename = self.output_dir / "05_bubble_score_performance.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 5 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # CHART 6: HEATMAP - Kriterien erfüllt/nicht erfüllt
    # ========================================================================

    def create_heatmap_criteria_fulfillment(self, top_n: int = 15) -> str:
        """
        Erstellt Heatmap: Welche Kriterien erfüllt sind
        """
        # Hole Roh-Daten
        top_companies = self.analyzer.df.nlargest(top_n, 'Rank_Score')

        # Erstelle Matrix aus erfuellte_kriterien
        heatmap_data = []
        companies: list[str] = []

        for idx, row in top_companies.iterrows():
            companies.append(row['Symbol'])
            # Berechne erfüllte Kriterien
            roe_ok = 1 if row['ROE'] >= 0.15 else 0
            roic_ok = 1 if row['ROIC'] >= 0.16 else 0
            fcf_ok = 1 if row['FCF_Margin'] >= 0.10 else 0
            rev_ok = 1 if row['Revenue_Growth'] >= 0.08 else 0
            eps_ok = 1 if row['EPS_Growth'] >= 0.10 else 0
            de_ok = 1 if row['Debt_to_Equity'] <= 0.8 else 0

            heatmap_data.append([roe_ok, roic_ok, fcf_ok, rev_ok, eps_ok, de_ok])

        # Erstelle DataFrame für Heatmap
        criterion_columns: list[str] = [
            'ROE\n(≥15%)', 'ROIC\n(≥16%)', 'FCF-M\n(≥10%)',
            'RevG\n(≥8%)', 'EPSG\n(≥10%)', 'D/E\n(≤0.8)'
        ]
        heatmap_df = pd.DataFrame(
            heatmap_data,
            index=pd.Index(companies),
            columns=pd.Index(criterion_columns)
        )

        # Erstelle Heatmap
        fig, ax = plt.subplots(figsize=(10, top_n * 0.4))

        sns.heatmap(heatmap_df, annot=True, fmt='d', cmap='RdYlGn',
                    cbar_kws={'label': 'Erfüllt (1) / Nicht erfüllt (0)'},
                    linewidths=1, linecolor='black', ax=ax,
                    vmin=0, vmax=1, square=False, cbar=True)

        ax.set_title(f'Kriterien Erfüllung - Top {top_n} Unternehmen',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Kriterien', fontsize=11, fontweight='bold')
        ax.set_ylabel('Unternehmen', fontsize=11, fontweight='bold')

        plt.tight_layout()
        filename = self.output_dir / "06_heatmap_criteria_fulfillment.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Chart 6 erstellt: {filename}")
        return str(filename)

    # ========================================================================
    # HAUPTMETHODE: Alle Charts generieren
    # ========================================================================

    def generate_all_charts(self) -> dict:
        """Generiert alle Charts und gibt Dateinamen zurück"""
        print("\n" + "=" * 100)
        print("ERSTELLE ALLE VISUALISIERUNGEN")
        print("=" * 100 + "\n")

        charts = {
            'scatter_score_vs_criteria': self.create_scatter_score_vs_criteria(),
            'bar_avg_score': self.create_bar_avg_score_by_criteria(),
            'boxplot_distribution': self.create_boxplot_score_distribution(),
            'histogram_distribution': self.create_histogram_score_distribution(),
            'bubble_performance': self.create_bubble_score_performance(),
            'heatmap_criteria': self.create_heatmap_criteria_fulfillment(),
        }

        print(f"\n✓ Alle Charts im Ordner '{self.output_dir}' gespeichert")
        return charts


def find_latest_results_file() -> Path:
    """Findet die neueste Datei im Schema results_YYYYMMDD_HHMMSS.json."""
    results_dir = Path(__file__).resolve().parents[1] / "compounder_analysis"
    filename_pattern = re.compile(r"^results_(\d{8}_\d{6})\.json$")
    matching_files = []

    for path in results_dir.glob("results_*.json"):
        match = filename_pattern.fullmatch(path.name)
        if match:
            timestamp = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            matching_files.append((timestamp, path))

    if not matching_files:
        raise FileNotFoundError(
            f"Keine Ergebnisdatei im Format results_YYYYMMDD_HHMMSS.json "
            f"gefunden in: {results_dir}"
        )

    return max(matching_files, key=lambda item: item[0])[1]


def main():

    # Analyzer starten
    results_file = find_latest_results_file()
    print(f"Verwende Ergebnisdatei: {results_file}")
    analyzer = CompoundAnalyzer(str(results_file))

    # Chart-Generator initialisieren
    chart_gen = ChartGenerator(analyzer)

    # Alle Charts generieren
    charts = chart_gen.generate_all_charts()

    # Oder einzelne Charts:
    # chart_gen.create_scatter_score_vs_criteria()
    # chart_gen.create_bubble_score_performance()

if __name__ == "__main__":
    main()
