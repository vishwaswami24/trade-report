from __future__ import annotations


SECTOR_PROFILES: dict[str, dict[str, list[str]]] = {
    "pharmaceuticals": {
        "watchlist": ["Sun Pharma", "Dr. Reddy's", "Cipla", "Divi's Laboratories"],
        "drivers": [
            "USFDA approvals, remediation progress, and export order wins",
            "Domestic branded prescription growth and chronic therapy demand",
            "Currency moves affecting export-heavy margins",
        ],
        "risks": [
            "Compliance setbacks or import alerts from regulators",
            "Pricing pressure in export markets",
            "Raw material cost spikes for intermediates and APIs",
        ],
    },
    "technology": {
        "watchlist": ["TCS", "Infosys", "HCLTech", "Tech Mahindra"],
        "drivers": [
            "Global IT spending guidance and deal conversion velocity",
            "AI adoption budgets and cloud modernization demand",
            "Rupee movement against the US dollar",
        ],
        "risks": [
            "Client budget delays in the US and Europe",
            "Wage inflation and margin pressure",
            "Weak discretionary spending in enterprise tech",
        ],
    },
    "agriculture": {
        "watchlist": ["UPL", "PI Industries", "Coromandel International", "Kaveri Seed"],
        "drivers": [
            "Monsoon progress and sowing acreage trends",
            "Fertilizer, agrochemical, and seed demand across key states",
            "Government procurement and rural income support measures",
        ],
        "risks": [
            "Erratic rainfall and crop damage",
            "Policy changes impacting subsidies or procurement",
            "Commodity price swings and inventory stress",
        ],
    },
    "banking": {
        "watchlist": ["HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank"],
        "drivers": [
            "Credit growth, deposit traction, and NIM stability",
            "RBI policy stance and system liquidity",
            "Asset quality trends in retail and SME books",
        ],
        "risks": [
            "Deposit cost pressure",
            "Higher slippages in unsecured or SME lending",
            "Unexpected policy tightening",
        ],
    },
    "energy": {
        "watchlist": ["Reliance Industries", "ONGC", "NTPC", "Power Grid"],
        "drivers": [
            "Crude price direction and refining spreads",
            "Power demand growth and capacity additions",
            "Government push for transition, transmission, and renewables",
        ],
        "risks": [
            "Commodity volatility",
            "Tariff or subsidy changes",
            "Execution delays in large capex projects",
        ],
    },
}


def get_sector_profile(sector: str) -> dict[str, list[str]]:
    normalized = sector.lower().strip()
    if normalized in SECTOR_PROFILES:
        return SECTOR_PROFILES[normalized]

    title = sector.title()
    return {
        "watchlist": [
            f"Large-cap {title} leaders",
            f"Mid-cap {title} challengers",
            f"Supply-chain beneficiaries in {title}",
        ],
        "drivers": [
            f"Domestic demand and pricing trends in {title}",
            f"Government policy, regulation, and incentive changes affecting {title}",
            f"Export momentum, currency moves, and input-cost behavior in {title}",
        ],
        "risks": [
            f"Execution and margin pressure across {title} companies",
            f"Regulatory or tax changes affecting {title}",
            f"Market-wide risk-off sentiment reducing flows into {title}",
        ],
    }
