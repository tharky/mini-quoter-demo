# Building Energy Upgrade Analyzer

### [Live Demo](https://mini-quoter-demo.streamlit.app/)


A Streamlit demo that estimates annual heating and cooling energy costs for an existing building and a proposed upgrade using NOAA climate normals.

## Features

- Maps a U.S. ZIP code to the nearest NOAA climate station.
- Compares existing vs. proposed insulation, AFUE, and SEER values.
- Estimates annual natural-gas use, electricity use, cost, and savings.
- Generates a short OpenAI-powered project summary.
- Limits public AI usage to 3 successful summaries per device per day.

## Model

The calculator uses a simplified conduction model based on effective R-value, building area, HDD65, and CDD65. It is intended for comparative estimates rather than full building-load analysis.

The model does not include infiltration, solar gains, internal loads, humidity, or HVAC part-load behavior.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add an OpenAI API key:

```toml
OPENAI_API_KEY = "sk-..."
```

Then run:

```powershell
streamlit run app/streamlit_app.py
```

`.streamlit/secrets.toml` is ignored by Git and should never be committed.

## Data

NOAA 1991–2020 HDD65/CDD65 climate normals are bundled with the package.
