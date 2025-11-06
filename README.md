# wosrewards batch redeemer (safe automation)

This small tool automates applying gift codes on https://wosrewards.com/ using Selenium.

Important:
- This script does NOT bypass captchas (the target site presently doesn't require one).
- Respect site limits (default: 50 codes per account/day). Over-automating may get your account blocked.

Files created:
- `redeem.py` — main script. Update CSS selectors at the top of the file if needed.
- `requirements.txt` — Python dependencies.

Quick start (PowerShell on Windows):

```powershell
# create & activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install deps
pip install -r requirements.txt

# create a file 'codes.txt' with one code per line (max 50 per run/account)
python redeem.py --player-id 123456 --codes-file codes.txt
```

Notes:
- If the script can't find the page inputs/buttons, open the page in your browser, inspect the Player ID and Code input elements and the Apply button, and update selectors in the `CONFIG` dictionary at the top of `redeem.py`.
- The script writes results to `results/results.csv` (timestamp, code, result).

Need help adapting the selectors or adding login support? Reply and paste the relevant HTML snippets or describe the UI and I will update the script.
