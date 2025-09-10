# mini-quoter - Energy Analysis Streamlit App

---

# Features
- **ZIP to nearest weather station** (geocode + haversine algorithm)
- **Baseline vs Proposed** inputs with energy and price comparisons
- **AI Analysis of saved energy** if proper OpenAI API key is given


## Requirements
- Python 3.10+

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
streamlit run app/streamlit_app.py

### Data
Included: data/noaa_hdd_cdd_allstations.csv (public-domain NOAA normals, 1991–2020).

## Tests
Install dev tools and run tests:

```bash
python -m pip install -U pip
pip install -e .
pip install pytest pytest-cov
pytest -q