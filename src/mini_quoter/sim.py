import os

import streamlit as st
from openai import OpenAI

THERM_BTU = 100_000.0
WH_PER_KWH = 1_000.0


def calc_scenario(
    sqft,
    R_value,
    AFUE,
    SEER,
    HDD65,
    CDD65,
    usd_per_therm,
    usd_per_kWh,
):
    HDD_hours = HDD65 * 24.0
    CDD_hours = CDD65 * 24.0

    UA = sqft / R_value
    Q_heat_BTU = UA * HDD_hours
    Q_cool_BTU = UA * CDD_hours

    therms = (Q_heat_BTU / AFUE) / THERM_BTU
    kWh = (Q_cool_BTU / SEER) / WH_PER_KWH
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


def _get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment or Streamlit Secrets.

    Checking the environment first keeps local development working even when
    no .streamlit/secrets.toml file exists.
    """
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    return value or default


def get_ai_response(
    location_name: str,
    HDD65: float,
    CDD65: float,
    UA_base: float,
    therms_base: float,
    kwh_base: float,
    cost_base: float,
    UA_prop: float,
    therms_prop: float,
    kwh_prop: float,
    cost_prop: float,
    R_base: float,
    R_prop: float,
    AFUE_base: float,
    AFUE_prop: float,
    SEER_base: float,
    SEER_prop: float,
) -> str:
    therms_saved = therms_base - therms_prop
    kwh_saved = kwh_base - kwh_prop
    usd_saved = cost_base - cost_prop
    reduction_percent = (
        100.0 * (UA_base - UA_prop) / UA_base if UA_base > 0 else 0.0
    )

    api_key = _get_setting("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Add it to Streamlit Secrets, "
            ".streamlit/secrets.toml, or the OPENAI_API_KEY environment variable."
        )

    client = OpenAI(api_key=api_key)

    system_msg = (
        "You are an energy analyst. Write a concise, neutral summary for a proposal. "
        "Do not use 'we', 'our', or 'your'. Use plain language in 3 or 4 sentences. "
        "Use only the provided data; do not invent or project values."
    )

    user_msg = (
        "Write one short project-summary paragraph:\n"
        f"- Location and climate: {location_name} "
        f"(HDD65={HDD65:.0f}, CDD65={CDD65:.0f}).\n"
        f"- Insulation: R-value improved from R-{R_base:g} to R-{R_prop:g}.\n"
        f"- UA change: {UA_base:.0f} -> {UA_prop:.0f}; "
        f"conductive-load reduction {reduction_percent:.0f}%.\n"
        f"- Annual savings: ~{therms_saved:.0f} therms, "
        f"~{kwh_saved:.0f} kWh, ~${usd_saved:.0f}.\n"
        f"- Efficiency: AFUE {AFUE_base:g} -> {AFUE_prop:g}, "
        f"SEER {SEER_base:g} -> {SEER_prop:g}."
    )

    response = client.chat.completions.create(
        model=_get_setting("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.25,
        max_tokens=220,
    )

    return response.choices[0].message.content.strip()
