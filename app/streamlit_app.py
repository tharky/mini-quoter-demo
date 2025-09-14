from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "src")) # Add src to sys.path so streamlit can import packages
import streamlit as st
import pandas as pd
import altair as alt
import uuid
from mini_quoter.locator import find_nearest_station
from mini_quoter.sim import calc_scenario, get_ai_response
from streamlit_cookies_controller import CookieController
from mini_quoter.rate_limit import take, LIMIT, TZ

st.set_page_config(
    page_title="Tiger's Mini Energy Analysis",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="expanded"
)
st.title("⚡ Tiger's Mini Energy Analysis")
st.caption("Annual savings from insulation & HVAC upgrades.")

# Sidebar inputs
st.sidebar.header("Inputs")
zipcode = st.sidebar.text_input("ZIP code", "53715")
sqft = st.sidebar.number_input("Building Size (sqft)", min_value=100.0, value=10000.0, step=100.0, format="%.0f")

st.sidebar.subheader("Utility $$$")
usd_per_kWh = st.sidebar.number_input("Electricity ($/kWh)",  min_value=0.01, value=0.15, step=0.01, format="%.3f")
usd_per_therm = st.sidebar.number_input("Natural Gas ($/therm)", min_value=0.10, value=1.20, step=0.05, format="%.2f")

st.sidebar.subheader("Baseline (current)")
R_baseline = st.sidebar.number_input("R-value (effective)", min_value=0.1, value=10.0, step=1.0)
AFUE_base = st.sidebar.number_input("AFUE (0–1)", min_value=0.3, max_value=1.0, value=0.80, step=0.01, format="%.2f")
SEER_base = st.sidebar.number_input("SEER", min_value=5.0, value=13.0, step=0.5, format="%.1f")

st.sidebar.subheader("Proposed (upgrade)")
R_proposed = st.sidebar.number_input("R-value (upgraded)", min_value=0.1, value=20.0, step=1.0)
AFUE_prop = st.sidebar.number_input("AFUE (0–1, upgraded)", min_value=0.3, max_value=1.0, value=0.95, step=0.01, format="%.2f")
SEER_prop = st.sidebar.number_input("SEER (upgraded)", min_value=5.0, value=18.0, step=0.5, format="%.1f")

# Sets cookies to limit user inputs per day (so my gpt doesn't get overloaded)
c = CookieController()
uid = c.get("mqid")
if not uid:
    uid = uuid.uuid4().hex
    c.set("mqid", uid, max_age=60*60*24*365)  # 1 year
    st.stop() 

compute = st.sidebar.button("Run Simulation")

# Main window
if compute:
    try:
        # Rate limiter
        ok, used, left, reset = take(uid)
        if not ok:
            hrs, mins = divmod(reset // 60, 60)
            st.error(f"Daily prompt limit reached ({LIMIT}/day). resets in {hrs:d}h {mins:d}m")
            st.stop()
        st.caption(f"{used}/{LIMIT} AI requests used today (resets at midnight {TZ})")

        # Get location data from zip code
        loc_data = find_nearest_station(sqft, zipcode, usd_per_therm, usd_per_kWh)
        name, city, state, HDD65, CDD65, station = (
            loc_data["Name"], loc_data["City"], loc_data["State"],
            float(loc_data["HDD65"]), float(loc_data["CDD65"]),
            loc_data["Nearest Station"]
        )

        st.subheader(f"Building Location: {name}")
        st.write(f"HDD65 **{HDD65:,.0f}**  •  CDD65 **{CDD65:,.0f}**  •  Weather Station **{station}**")
        st.markdown(
            f"Climate data from [NOAA]({"https://www.ncei.noaa.gov/"})  climate station closest to input ZIP code **{zipcode}**"
        )

        # run engine (baseline vs proposed)
        baseline = calc_scenario(
            sqft, R_baseline, AFUE_base, SEER_base,
            HDD65, CDD65, usd_per_therm, usd_per_kWh
        )
        proposed = calc_scenario(
            sqft, R_proposed, AFUE_prop, SEER_prop,
            HDD65, CDD65, usd_per_therm, usd_per_kWh
        )

        # Calculate savings
        savings = {
            "therms": baseline["therms"] - proposed["therms"],
            "kWh":    baseline["kWh"]    - proposed["kWh"],
            "cost":   baseline["cost"]   - proposed["cost"],
        }
        heat_pct = (100.0 * (baseline["UA"] - proposed["UA"]) / baseline["UA"]) if baseline["UA"] > 0 else 0.0

        # Comparison table and bar chart
        c1, c2, c3 = st.columns(3)
        c1.metric("Annual cost (baseline)", f"${baseline['cost']:,.0f}")
        c2.metric("Annual cost (proposed)", f"${proposed['cost']:,.0f}")
        c3.metric("Savings / yr", f"${savings['cost']:,.0f}")
        table = pd.DataFrame({
            "therms/yr": [baseline["therms"], proposed["therms"], savings["therms"]],
            "kWh/yr":    [baseline["kWh"],    proposed["kWh"],    savings["kWh"]],
            "$/yr":      [baseline["cost"],   proposed["cost"],   savings["cost"]],
        }, index=["Baseline", "Proposed", "Savings"])
        st.dataframe(
            table.style.format({
                "therms/yr": "{:.0f}",
                "kWh/yr": "{:.0f}",
                "$/yr": "${:,.0f}"
            }),
            width='stretch'
        )
        chart_df = table.loc[["Baseline", "Proposed"], ["$/yr"]].reset_index()
        chart_df.columns = ["scenario", "cost_per_year"]
        chart = alt.Chart(chart_df).mark_bar().encode(
            x=alt.X("scenario:N", sort=None, title=""),
            y=alt.Y("cost_per_year:Q", title="Cost ($/yr)")
        ).properties(height=280)
        st.altair_chart(chart, use_container_width=True)

        
        # Get chatgpt writing about our stats (with nifty loading symbol until we get it)
        placeholder = st.empty()
        with st.spinner("Generating analysis..."):
            explanation = get_ai_response(
                loc_data["Name"], loc_data["HDD65"], loc_data["CDD65"],
                baseline["UA"], baseline["therms"], baseline["kWh"], baseline["cost"],
                proposed["UA"], proposed["therms"], proposed["kWh"], proposed["cost"],
                R_baseline, R_proposed,
                AFUE_base, AFUE_prop,
                SEER_base, SEER_prop,
            )
        placeholder.empty()
        st.markdown(explanation)

        # csv download
        csv = table.to_csv(index=False).encode()
        st.download_button("Download .csv", data=csv, file_name="quoter_results.csv", mime="text/csv")
        st.caption("Please note: this data is a conduction-only model (UA·HDD/CDD). Calculations ignore potential air leakage and HVAC part-loading.\n" +
            "Narrative section automatically generated from simulation results."
        )
    except Exception as e:
        st.error(str(e))
else:
    st.info("Enter building info and click **Run Simulation**.")
