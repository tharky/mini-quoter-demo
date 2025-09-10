import math
import pytest
from mini_quoter.sim import calc_scenario, get_ai_response
from mini_quoter.locator import find_nearest_station

# Give inputs, verify correct math
def test_calc_scenario():
    # basic inputs
    test = calc_scenario(
        sqft=10000, R_value=10, AFUE=0.80, SEER=13,
        HDD65=6000, CDD65=1200,
        usd_per_therm=1.20, usd_per_kWh=0.12,
    )
    # UA = 10000/10 = 1000
    assert test["UA"] == pytest.approx(1000)
    # Degree-hours
    assert test["HDD_hours"] == 6000 * 24
    assert test["CDD_hours"] == 1200 * 24
    # Therms ≈ 1.8e3, kWh ≈ 2215.38, cost ≈ 2425.85
    assert test["therms"] == pytest.approx(1800, rel=1e-3)
    assert test["kWh"] == pytest.approx(2_215.38, rel=1e-3)
    assert test["cost"] == pytest.approx(2425.85, rel=1e-3)

# Give two zipcodes, verify correct city, state, and station
def test_locator():
    test = find_nearest_station(
        sqft=1000, zipcode="53529", usd_per_therm=1.0, usd_per_kwh=0.1
    )
    assert test["City"] == "Dane"
    assert test["State"] == "WI"
    assert "lodi" in test["Nearest Station"].lower()
    test = find_nearest_station(
        sqft=1000, zipcode="10562", usd_per_therm=1.0, usd_per_kwh=0.1
    )
    assert test["City"] == "Ossining"
    assert test["State"] == "NY"
    assert "yorktown hts 1w" in test["Nearest Station"].lower()