"""
COMPOUNDER ANALYSE - VISUALISIERUNGS-SCRIPT
============================================
Liest direkt aus JSON-Datei ohne Vorverarbeitung
Erstellt alle Visualisierungen und Reports automatisch
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime


class CompoundAnalyzer:
    """Klasse zur Analyse von Compounder-Results aus JSON"""

    def __init__(self, json_path: str):
        """
        Initialisiert den Analyzer mit JSON-Datei

        Args:
            json_path: Pfad zur results JSON-Datei
        """
        self.json_path = json_path
        self.data = self._load_json()
        self.df = self._convert_to_dataframe()

    def _load_json(self) -> Dict:
        """Laden der JSON-Datei"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ JSON geladen: {self.json_path}")
        print(f"✓ {len(data)} Unternehmen geladen\n")
        return data

    def _convert_to_dataframe(self) -> pd.DataFrame:
        """
        Konvertiert JSON direkt zu DataFrame
        Keine externe Vorverarbeitung nötig
        """
        rows = []

        for company_name, results in self.data.items():
            try:
                row = {
                    'Company': company_name,
                    'Symbol': results.get('symbol', 'N/A'),
                    'ROE': results['kennzahlen']['ROE']['wert'],
                    'ROIC': results['kennzahlen']['ROIC']['wert'],
                    'FCF_Margin': results['kennzahlen']['FCF_Margin']['wert'],
                    'Revenue_Growth': results['kennzahlen']['Revenue_Growth']['wert'],
                    'EPS_Growth': results['kennzahlen']['EPS_Growth']['wert'],
                    'Debt_to_Equity': results['kennzahlen']['Debt_to_Equity']['wert'],
                    'Erfuellte_Kriterien': results['gesamtbewertung']['erfuellte_kriterien'],
                    'Erfolgsquote': results['gesamtbewertung']['erfolgsquote'],
                    'Durchschn_Performance': results['gesamtbewertung']['durchschnittliche_performance'],
                    'Rank_Score': results['gesamtbewertung']['rank_score'],
                    'Quality': results['gesamtbewertung']['compounder_qualitaet']
                }
                rows.append(row)
            except KeyError as e:
                print(f"⚠️  Fehler bei {company_name}: {e}")
                continue

        df = pd.DataFrame(rows)
        print(f"✓ DataFrame erstellt: {len(df)} Reihen")
        return df

    def print_statistics(self) -> None:
        """Druckt Gesamt-Statistiken"""
        print("\n" + "=" * 100)
        print("1. GESAMT-STATISTIKEN")
        print("=" * 100 + "\n")

        print(f"Gesamtzahl der Analysen: {len(self.df)}")
        print(f"\nVerteilung nach Kriterien erfüllt:")
        print(self.df['Erfuellte_Kriterien'].value_counts().sort_index(ascending=False))
        print(f"\nVerteilung nach Qualität:")
        print(self.df['Quality'].value_counts().sort_index(ascending=False))

    def print_top_candidates(self, top_n: int = 10) -> None:
        """Druckt Top-N Kandidaten nach Rank_Score"""
        print("\n" + "=" * 100)
        print(f"2. TOP {top_n} KANDIDATEN - NACH RANK_SCORE")
        print("=" * 100 + "\n")

        top = self.df.nlargest(top_n, 'Rank_Score')[
            ['Company', 'Symbol', 'Erfuellte_Kriterien', 'Rank_Score',
             'Durchschn_Performance', 'Quality']
        ]

        for idx, (i, row) in enumerate(top.iterrows(), 1):
            criteria_status = "✅" if row['Erfuellte_Kriterien'] >= 4 else "⚠️" if row[
                                                                                      'Erfuellte_Kriterien'] >= 3 else "❌"
            print(f"{idx:2d}. {criteria_status} {row['Company'][:40]:40s} ({row['Symbol']:10s}) | "
                  f"Kriterien: {row['Erfuellte_Kriterien']}/6 | Score: {row['Rank_Score']:.3f} | "
                  f"{row['Quality']}")

    def print_grouped_by_criteria(self) -> None:
        """Druckt Kandidaten gruppiert nach erfüllten Kriterien"""
        print("\n" + "=" * 100)
        print("3. KANDIDATEN NACH KRITERIEN-GRUPPEN")
        print("=" * 100)

        for criteria_count in sorted(self.df['Erfuellte_Kriterien'].unique(), reverse=True):
            group = self.df[self.df['Erfuellte_Kriterien'] == criteria_count].sort_values(
                'Rank_Score', ascending=False
            )

            emoji = {6: "🟢", 5: "🟡", 4: "🟠", 3: "🟠", 2: "🔴", 1: "🔴", 0: "⚫"}
            print(
                f"\n{emoji.get(criteria_count, '⚪')} {criteria_count}/6 Kriterien erfüllt ({len(group)} Unternehmen):")

            for idx, (i, row) in enumerate(group.iterrows(), 1):
                if idx <= 5:  # Zeige Top 5 pro Gruppe
                    print(f"   {idx}. {row['Company'][:45]:45s} | Score: {row['Rank_Score']:.3f} | "
                          f"Performance: {row['Durchschn_Performance']:.2%}")

            if len(group) > 5:
                print(f"   ... und {len(group) - 5} weitere")

    def print_detailed_top5(self) -> None:
        """Druckt detaillierte Kennzahlen für Top 5"""
        print("\n" + "=" * 100)
        print("4. DETAILLIERTE KENNZAHLEN - TOP 5 INVESTITIONEN")
        print("=" * 100)

        top_5 = self.df.nlargest(5, 'Rank_Score')

        for idx, (i, row) in enumerate(top_5.iterrows(), 1):
            status = "✅ KAUFEN" if row['Erfuellte_Kriterien'] >= 4 else "⚠️ PRÜFEN"
            print(f"\n{idx}. {row['Company']} ({row['Symbol']}) - {status}")
            print(
                f"   Rank-Score: {row['Rank_Score']:.3f} | Durchschn. Performance: {row['Durchschn_Performance']:.2%}")
            print(f"   Erfüllte Kriterien: {row['Erfuellte_Kriterien']}/6 | Qualität: {row['Quality']}")
            print(f"   ├─ ROE: {row['ROE']:7.2%} | ROIC: {row['ROIC']:7.2%} | FCF-Marge: {row['FCF_Margin']:7.2%}")
            print(f"   ├─ Revenue-Growth: {row['Revenue_Growth']:7.2%} | EPS-Growth: {row['EPS_Growth']:7.2%}")
            print(f"   └─ Debt/Equity: {row['Debt_to_Equity']:7.2f}")

    def print_problem_analysis(self) -> None:
        """Druckt Analyse der häufigsten Probleme"""
        print("\n" + "=" * 100)
        print("5. HÄUFIGSTE PROBLEME (Kriterien NICHT erfüllt)")
        print("=" * 100 + "\n")

        criteria_analysis = [
            ('ROE (Min 15%)', self.df['ROE'] < 0.15),
            ('ROIC (Min 16%)', self.df['ROIC'] < 0.16),
            ('FCF-Margin (Min 10%)', self.df['FCF_Margin'] < 0.10),
            ('Revenue-Growth (Min 8%)', self.df['Revenue_Growth'] < 0.08),
            ('EPS-Growth (Min 10%)', self.df['EPS_Growth'] < 0.10),
            ('Debt/Equity (Max 0.8)', self.df['Debt_to_Equity'] > 0.8),
        ]

        problems = [(name, mask.sum()) for name, mask in criteria_analysis]
        problems_sorted = sorted(problems, key=lambda x: x[1], reverse=True)

        for criterion, count in problems_sorted:
            pct = count / len(self.df) * 100
            print(f"  ❌ {criterion:30s}: {count:2d}/{len(self.df)} ({pct:5.1f}%) nicht erfüllt")

    def print_recommendations(self) -> None:
        """Druckt Investitions-Empfehlungen"""
        print("\n" + "=" * 100)
        print("6. EMPFEHLUNGEN")
        print("=" * 100 + "\n")

        # Kategorisierung
        buy = self.df[self.df['Erfuellte_Kriterien'] >= 4].nlargest(5, 'Rank_Score')
        consider = self.df[(self.df['Erfuellte_Kriterien'] == 3)].nlargest(5, 'Rank_Score')
        filter_out = self.df[self.df['Erfuellte_Kriterien'] < 2]

        print("🟢 KAUFEN (≥ 4 Kriterien erfüllt):")
        if len(buy) > 0:
            for idx, (i, row) in enumerate(buy.iterrows(), 1):
                print(f"  {idx}. {row['Company'][:40]:40s} ({row['Symbol']:10s}) - Score: {row['Rank_Score']:.3f}")
        else:
            print("  (Keine Kandidaten)")

        print("\n🟡 PRÜFEN (3 Kriterien + hohe Performance):")
        if len(consider) > 0:
            for idx, (i, row) in enumerate(consider.iterrows(), 1):
                if idx <= 5:
                    print(
                        f"  {idx}. {row['Company'][:40]:40s} ({row['Symbol']:10s}) - Score: {row['Rank_Score']:.3f}, Performance: {row['Durchschn_Performance']:.2%}")
        else:
            print("  (Keine Kandidaten)")

        print(f"\n🔴 AUSFILTERN (< 2 Kriterien):")
        if len(filter_out) > 0:
            names = ", ".join(filter_out['Company'].head(5).tolist())
            remaining = len(filter_out) - 5
            if remaining > 0:
                print(f"  {names}, ... und {remaining} weitere")
            else:
                print(f"  {names}")

        print(f"\n📊 GESAMT-STATISTIK:")
        print(f"  • Qualifizierte Kandidaten (≥ 4/6): {len(self.df[self.df['Erfuellte_Kriterien'] >= 4])}")
        print(f"  • Moderate Kandidaten (3/6): {len(self.df[self.df['Erfuellte_Kriterien'] == 3])}")
        print(f"  • Zu filtern (< 3/6): {len(self.df[self.df['Erfuellte_Kriterien'] < 3])}")

    def get_charts_data(self) -> Dict:
        """
        Gibt Daten für Chart-Generierung zurück
        (zur Verwendung mit create_chart tool)
        """
        top_12 = self.df.nlargest(12, 'Rank_Score')

        return {
            'top_12': {
                'companies': top_12['Company'].tolist(),
                'scores': top_12['Rank_Score'].tolist(),
                'criteria': top_12['Erfuellte_Kriterien'].tolist(),
                'quality': top_12['Quality'].tolist(),
            },
            'criteria_dist': {
                'labels': ['4+ Kriterien', '3 Kriterien', '2 Kriterien', '1 Kriterium', '0 Kriterien'],
                'values': [
                    len(self.df[self.df['Erfuellte_Kriterien'] >= 4]),
                    len(self.df[self.df['Erfuellte_Kriterien'] == 3]),
                    len(self.df[self.df['Erfuellte_Kriterien'] == 2]),
                    len(self.df[self.df['Erfuellte_Kriterien'] == 1]),
                    len(self.df[self.df['Erfuellte_Kriterien'] == 0]),
                ]
            },
            'heatmap_top10': {
                'companies': self.df.nlargest(10, 'Rank_Score')['Company'].tolist(),
                'metrics': {
                    'ROE': self.df.nlargest(10, 'Rank_Score')['ROE'].apply(lambda x: f"{x:.1%}").tolist(),
                    'ROIC': self.df.nlargest(10, 'Rank_Score')['ROIC'].apply(lambda x: f"{x:.1%}").tolist(),
                    'FCF_Margin': self.df.nlargest(10, 'Rank_Score')['FCF_Margin'].apply(lambda x: f"{x:.1%}").tolist(),
                    'Revenue_Growth': self.df.nlargest(10, 'Rank_Score')['Revenue_Growth'].apply(
                        lambda x: f"{x:.1%}").tolist(),
                    'EPS_Growth': self.df.nlargest(10, 'Rank_Score')['EPS_Growth'].apply(lambda x: f"{x:.1%}").tolist(),
                    'Debt_to_Equity': self.df.nlargest(10, 'Rank_Score')['Debt_to_Equity'].apply(
                        lambda x: f"{x:.2f}").tolist(),
                }
            },
            'scatter': {
                'companies': self.df['Company'].tolist(),
                'scores': self.df['Rank_Score'].tolist(),
                'criteria': self.df['Erfuellte_Kriterien'].tolist(),
                'quality': self.df['Quality'].tolist(),
            }
        }

    def print_full_report(self) -> None:
        """Druckt vollständigen Report"""
        self.print_statistics()
        self.print_top_candidates(10)
        self.print_grouped_by_criteria()
        self.print_detailed_top5()
        self.print_problem_analysis()
        self.print_recommendations()

        print("\n" + "=" * 100)
        print("✅ REPORT VOLLSTÄNDIG")
        print("=" * 100 + "\n")

    def export_to_csv(self, output_path: str = None) -> str:
        """Exportiert DataFrame zu CSV"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"compounder_analysis_{timestamp}.csv"

        self.df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ CSV exportiert: {output_path}")
        return output_path

    def export_top_n_json(self, n: int = 15, output_path: str = None) -> str:
        """Exportiert Top-N als neue JSON"""
        if output_path is None:
            output_path = f"top_{n}_compounders.json"

        top_n = self.df.nlargest(n, 'Rank_Score')
        export_data = top_n.to_dict('records')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Top-{n} JSON exportiert: {output_path}")
        return output_path


def main():
    """Hauptfunktion"""

    # EINZIGE KONFIGURATION ERFORDERLICH:
    json_file = "../compounder_analysis/results_20251112_162918.json"  # <- Ändere hier den Dateinamen

    print("=" * 100)
    print("COMPOUNDER ANALYSE - VISUALISIERUNGS-SYSTEM")
    print("=" * 100 + "\n")

    try:
        # Initialisiere Analyzer mit JSON-Datei
        analyzer = CompoundAnalyzer(json_file)

        # Drucke vollständigen Report
        analyzer.print_full_report()

        # Optional: Exportiere Ergebnisse
        # csv_path = analyzer.export_to_csv()
        # json_path = analyzer.export_top_n_json(15)

        # Erhalte Chart-Daten für weitere Verarbeitung
        chart_data = analyzer.get_charts_data()
        print(f"✓ Chart-Daten verfügbar: {len(chart_data)} Datensätze\n")

    except FileNotFoundError:
        print(f"❌ Fehler: Datei '{json_file}' nicht gefunden!")
        print("   Stelle sicher, dass die JSON-Datei im selben Verzeichnis liegt.")
    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
