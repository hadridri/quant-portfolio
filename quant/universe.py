"""Tickers offered in the app and scanned by the daily alert job.

Any other Yahoo Finance symbol can still be typed in the app; this list only
feeds the suggestions and the golden cross scanner.
"""

US = {
    "AAPL": "Apple", "ABBV": "AbbVie", "ABT": "Abbott", "ACN": "Accenture", "ADBE": "Adobe",
    "AIG": "AIG", "AMD": "AMD", "AMGN": "Amgen", "AMT": "American Tower", "AMZN": "Amazon",
    "AVGO": "Broadcom", "AXP": "American Express", "BA": "Boeing", "BAC": "Bank of America",
    "BKNG": "Booking", "BLK": "BlackRock", "BMY": "Bristol-Myers",
    "BRK-B": "Berkshire Hathaway", "C": "Citigroup", "CAT": "Caterpillar", "CL": "Colgate-Palmolive",
    "CMCSA": "Comcast", "COF": "Capital One", "COP": "ConocoPhillips", "COST": "Costco",
    "CRM": "Salesforce", "CSCO": "Cisco", "CVS": "CVS Health", "CVX": "Chevron", "DE": "Deere",
    "DHR": "Danaher", "DIS": "Disney", "DUK": "Duke Energy", "EMR": "Emerson", "F": "Ford",
    "FDX": "FedEx", "GD": "General Dynamics", "GE": "GE Aerospace", "GILD": "Gilead",
    "GM": "General Motors", "GOOGL": "Alphabet", "GS": "Goldman Sachs", "HD": "Home Depot",
    "HON": "Honeywell", "IBM": "IBM", "INTC": "Intel", "INTU": "Intuit", "ISRG": "Intuitive Surgical",
    "JNJ": "Johnson & Johnson", "JPM": "JPMorgan", "KO": "Coca-Cola", "LIN": "Linde", "LLY": "Eli Lilly",
    "LMT": "Lockheed Martin", "LOW": "Lowe's", "MA": "Mastercard", "MCD": "McDonald's",
    "MDLZ": "Mondelez", "MDT": "Medtronic", "MET": "MetLife", "META": "Meta", "MMM": "3M",
    "MO": "Altria", "MRK": "Merck", "MS": "Morgan Stanley", "MSFT": "Microsoft", "MU": "Micron",
    "NEE": "NextEra Energy", "NFLX": "Netflix", "NKE": "Nike", "NOW": "ServiceNow", "NVDA": "Nvidia",
    "ORCL": "Oracle", "PEP": "PepsiCo", "PFE": "Pfizer", "PG": "Procter & Gamble", "PLTR": "Palantir",
    "PM": "Philip Morris", "PYPL": "PayPal", "QCOM": "Qualcomm", "RTX": "RTX", "SBUX": "Starbucks",
    "SCHW": "Charles Schwab", "SO": "Southern Co", "SPG": "Simon Property", "T": "AT&T",
    "TGT": "Target", "TMO": "Thermo Fisher", "TMUS": "T-Mobile", "TSLA": "Tesla", "TSM": "TSMC",
    "TXN": "Texas Instruments", "UBER": "Uber", "UNH": "UnitedHealth", "UNP": "Union Pacific",
    "UPS": "UPS", "USB": "US Bancorp", "V": "Visa", "VZ": "Verizon", "WFC": "Wells Fargo",
    "WMT": "Walmart", "XOM": "ExxonMobil",
}

FRANCE = {
    "AC.PA": "Accor", "ACA.PA": "Crédit Agricole", "AI.PA": "Air Liquide", "AIR.PA": "Airbus",
    "BN.PA": "Danone", "BNP.PA": "BNP Paribas", "CA.PA": "Carrefour", "CAP.PA": "Capgemini",
    "CS.PA": "AXA", "DG.PA": "Vinci", "DSY.PA": "Dassault Systèmes", "EL.PA": "EssilorLuxottica",
    "EN.PA": "Bouygues", "ENGI.PA": "Engie", "ERF.PA": "Eurofins", "GLE.PA": "Société Générale",
    "HO.PA": "Thales", "KER.PA": "Kering", "LR.PA": "Legrand", "MC.PA": "LVMH", "ML.PA": "Michelin",
    "MT.AS": "ArcelorMittal", "OR.PA": "L'Oréal", "ORA.PA": "Orange", "PUB.PA": "Publicis",
    "RI.PA": "Pernod Ricard", "RMS.PA": "Hermès", "RNO.PA": "Renault", "SAF.PA": "Safran",
    "SAN.PA": "Sanofi", "SGO.PA": "Saint-Gobain", "STLAP.PA": "Stellantis", "STMPA.PA": "STMicroelectronics",
    "SU.PA": "Schneider Electric", "TEP.PA": "Teleperformance", "TTE.PA": "TotalEnergies",
    "URW.PA": "Unibail-Rodamco", "VIE.PA": "Veolia", "VIV.PA": "Vivendi",
}

FRANCE_MORE = {
    "AF.PA": "Air France-KLM", "AKE.PA": "Arkema", "ALO.PA": "Alstom", "AM.PA": "Dassault Aviation",
    "AMUN.PA": "Amundi", "BOL.PA": "Bolloré", "BVI.PA": "Bureau Veritas", "COFA.PA": "Coface",
    "EDEN.PA": "Edenred", "ENX.PA": "Euronext", "ERA.PA": "Eramet", "EXENS.PA": "Exosens",
    "FGR.PA": "Eiffage", "FR.PA": "Valeo", "FRVIA.PA": "Forvia", "GET.PA": "Getlink", "IPN.PA": "Ipsen",
    "NEX.PA": "Nexans", "RXL.PA": "Rexel", "SCR.PA": "SCOR", "SOI.PA": "Soitec", "SPIE.PA": "SPIE",
    "SW.PA": "Sodexo", "UBI.PA": "Ubisoft", "VK.PA": "Vallourec",
}

# EU / EEA companies: eligible for the French PEA
EUROPE_PEA = {
    "ADS.DE": "Adidas", "AIR.DE": "Airbus (Xetra)", "ALV.DE": "Allianz", "BAS.DE": "BASF", "BAYN.DE": "Bayer",
    "BEI.DE": "Beiersdorf", "BMW.DE": "BMW", "CON.DE": "Continental", "DB1.DE": "Deutsche Börse",
    "DBK.DE": "Deutsche Bank", "DHL.DE": "DHL Group", "DTE.DE": "Deutsche Telekom", "ENR.DE": "Siemens Energy",
    "EOAN.DE": "E.ON", "HEN3.DE": "Henkel", "HNR1.DE": "Hannover Re", "IFX.DE": "Infineon",
    "MBG.DE": "Mercedes-Benz", "MUV2.DE": "Munich Re", "RHM.DE": "Rheinmetall", "RWE.DE": "RWE",
    "SAP.DE": "SAP", "SIE.DE": "Siemens", "VOW3.DE": "Volkswagen", "ZAL.DE": "Zalando",
    "AD.AS": "Ahold Delhaize", "ADYEN.AS": "Adyen", "ASM.AS": "ASM International", "ASML.AS": "ASML",
    "BESI.AS": "BE Semiconductor", "HEIA.AS": "Heineken", "INGA.AS": "ING", "PHIA.AS": "Philips",
    "PRX.AS": "Prosus", "UMG.AS": "Universal Music", "WKL.AS": "Wolters Kluwer",
    "ABI.BR": "AB InBev", "KBC.BR": "KBC", "UCB.BR": "UCB",
    "BBVA.MC": "BBVA", "CABK.MC": "CaixaBank", "IBE.MC": "Iberdrola", "ITX.MC": "Inditex",
    "REP.MC": "Repsol", "SAN.MC": "Santander", "TEF.MC": "Telefónica",
    "ENEL.MI": "Enel", "ENI.MI": "Eni", "G.MI": "Generali", "ISP.MI": "Intesa Sanpaolo",
    "LDO.MI": "Leonardo", "MONC.MI": "Moncler", "PRY.MI": "Prysmian", "RACE.MI": "Ferrari",
    "STLAM.MI": "Stellantis (Milan)", "UCG.MI": "UniCredit",
    "RYA.IR": "Ryanair",
    "KNEBV.HE": "Kone", "NDA-FI.HE": "Nordea", "NOKIA.HE": "Nokia", "SAMPO.HE": "Sampo",
    "DSV.CO": "DSV", "MAERSK-B.CO": "Maersk", "NOVO-B.CO": "Novo Nordisk", "VWS.CO": "Vestas",
    "ATCO-A.ST": "Atlas Copco", "ERIC-B.ST": "Ericsson", "INVE-B.ST": "Investor AB",
    "SAND.ST": "Sandvik", "VOLV-B.ST": "Volvo",
    "DNB.OL": "DNB", "EQNR.OL": "Equinor",
}

# UK and Switzerland: not PEA-eligible
EUROPE = {
    "AZN.L": "AstraZeneca", "BP.L": "BP", "HSBA.L": "HSBC", "NESN.SW": "Nestlé", "NOVN.SW": "Novartis",
    "SHEL.L": "Shell", "ULVR.L": "Unilever",
}

ETF = {
    "SPY": "S&P 500 ETF", "IVV": "iShares S&P 500", "QQQ": "Nasdaq 100 ETF", "DIA": "Dow Jones ETF",
    "IWM": "Russell 2000 ETF", "VTI": "US Total Market", "EFA": "Developed ex-US", "EEM": "Emerging Markets",
    "EWA": "Australia", "EWC": "Canada", "EWG": "Germany", "EWJ": "Japan", "EWQ": "France", "EWU": "UK",
    "EWZ": "Brazil", "FXI": "China", "INDA": "India", "CW8.PA": "Amundi MSCI World",
    "TLT": "US Treasuries 20y+", "IEF": "US Treasuries 7-10y", "SHY": "US Treasuries 1-3y",
    "LQD": "Investment Grade Bonds", "HYG": "High Yield Bonds", "TIP": "Inflation-Linked Bonds",
    "GLD": "Gold", "SLV": "Silver", "GDX": "Gold Miners", "USO": "Oil", "DBC": "Commodities",
    "VNQ": "US Real Estate", "XLB": "Materials", "XLC": "Communication", "XLE": "Energy", "XLF": "Financials",
    "XLI": "Industrials", "XLK": "Technology", "XLP": "Consumer Staples", "XLU": "Utilities",
    "XLV": "Health Care", "XLY": "Consumer Discretionary", "SMH": "Semiconductors",
}

INDEX = {
    "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones", "^RUT": "Russell 2000",
    "^FCHI": "CAC 40", "^GDAXI": "DAX", "^STOXX50E": "Euro Stoxx 50", "^FTSE": "FTSE 100", "^N225": "Nikkei 225",
}

CRYPTO = {"BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana"}

GROUPS = {"US stocks": US, "France": FRANCE, "France mid caps": FRANCE_MORE,
          "Europe (PEA)": EUROPE_PEA, "Europe (UK, CH)": EUROPE, "ETFs": ETF, "Indices": INDEX, "Crypto": CRYPTO}
NAMES = {t: n for group in GROUPS.values() for t, n in group.items()}
UNIVERSE = list(NAMES)
# Shares of EU/EEA companies plus the PEA-eligible World ETF
PEA = {*FRANCE, *FRANCE_MORE, *EUROPE_PEA, "CW8.PA"}


def label(ticker: str) -> str:
    name = NAMES.get(ticker)
    return f"{ticker} · {name}" if name else ticker
