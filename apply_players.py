#!/usr/bin/env python3
"""
apply_players.py

Simple script to fill the player IDs textarea on wosrewards.com and click "Apply Codes".
This performs a real submission on the live site. Use responsibly and confirm you own the
player IDs or have permission.

Usage:
  python apply_players.py --player-ids "529265458"

The script saves `apply_result.png` (screenshot after submission) and prints any visible message.
"""

import argparse
import time
import os
import shutil
import tempfile
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def pick_first(driver, selectors):
    for sel in selectors.split(","):
        sel = sel.strip()
        try:
            return driver.find_element(By.CSS_SELECTOR, sel)
        except Exception:
            continue
    raise RuntimeError(f"No element found for selectors: {selectors}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-ids", required=True, help="Player IDs (comma/space/newline separated)")
    parser.add_argument("--url", default="https://wosrewards.com/", help="Target URL")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--user-data-dir", default=None, help="Path to Chrome user data dir to reuse profile (optional)")
    parser.add_argument("--profile-directory", default=None, help="Chrome profile directory name inside user-data-dir (e.g. 'Default' or 'Profile 2')")
    args = parser.parse_args()

    options = Options()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")

    # If user-data-dir and profile-directory provided, attempt to copy that profile to a temp dir
    # and use the copy. Copying avoids lockfile and extension-related crashes when launching
    # from an existing profile directory.
    temp_dir = None
    if args.user_data_dir and args.profile_directory:
        src_profile = os.path.join(args.user_data_dir, args.profile_directory)
        if os.path.exists(src_profile):
            print(f"Copying profile from {src_profile} to a temporary directory to avoid locks...")
            temp_dir = tempfile.mkdtemp(prefix="wos_profile_")
            try:
                # copy the whole user-data-dir but only the specified profile folder
                dest_profile_parent = os.path.join(temp_dir, "User Data")
                os.makedirs(dest_profile_parent, exist_ok=True)
                shutil.copytree(src_profile, os.path.join(dest_profile_parent, args.profile_directory))
                # Use the temporary 'User Data' folder as the user-data-dir for Chrome
                args.user_data_dir = dest_profile_parent
            except Exception as e:
                print("Warning: failed to copy profile, attempting to use original profile directly:", e)

    # If user-data-dir or profile-directory provided, add to options so Selenium uses that Chrome profile.
    if args.user_data_dir:
        options.add_argument(f"--user-data-dir={args.user_data_dir}")
        # add flags that often improve launching with an existing profile
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
    if args.profile_directory:
        options.add_argument(f"--profile-directory={args.profile_directory}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    try:
        print("Opening page...")
        driver.get(args.url)
        time.sleep(1.0)

        # Try a few reasonable selectors for the textarea and the Apply button
        textarea_selectors = "textarea[placeholder*='player IDs'], textarea#players, textarea"
        apply_btn_selectors = "button:where([type='button']), button, input[type='button'], input[type='submit']"

        # Prefer button with exact text 'Apply Codes' using XPath
        try:
            textarea = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder*='player IDs']")))
        except Exception:
            # fallback to any textarea
            textarea = pick_first(driver, textarea_selectors)

        # fill textarea
        print("Filling player IDs into textarea...")
        textarea.clear()
        textarea.send_keys(args.player_ids)
        time.sleep(0.3)

        # find apply button by XPath text match first
        apply_btn = None
        try:
            apply_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Apply Codes']")
        except Exception:
            # try contains
            try:
                apply_btn = driver.find_element(By.XPATH, "//button[contains(., 'Apply Codes')]")
            except Exception:
                pass

        if not apply_btn:
            # fallback: pick first visible button near the textarea
            try:
                # attempt to find a button following the textarea
                apply_btn = driver.find_element(By.XPATH, "//textarea/following::button[1]")
            except Exception:
                apply_btn = pick_first(driver, apply_btn_selectors)

        print("Clicking Apply Codes button...")
        apply_btn.click()

        # wait a bit for result
        time.sleep(2.0)
        out_path = Path("apply_result.png")
        driver.save_screenshot(str(out_path))
        print(f"Saved screenshot to {out_path}")

        # try to read a message element
        msg_text = None
        for sel in [".alert", ".message", ".result", "#result"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                txt = el.text.strip()
                if txt:
                    msg_text = txt
                    break
            except Exception:
                continue

        if msg_text:
            print("Result message:", msg_text)
        else:
            print("No obvious message element found. Check apply_result.png for page state.")

        # After applying, navigate to Task Status to check queue for the player IDs
        try:
            print("Navigating to Task Status page...")
            # try clicking the Task Status menu link
            clicked = False
            for xpath in ["//a[contains(., 'Task Status') or contains(., 'Task status')]", "//a[contains(translate(., 'TASK STATUS', 'task status'), 'task status')]"]:
                try:
                    el = driver.find_element(By.XPATH, xpath)
                    el.click()
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                # fallback: find link with href containing 'task' or 'status'
                try:
                    el = driver.find_element(By.XPATH, "//a[contains(@href, 'task') or contains(@href, 'status')]")
                    el.click()
                    clicked = True
                except Exception:
                    pass

            if not clicked:
                print("Could not find Task Status link on the page. Skipping status check.")
            else:
                time.sleep(1.0)
                # wait for table or header
                try:
                    wait.until(lambda d: d.find_element(By.XPATH, "//table") or d.find_element(By.XPATH, "//h1[contains(., 'Queue Status')]") )
                except Exception:
                    pass

                # scrape table rows (if any)
                rows = []
                try:
                    table = driver.find_element(By.XPATH, "//table")
                    tbody = table.find_element(By.TAG_NAME, "tbody")
                    tr_list = tbody.find_elements(By.TAG_NAME, "tr")
                    for tr in tr_list:
                        cells = tr.find_elements(By.TAG_NAME, "td")
                        texts = [c.text.strip() for c in cells]
                        if texts:
                            rows.append(texts)
                except Exception:
                    # fallback: try other selectors
                    try:
                        items = driver.find_elements(By.CSS_SELECTOR, ".table-responsive tr, .queue-list li, .task-row")
                        for it in items:
                            texts = it.text.splitlines()
                            if texts:
                                rows.append([" | ".join(texts)])
                    except Exception:
                        pass

                out_csv = Path("task_status_after_apply.csv")
                if rows:
                    maxcols = max(len(r) for r in rows)
                    headers = [f"col{i+1}" for i in range(maxcols)]
                    with out_csv.open("w", encoding='utf-8', newline='') as f:
                        import csv as _csv
                        writer = _csv.writer(f)
                        writer.writerow(headers)
                        for r in rows:
                            writer.writerow(r + [""] * (maxcols - len(r)))
                    print(f"Wrote {len(rows)} rows to {out_csv}")

                    # filter rows matching any provided player id
                    pids = [p.strip() for p in args.player_ids.replace(',', ' ').split() if p.strip()]
                    matched = []
                    for r in rows:
                        line = ' '.join(r)
                        for pid in pids:
                            if pid in line:
                                matched.append((pid, line))
                    if matched:
                        print("Found status entries for provided player IDs:")
                        for pid, line in matched:
                            print(pid, "->", line)
                    else:
                        print("No matching player IDs found in the queue table (refresh may be required).")
                else:
                    print("No rows found on Task Status page after apply.")

                out_png2 = Path("task_status_after_apply.png")
                driver.save_screenshot(str(out_png2))
                print(f"Saved Task Status screenshot to {out_png2}")
        except Exception as e:
            print("Error while checking Task Status:", e)

    finally:
        print("Done. Closing browser in 2 seconds...")
        time.sleep(2)
        driver.quit()


if __name__ == '__main__':
    main()
