# KelanaAI

KelanaAI is a travel planning application with an integrated AI assistant, built for users in Indonesia.

This repository currently contains the first baseline feature: a Python console-based **Trip Summary Generator**.

## Project Structure

```
kelana-ai/
├── README.md
├── backend/
│   └── main.py        # Console-based Trip Summary Generator (entry point)
└── frontend/
    └── .gitkeep       # Placeholder — frontend coming later
```

## Requirements

- Python 3 (standard library only — no third-party dependencies)

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
```

## Known Limitations

- Numeric prompts (`days`, `budget`) raise `ValueError` on non-numeric input. Retry-loop validation is the planned upgrade path.

## Release

- `v0.1.0` — Initial console-based Trip Summary Generator.
