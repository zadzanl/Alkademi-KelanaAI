# KelanaAI

KelanaAI is a travel planning application with an integrated AI assistant, built for users in Indonesia.

This repository currently contains a Python console-based **Trip Summary Generator** with deterministic budget and travel recommendations.

## Project Structure

```
kelana-ai/
├── README.md
├── backend/
│   ├── main.py                 # Console entry point and presentation
│   └── services/
│       └── trip_service.py     # Daily budget and recommendation rules
├── tests/
│   └── test_trip_service.py    # Standard-library regression checks
└── frontend/
    └── .gitkeep       # Placeholder, frontend coming later
```

## Requirements

- Python 3 (Standard library only. No third-party dependencies)

## Running the App

```bash
python backend/main.py
```

The app interactively prompts for:

- `destination` (string)
- `country` (string)
- `days` (integer)
- `budget` (float)
- `currency` (string)
- `travel_month` (string)

It then prints a formatted trip summary, for example:

```
========================
KelanaAI
========================

Destination: Japan
Country: Japan
Days: 5
Budget: 1500.0 USD
Currency: USD
Travel Month: December
Category:             Standard
Daily Budget:         300.0 USD/Day
Recommended Places:
- Tokyo Tower
- Shibuya
- Mount Fuji
Recommended Transportation: Train
```

Run the regression checks from the repository root:

```bash
python -m unittest discover -s tests -v
```

## Known Limitations

- Numeric prompts (`days`, `budget`) raise `ValueError` on non-numeric input. Retry-loop validation is the planned upgrade path.
- A trip duration of zero raises `ZeroDivisionError`; positive-day validation is a future change.
- Category thresholds are applied directly to the entered numeric budget without currency conversion. Currency normalization is a future requirement.
- Place recommendations are the static lesson dataset and are not destination-aware.

## Release

- `v0.1.0` — Initial console-based Trip Summary Generator.
