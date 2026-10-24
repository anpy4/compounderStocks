import yfinance as yf
from curl_cffi import requests
from typing import Dict, Any, Optional
import statistics
from src.metrics.roe import ROECalculator
from src.metrics.roic import ROICCalculator
from src.metrics.fcf import FCFMarginCalculator
from src.metrics.revenue_growth import RevenueGrowthCalculator
from src.metrics.eps_growth import EpsGrowthCalculator
from src.metrics.debt_to_equity import DebtToEquityCalculator
from src.thresholds import SCHWELLENWERTE



def _normalize_for_ranking(kennzahl: str, wert: Optional[float]) -> float:
    """
    Normalisiert Kennzahlen für Ranking auf 0-1 Skala.
    Höhere Werte = bessere Performance

    Debt_Equity ist INVERS (niedriger = besser)
    """
    if wert is None:
        return 0.0

    # Für Debt/Equity: Invers, da niedriger besser ist
    if kennzahl == 'Debt_to_Equity':
        # Normalisiere: 0.0 → 1.0, 0.5 → 2/3, 1.5 → 0.0
        return max(0.0, min(1.0, (1.5 - wert) / 1.5))

    # Andere Kennzahlen: Höher = besser
    # Begrenzte normalisierung (Cap bei realistische Maxima)
    max_values = {
        'ROE': 0.60,  # 60% ist ein extremes Maximum
        'ROIC': 0.60,
        'FCF_Margin': 0.50,  # 50% FCF-Margin ist sehr hoch
        'Revenue_Growth': 0.50,  # 50% Revenue-Growth ist extrem
        'EPS_Growth': 0.50,
    }

    max_val = max_values.get(kennzahl, 1.0)
    return min(1.0, wert / max_val)


def _calculate_average_performance(results: Dict[str, Any]) -> float:
    """
    Berechnet durchschnittliche Performance für Ranking innerhalb einer Kategorie.
    Gibt Wert zwischen 0.0-1.0 zurück.

    Nur erfüllte Kriterien werden berücksichtigt!
    """
    performances = []

    # Nur Werte von erfüllten Kriterien
    for kriterium, erfuellt in results['erfuellt_kriterien'].items():
        if erfuellt:  # Nur wenn Kriterium erfüllt
            # Extrahiere kennzahl-Name aus kriterium
            # z.B. "ROE_min" → "ROE"
            kennzahl_key = kriterium.replace('_min', '').replace('_ok', '')
            if kennzahl_key == 'Debt_Equity':
                kennzahl_key = 'Debt_to_Equity'

            if kennzahl_key in results['kennzahlen']:
                wert = results['kennzahlen'][kennzahl_key]['wert']
                if wert is not None:
                    normalized = _normalize_for_ranking(kennzahl_key, wert)
                    performances.append(normalized)

    if performances:
        return statistics.mean(performances)
    else:
        return 0.0


def _analyze_compounder(ticker) -> Dict[str, Any]:
    """
    Führt eine umfassende Compounder-Analyse durch

    Args:
        ticker: yfinance.Ticker Objekt (oder Mock)

    Returns:
        Dict mit allen Kennzahlen und Gesamtbewertung
    """
    results = {
        'symbol': getattr(ticker, 'ticker', 'Unknown'),
        'kennzahlen': {},
        'erfuellt_kriterien': {},
        'gesamtbewertung': {}
    }

    # Alle Kennzahlen berechnen
    roe_value, roe_bewertung = ROECalculator().calculate(ticker)
    roic_value, roic_bewertung = ROICCalculator().calculate(ticker)
    fcf_margin_value, fcf_margin_bewertung = FCFMarginCalculator().calculate(ticker)
    revenue_growth_value, revenue_growth_bewertung = RevenueGrowthCalculator().calculate(ticker)
    eps_growth_value, eps_growth_bewertung = EpsGrowthCalculator().calculate(ticker)
    debt_equity_value, debt_equity_bewertung = DebtToEquityCalculator().calculate(ticker)

    # Ergebnisse sammeln
    results['kennzahlen'] = {
        'ROE': {'wert': roe_value, 'bewertung': roe_bewertung},
        'ROIC': {'wert': roic_value, 'bewertung': roic_bewertung},
        'FCF_Margin': {'wert': fcf_margin_value, 'bewertung': fcf_margin_bewertung},
        'Revenue_Growth': {'wert': revenue_growth_value, 'bewertung': revenue_growth_bewertung},
        'EPS_Growth': {'wert': eps_growth_value, 'bewertung': eps_growth_bewertung},
        'Debt_to_Equity': {'wert': debt_equity_value, 'bewertung': debt_equity_bewertung}
    }

    # Prüfe welche Kriterien erfüllt sind (MIT ERHÖHTEN SCHWELLENWERTEN!)
    results['erfuellt_kriterien'] = {
        'ROE_min': roe_value is not None and roe_value >= SCHWELLENWERTE['ROE_min'],
        'ROIC_min': roic_value is not None and roic_value >= SCHWELLENWERTE['ROIC_min'],
        'FCF_Margin_min': fcf_margin_value is not None and fcf_margin_value >= SCHWELLENWERTE['FCF_Marge_min'],
        'Revenue_Growth_min': revenue_growth_value is not None and revenue_growth_value >= SCHWELLENWERTE[
            'Umsatzwachstum_min'],
        'EPS_Growth_min': eps_growth_value is not None and eps_growth_value >= SCHWELLENWERTE['EPS_Wachstum_min'],
        'Debt_Equity_ok': debt_equity_value is not None and debt_equity_value <= SCHWELLENWERTE['Debt_Equity_max']
    }

    # Gesamtbewertung
    erfuellte_kriterien = sum(results['erfuellt_kriterien'].values())
    gesamtkriterien = len(results['erfuellt_kriterien'])

    # Berechne durchschnittliche Performance für Ranking
    avg_performance = _calculate_average_performance(results)

    results['gesamtbewertung'] = {
        'erfuellte_kriterien': erfuellte_kriterien,
        'gesamtkriterien': gesamtkriterien,
        'erfolgsquote': erfuellte_kriterien / gesamtkriterien if gesamtkriterien > 0 else 0,
        'compounder_qualitaet': _get_compounder_qualitaet(erfuellte_kriterien, gesamtkriterien),
        'durchschnittliche_performance': avg_performance,  # NEU!
        'rank_score': _calculate_rank_score(erfuellte_kriterien, avg_performance)  # NEU!
    }

    return results


def _get_compounder_qualitaet(erfuellt: int, gesamt: int) -> str:
    """Bewertet die Gesamtqualität als Compounder"""
    if erfuellt == gesamt:
        return "Exzellenter Compounder"
    elif erfuellt >= gesamt * 0.8:
        return "Starker Compounder"
    elif erfuellt >= gesamt * 0.6:
        return "Guter Compounder"
    elif erfuellt >= gesamt * 0.4:
        return "Moderater Compounder"
    else:
        return "Schwacher Compounder"


def _calculate_rank_score(erfuellte: int, avg_performance: float) -> float:
    """
    Berechnet einen einfachen Rank-Score für Sortierung.

    Gewichtung:
    - 70% auf Kriterien-Erfüllung (6/6 = max)
    - 30% auf durchschnittliche Performance
    """
    criteria_score = (erfuellte / 6.0) * 0.70
    performance_score = avg_performance * 0.30

    return criteria_score + performance_score


def _print_analysis_results(results: Dict[str, Any]) -> None:
    """Druckt die Analyseergebnisse in formatierter Form"""
    print(f"=== COMPOUNDER-ANALYSE FÜR {results['symbol']} ===")
    print()

    print("KENNZAHLEN:")
    for kennzahl, data in results['kennzahlen'].items():
        wert = data['wert']
        bewertung = data['bewertung']
        if wert is not None:
            if kennzahl in ['ROE', 'ROIC', 'FCF_Margin', 'Revenue_Growth', 'EPS_Growth']:
                print(f"  {kennzahl}: {wert:.2%} ({bewertung})")
            else:
                print(f"  {kennzahl}: {wert:.2f} ({bewertung})")
        else:
            print(f"  {kennzahl}: N/A ({bewertung})")

    print()
    print("ERFÜLLTE KRITERIEN:")
    for kriterium, erfuellt in results['erfuellt_kriterien'].items():
        status = "✓" if erfuellt else "✗"
        print(f"  {status} {kriterium}: {erfuellt}")

    print()
    print("GESAMTBEWERTUNG:")
    gb = results['gesamtbewertung']
    print(f"  Erfüllte Kriterien: {gb['erfuellte_kriterien']} von {gb['gesamtkriterien']}")
    print(f"  Erfolgsquote: {gb['erfolgsquote']:.1%}")
    print(f"  Durchschnittliche Performance: {gb['durchschnittliche_performance']:.2%}")
    print(f"  Rank-Score: {gb['rank_score']:.3f}")
    print(f"  Qualität: {gb['compounder_qualitaet']}")
    print()


def _analyze_one(ticker_symbol: str, print_results: bool = True):
    """Analysiert einzelne Aktie"""
    with requests.Session(impersonate="chrome") as session:
        session.verify = False
        ticker = yf.Ticker(ticker_symbol, session=session)

        result = _analyze_compounder(ticker)

        if print_results:
            _print_analysis_results(result)

        return result


def analyze_batch(ticker_symbols: Dict[str, str]):
    """
    Analysiert Batch von Aktien mit NEUEM Ranking-System
    """
    results = {}

    for name, symbol in ticker_symbols.items():
        print(f"Analysiere {name}...")
        results[name] = _analyze_one(symbol, print_results=False)

    # NEUES RANKING: Erst nach Kriterien, dann nach Performance innerhalb Kategorie
    sorted_results = _sort_results_by_criteria_and_performance(results)

    return sorted_results


def _sort_results_by_criteria_and_performance(results: Dict) -> Dict:
    """
    Sortiert Results hierarchisch:
    1. Nach erfüllte_kriterien (6/6 > 5/6 > 4/6 > ...)
    2. Innerhalb Kategorie: Nach durchschnittlicher Performance

    NEUER ANSATZ: Bessere Differenzierung ohne Composite Score
    """
    # Gruppiere nach Kriterien
    grouped = {}
    for name, data in results.items():
        criteria_count = data['gesamtbewertung']['erfuellte_kriterien']
        if criteria_count not in grouped:
            grouped[criteria_count] = []
        grouped[criteria_count].append((name, data))

    # Sortiere jede Gruppe nach Performance
    sorted_results = {}
    for criteria_count in sorted(grouped.keys(), reverse=True):
        group = grouped[criteria_count]
        # Sortiere nach Performance (descending)
        sorted_group = sorted(
            group,
            key=lambda x: x[1]['gesamtbewertung']['durchschnittliche_performance'],
            reverse=True
        )

        for name, data in sorted_group:
            sorted_results[name] = data

    return sorted_results


if __name__ == "__main__":
    # Einzelanalyse
    #_analyze_one("DBK.F")

    # Batch-Analyse
    tickers = {'adidas AG': 'ADS.F', 'Allianz SE': 'ALV.F', 'BASF SE': 'BAS.F', 'Bayer AG': 'BAYN.F', 'Beiersdorf AG': 'BEI.F', 'Bayerische Motoren Werke AG': 'BMW.F', 'Continental AG': 'CON.F', 'Covestro AG': '1COV.F', 'Deutsche Bank AG': 'DBK.F', 'Deutsche BÃ¶rse AG': 'DB1.F', 'Deutsche Post AG': 'DPW.F', 'Deutsche Telekom AG': 'DTE.F', 'E.ON SE': 'EOAN.F', 'Fresenius Medical Care AG & Co. KGaA St': 'FME.F', 'Fresenius SE & Co. KGaA': 'FRE.F', 'HeidelbergCement AG': 'HEI.F', 'Henkel AG & Co. KGaA Vz': 'HEN3.F', 'Infineon Technologies AG': 'IFX.F', 'Linde PLC': 'LIN.F', 'MERCK Kommanditgesellschaft auf Aktien': 'MRK.F', 'MÃ¼nchener RÃ¼ckversicherungs-Gesellschaft AG': 'MUV2.F', 'RWE AG': 'RWE.F', 'SAP SE': 'SAP.F', 'Siemens AG': 'SIE.F', 'Volkswagen AG': 'VOW3.F', 'Vonovia SE': 'VNA.F', 'Airbus SE': 'AIR.F', 'Brenntag AG': 'BNR.F', 'Hannover RÃ¼ck SE': 'HNR1.F', 'MTU Aero Engines AG': 'MTX.F', 'PUMA SE': 'PUM.F', 'QIAGEN N.V.': 'QIA.F', 'Sartorius AG': 'SRT3.F', 'Siemens Healthineers AG': 'SHL.F', 'Symrise AG': 'SY1.F', 'Zalando SE': 'ZAL.F', 'Siemens Energy AG': 'ENR.F', 'Porsche Automobil Holding SE': 'PAH3.F', 'Daimler Truck Holding AG': 'DTG.F', 'Mercedes-Benz Group AG': 'MBG.F'}


    res = analyze_batch(tickers)
    print(res)