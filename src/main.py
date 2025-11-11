from src.analysis import analyze_batch
import json


def main():
    tickers = {'adidas AG': 'ADS.F', 'Allianz SE': 'ALV.F', 'BASF SE': 'BAS.F', 'Bayer AG': 'BAYN.F',
               'Beiersdorf AG': 'BEI.F', 'Bayerische Motoren Werke AG': 'BMW.F', 'Continental AG': 'CON.F',
               'Covestro AG': '1COV.F', 'Deutsche Bank AG': 'DBK.F', 'Deutsche BÃ¶rse AG': 'DB1.F',
               'Deutsche Post AG': 'DPW.F', 'Deutsche Telekom AG': 'DTE.F', 'E.ON SE': 'EOAN.F',
               'Fresenius Medical Care AG & Co. KGaA St': 'FME.F', 'Fresenius SE & Co. KGaA': 'FRE.F',
               'HeidelbergCement AG': 'HEI.F', 'Henkel AG & Co. KGaA Vz': 'HEN3.F', 'Infineon Technologies AG': 'IFX.F',
               'Linde PLC': 'LIN.F', 'MERCK Kommanditgesellschaft auf Aktien': 'MRK.F',
               'MÃ¼nchener RÃ¼ckversicherungs-Gesellschaft AG': 'MUV2.F', 'RWE AG': 'RWE.F', 'SAP SE': 'SAP.F',
               'Siemens AG': 'SIE.F', 'Volkswagen AG': 'VOW3.F', 'Vonovia SE': 'VNA.F', 'Airbus SE': 'AIR.F',
               'Brenntag AG': 'BNR.F', 'Hannover RÃ¼ck SE': 'HNR1.F', 'MTU Aero Engines AG': 'MTX.F',
               'PUMA SE': 'PUM.F', 'QIAGEN N.V.': 'QIA.F', 'Sartorius AG': 'SRT3.F', 'Siemens Healthineers AG': 'SHL.F',
               'Symrise AG': 'SY1.F', 'Zalando SE': 'ZAL.F', 'Siemens Energy AG': 'ENR.F',
               'Porsche Automobil Holding SE': 'PAH3.F', 'Daimler Truck Holding AG': 'DTG.F',
               'Mercedes-Benz Group AG': 'MBG.F'}
    sorted_results = analyze_batch(tickers)
    _store_results_to_json(sorted_results, "../compounder_analysis/results.json")


def _store_results_to_json(results, filename):
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":

    import os
    x = os.getcwd()

    main()