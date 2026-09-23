from pathlib import Path
import sys
import uuid

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "src"))

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

from mini_quoter.locator import find_nearest_station
from mini_quoter.rate_limit import LIMIT, TZ, check
from mini_quoter.sim import calc_scenario, get_ai_response


st.set_page_config(
    page_title="Building Energy Upgrade Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Building Energy Upgrade Analyzer")
st.caption(
    "Compare existing and proposed building-envelope and HVAC performance "
    "using location-specific NOAA climate normals."
)


# Persistent browser ID used only for the daily public-demo AI limit.
cookies = CookieController()
uid = cookies.get("mqid")

if not uid:
    uid = uuid.uuid4().hex
    cookies.set("mqid", uid, max_age=60 * 60 * 24 * 365)
    st.stop()


# Inputs are grouped in a form so edits do not rerun the analysis until submit.
with st.sidebar.form("simulation_inputs"):
    st.header("Building Parameters")

    zipcode = st.text_input("ZIP code", "53715")

    sqft = st.number_input(
        "Building size (sq ft)",
        min_value=100.0,
        value=10000.0,
        step=100.0,
        format="%.0f",
    )

    st.subheader("Utility Rates")

    usd_per_kWh = st.number_input(
        "Electricity ($/kWh)",
        min_value=0.01,
        value=0.15,
        step=0.01,
        format="%.3f",
    )

    usd_per_therm = st.number_input(
        "Natural gas ($/therm)",
        min_value=0.10,
        value=1.20,
        step=0.05,
        format="%.2f",
    )

    st.divider()
    st.subheader("Existing Conditions")

    R_baseline = st.number_input(
        "Effective R-value",
        min_value=0.1,
        value=10.0,
        step=1.0,
    )

    AFUE_base = st.number_input(
        "AFUE",
        min_value=0.3,
        max_value=1.0,
        value=0.80,
        step=0.01,
        format="%.2f",
    )

    SEER_base = st.number_input(
        "SEER",
        min_value=5.0,
        value=13.0,
        step=0.5,
        format="%.1f",
    )

    st.divider()
    st.subheader("Proposed Upgrade")

    R_proposed = st.number_input(
        "Effective R-value",
        min_value=0.1,
        value=20.0,
        step=1.0,
        key="proposed_r",
    )

    AFUE_prop = st.number_input(
        "AFUE",
        min_value=0.3,
        max_value=1.0,
        value=0.95,
        step=0.01,
        format="%.2f",
        key="proposed_afue",
    )

    SEER_prop = st.number_input(
        "SEER",
        min_value=5.0,
        value=18.0,
        step=0.5,
        format="%.1f",
        key="proposed_seer",
    )

    compute = st.form_submit_button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
    )


if not compute:
    st.info(
        "Configure the building and proposed upgrade in the sidebar, "
        "then select **Run Analysis**."
    )
    st.stop()


# Run the calculation engine. These results remain available even if the
# public-demo AI quota is exhausted or the summary service is unavailable.
try:
    loc_data = find_nearest_station(
        sqft,
        zipcode,
        usd_per_therm,
        usd_per_kWh,
    )

    name = loc_data["Name"]
    HDD65 = float(loc_data["HDD65"])
    CDD65 = float(loc_data["CDD65"])
    station = loc_data["Nearest Station"]

    baseline = calc_scenario(
        sqft,
        R_baseline,
        AFUE_base,
        SEER_base,
        HDD65,
        CDD65,
        usd_per_therm,
        usd_per_kWh,
    )

    proposed = calc_scenario(
        sqft,
        R_proposed,
        AFUE_prop,
        SEER_prop,
        HDD65,
        CDD65,
        usd_per_therm,
        usd_per_kWh,
    )
except Exception as exc:
    st.error(f"Unable to run the analysis: {exc}")
    st.stop()


savings = {
    "therms": baseline["therms"] - proposed["therms"],
    "kWh": baseline["kWh"] - proposed["kWh"],
    "cost": baseline["cost"] - proposed["cost"],
}

cost_reduction_pct = (
    100 * savings["cost"] / baseline["cost"]
    if baseline["cost"] > 0
    else 0
)


# Climate basis.
st.caption("CLIMATE BASIS")
st.write(f"**{name}** · ZIP {zipcode}")
st.caption(
    f"NOAA station: {station}  |  "
    f"HDD65: {HDD65:,.0f}  |  "
    f"CDD65: {CDD65:,.0f}"
)


# Headline results.
st.subheader("Annual Cost Comparison")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Estimated Savings", f"${savings['cost']:,.0f}/yr")
m2.metric("Existing", f"${baseline['cost']:,.0f}/yr")
m3.metric("Proposed", f"${proposed['cost']:,.0f}/yr")
m4.metric("Reduction", f"{cost_reduction_pct:.1f}%")

st.divider()


# Cost chart and energy-use table.
chart_col, table_col = st.columns([1.3, 1])

with chart_col:
    st.subheader("Estimated Annual Cost")

    chart_df = pd.DataFrame(
        {
            "Scenario": ["Existing", "Proposed"],
            "Annual Cost": [baseline["cost"], proposed["cost"]],
        }
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar(size=70)
        .encode(
            x=alt.X("Scenario:N", sort=None, title=None),
            y=alt.Y("Annual Cost:Q", title="Annual cost ($/yr)"),
            tooltip=[
                "Scenario:N",
                alt.Tooltip(
                    "Annual Cost:Q",
                    title="Annual Cost",
                    format="$,.0f",
                ),
            ],
        )
    )

    labels = (
        alt.Chart(chart_df)
        .mark_text(dy=-10, fontSize=14)
        .encode(
            x=alt.X("Scenario:N", sort=None),
            y="Annual Cost:Q",
            text=alt.Text("Annual Cost:Q", format="$,.0f"),
        )
    )

    chart = (bars + labels).properties(height=320)
    st.altair_chart(chart, use_container_width=True)

with table_col:
    st.subheader("Energy Use")

    table = pd.DataFrame(
        {
            "Existing": [
                baseline["therms"],
                baseline["kWh"],
                baseline["cost"],
            ],
            "Proposed": [
                proposed["therms"],
                proposed["kWh"],
                proposed["cost"],
            ],
            "Savings": [
                savings["therms"],
                savings["kWh"],
                savings["cost"],
            ],
        },
        index=[
            "Natural Gas (therms/yr)",
            "Electricity (kWh/yr)",
            "Energy Cost ($/yr)",
        ],
    )

    st.dataframe(
        table.style.format("{:,.0f}"),
        width="stretch",
        hide_index=False,
    )


# Generated summary. Quota is checked first but only consumed after a
# successful OpenAI response, so failed requests do not burn a daily use.
st.divider()
st.subheader("Generated Project Summary")

allowed, used, _, reset = take(uid)

if not allowed:
    hrs, mins = divmod(reset // 60, 60)
    st.info(
        f"Daily generated-summary limit reached ({LIMIT}/day). "
        f"The calculator remains available. Resets in {hrs:d}h {mins:d}m."
    )
else:
    try:
        with st.spinner("Generating project summary..."):
            explanation = get_ai_response(
                loc_data["Name"],
                loc_data["HDD65"],
                loc_data["CDD65"],
                baseline["UA"],
                baseline["therms"],
                baseline["kWh"],
                baseline["cost"],
                proposed["UA"],
                proposed["therms"],
                proposed["kWh"],
                proposed["cost"],
                R_baseline,
                R_proposed,
                AFUE_base,
                AFUE_prop,
                SEER_base,
                SEER_prop,
            )

        st.markdown(explanation)

    except Exception as exc:
        print(f"Generated summary failed: {exc}")
        st.warning(
            "The calculation completed, but the generated summary is "
            "temporarily unavailable."
        )

st.divider()
st.caption(
    f"{used}/{LIMIT} AI summaries used today · "
    f"Resets at midnight {TZ}"
)

with st.expander("Methodology"):
    st.markdown(
        """
        **Climate:** NOAA HDD65 and CDD65 normals from the station nearest
        the entered ZIP code.

        **Model:** Annual conductive heating and cooling loads are estimated
        from building area, effective R-value, AFUE, and SEER.

        **Scope:** This simplified model excludes infiltration, solar gains,
        internal loads, humidity, and HVAC part-load effects.
        """
    )
