#!/usr/bin/env python3
"""
redeem.py

Batch redeem script for wosrewards.com using Selenium.

Usage examples (PowerShell):
  python redeem.py --player-id 123456 --codes-file codes.txt

This script automates filling the player id and a gift code, clicking the apply button,
and logging the result. It assumes the site does NOT require a captcha.

IMPORTANT: The CSS selectors below are best-effort defaults. Inspect the site with
browser DevTools and update the selectors in the CONFIG dictionary if the script
can't find the inputs or button.
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager


# --- Config: update selectors here if the script can't find elements ---
CONFIG = {
    # Main URL
    "url": "https://wosrewards.com/",
    # CSS selector that opens the apply modal or focuses the form (if required). If not needed set to None
    "open_apply_selector": "button[data-target='#applyModal'], button#apply, a[href='#apply']",
    # Player ID input selector
    "player_selector": "input[name='playerId'], input#playerId, input[name='username'], input[name='player_id']",
    # Gift code input selector
    "code_selector": "input[name='code'], input[name='giftcode'], input#code",
    # Apply / submit button selector
    "submit_selector": "button[type='submit'], button#applyBtn, button.apply, input[type='submit']",
    # Optional selector for a visible message element to parse result text
    "message_selector": ".alert, .message, .result, #result",
}


def pick_first(driver, selector_list):
    """Try multiple comma-separated selectors and return the first found element."""
    for sel in selector_list.split(","):
        sel = sel.strip()
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            return el
        except Exception:
            continue
    raise RuntimeError(f"No element found for selectors: {selector_list}")


def init_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    # optional: set user agent or profile if needed
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def redeem_one(driver, wait, player_id, code, selectors):
    # Attempt to open apply form if there's an opener
    if selectors.get("open_apply_selector"):
        try:
            el = pick_first(driver, selectors["open_apply_selector"])
            try:
                el.click()
                # allow modal to open
                time.sleep(0.7)
            except Exception:
                pass
        except Exception:
            # it's okay if there's no opener
            pass

    # Fill player id
    player_elem = pick_first(driver, selectors["player_selector"])
    player_elem.clear()
    player_elem.send_keys(str(player_id))

    # Fill code
    code_elem = pick_first(driver, selectors["code_selector"])
    code_elem.clear()
    code_elem.send_keys(code)

    # Submit
    submit_elem = pick_first(driver, selectors["submit_selector"])
    try:
        submit_elem.click()
    except Exception:
        # fallback: send Enter from the code element
        from selenium.webdriver.common.keys import Keys

        code_elem.send_keys(Keys.RETURN)

    # wait briefly for response
    time.sleep(1.5)

    # capture message if available
    result_text = ""
    try:
        msg_el = driver.find_element(By.CSS_SELECTOR, selectors["message_selector"]) if selectors.get("message_selector") else None
        if msg_el:
            result_text = msg_el.text.strip()
    except Exception:
        # If no message element, try to read any alert text
        result_text = "(no message found)"

    return result_text


def run_batch(url, player_id, codes, out_csv, headless=False, per_account_limit=None, pause_between=1.0):
    driver = init_driver(headless=headless)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(url)
        # tiny wait for page JS to run
        time.sleep(1.0)

        results = []
        for i, code in enumerate(codes, start=1):
            if per_account_limit and i > per_account_limit:
                print(f"Reached per-account limit: {per_account_limit}. Stopping.")
                break

            print(f"[{i}/{len(codes)}] Redeeming code: {code}")
            try:
                result_text = redeem_one(driver, wait, player_id, code, CONFIG)
                print(" -> Result:", result_text)
                results.append({"code": code, "result": result_text})
            except Exception as e:
                print(" -> Error interacting with page:", e)
                results.append({"code": code, "result": f"error: {e}"})

            # small pause to mimic human behavior and avoid aggressive rate-limits
            time.sleep(pause_between)

        # write results
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "code", "result"])
            writer.writeheader()
            ts = datetime.utcnow().isoformat()
            for row in results:
                writer.writerow({"timestamp": ts, **row})

        print(f"Wrote results to {out_csv}")

    finally:
        print("Closing browser in 2 seconds for inspection...")
        time.sleep(2)
        driver.quit()


def load_codes(file_path):
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Codes file not found: {file_path}")
    codes = [line.strip() for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
    return codes


def main():
    parser = argparse.ArgumentParser(description="Batch redeemer for wosrewards.com (Selenium)")
    parser.add_argument("--player-id", required=True, help="Player ID to redeem for")
    parser.add_argument("--codes-file", required=True, help="Text file with one gift code per line (max 50 expected by site)")
    parser.add_argument("--url", default=CONFIG["url"], help="Redemption page URL")
    parser.add_argument("--out", default="results/results.csv", help="CSV file to write results")
    parser.add_argument("--headless", action="store_true", help="Run headless (not recommended when debugging selectors)")
    parser.add_argument("--per-account-limit", type=int, default=50, help="Max codes to attempt per account/day (site limit)")
    parser.add_argument("--pause", type=float, default=1.0, help="Seconds pause between attempts")
    args = parser.parse_args()

    codes = load_codes(args.codes_file)
    if not codes:
        print("No codes found in file.")
        sys.exit(1)

    out_csv = Path(args.out)
    run_batch(args.url, args.player_id, codes, out_csv, headless=args.headless, per_account_limit=args.per_account_limit, pause_between=args.pause)


if __name__ == "__main__":
    main()
