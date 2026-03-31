# DayLog

A desktop app to track daily work hours across multiple contracts/clients. Built with Python and CustomTkinter.

## Features

- **Multi-contract support** — register and manage multiple active contracts
- **Quick time logging** — add +30m, +1h, +2h or correct with -30m per contract
- **Persistent data** — all data saved to `%APPDATA%/DayLog/`, never lost between sessions
- **Daily auto-reset** — counters reset at midnight automatically
- **History view** — collapsible daily entries with full detail
- **Weekly/monthly reports** — aggregated hours per contract, per week, per month
- **Close Month** — snapshot the full monthly cycle with weekly breakdown
- **Single instance lock** — prevents data conflicts from multiple windows
- **Duplicate protection** — prevents adding contracts with the same name

## Getting Started

### Option 1: Run the executable (no install needed)
Download `DayLog.exe` from Releases and run it.

> On first launch, Windows SmartScreen may show a warning. Click "More info" then "Run anyway". This only happens once.

### Option 2: Run from source
```bash
git clone https://github.com/renandemaga/DayLog.git
cd DayLog
pip install -r requirements.txt
python daylog.py
```

### Build the executable yourself
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "DayLog" daylog.py
```

## How It Works

1. Add your contracts on the home screen
2. Select contracts and click **Start Shift**
3. Log hours with **+30m**, **+1h**, **+2h** buttons (use **-30m** to correct)
4. Close the app anytime — hours are saved on every click
5. On Fridays, check the **Report** for weekly totals
6. At month end, click **Close Month** to save the cycle summary

## Data Storage

All data is stored in `%APPDATA%/DayLog/` as JSON files:

- `contracts.json` — list of registered contracts
- `logs.json` — daily hour logs, history events, and closed cycle snapshots

## Tech Stack

- **Python 3.10+**
- **CustomTkinter** — modern dark-themed GUI framework

## License

MIT
