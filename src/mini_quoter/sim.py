import os
import streamlit as st
from openai import OpenAI

# Constants
THERM_BTU  = 100_000.0  # 1 therm = 100,000 BTU
WH_PER_KWH = 1_000.0    # 1 kWh = 1,000 Wh

def calc_scenario(sqft, R_value, AFUE, SEER, HDD65, CDD65, usd_per_therm, usd_per_kWh):
    # Convert degree days to degree hours
    HDD_hours = HDD65 * 24.0
    CDD_hours = CDD65 * 24.0

    # Calculate UA (total conductance) by dividing area by heat resistance (r value)
    UA = sqft / R_value

    # Calculate seasonal heating load BTU's (unit of energy) from UA and climate data
    Q_heat_BTU = UA * HDD_hours
    Q_cool_BTU = UA * CDD_hours

    # Calculate therms of fuel (therm is a unit of natural gas) from BTU's
    therms = (Q_heat_BTU / AFUE) / THERM_BTU

    # Calculate kWh (electricity) from BTU's
    kWh = (Q_cool_BTU / SEER) / WH_PER_KWH

    # Calculate cost from therms/kwh required and prices for each
    cost = therms * usd_per_therm + kWh * usd_per_kWh

    return {
        "UA": UA,
        "HDD_hours": HDD_hours,
        "CDD_hours": CDD_hours,
        "Q_heat_BTU": Q_heat_BTU,
        "Q_cool_BTU": Q_cool_BTU,
        "therms": therms,
        "kWh": kWh,
        "cost": cost,
    }

def get_ai_response(
    location_name: str,
    HDD65: float,
    CDD65: float,
    UA_base: float, therms_base: float, kwh_base: float, cost_base: float,
    UA_prop: float, therms_prop: float, kwh_prop: float, cost_prop: float,
    R_base: float, R_prop: float,
    AFUE_base: float, AFUE_prop: float,
    SEER_base: float, SEER_prop: float,
) -> str:

    # Calculate savings
    therms_saved = therms_base - therms_prop
    kwh_saved    = kwh_base    - kwh_prop
    usd_saved    = cost_base   - cost_prop
    reduction_percent = (100.0 * (UA_base - UA_prop) / UA_base) if UA_base > 0 else 0.0

    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in Streamlit Secrets (or env var).")
    client = OpenAI(api_key=api_key)

    # Create the prompt to analyze data without making anything new up.
    system_msg = (
        "You are an energy analyst. Write a concise, neutral summary for a proposal. "
        "Do not use 'we', 'our', or 'your'. Plain language. 3 or 4 sentences. "
        "Use only the provided data; do not invent or project values."
    )
    user_msg = (
        "Write the 'Narrative' as one paragraph:\n"
        f"- Location and climate: {location_name} (HDD65={HDD65:.0f}, CDD65={CDD65:.0f}).\n"
        f"- Insulation: R-value improved from R-{R_base:g} to R-{R_prop:g}.\n"
        f"- UA change: {UA_base:.0f} → {UA_prop:.0f}; heating demand reduction {reduction_percent:.0f}%.\n"
        f"- Annual savings: ~{therms_saved:.0f} therms, ~{kwh_saved:.0f} kWh, ~${usd_saved:.0f}.\n"
        f"- Efficiency references: AFUE {AFUE_base:g} → {AFUE_prop:g}, SEER {SEER_base:g} → {SEER_prop:g}."
    )

    # Prompt 4o
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system_msg},
                  {"role": "user", "content": user_msg}],
        temperature=0.25,
        max_tokens=220,
    )
    # Pick the first answer choice, messages, content, remove surrounding whitespace, and return it
    return resp.choices[0].message.content.strip()