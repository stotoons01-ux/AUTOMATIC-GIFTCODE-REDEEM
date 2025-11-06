#!/usr/bin/env python3
"""
check_status.py

Open wosrewards.com, navigate to the "Task Status" page and scrape the queue/status table.
Saves `queue_status.csv` and `queue_status.png` in the workspace.

Usage:
  python check_status.py
"""

import csv
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def find_click(driver, xpath_expr):
    try:
        el = driver.find_element(By.XPATH, xpath_expr)
        el.click()
        return True
    except Exception:
        return False


def main():
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)
    try:
        driver.get("https://wosrewards.com/")
        time.sleep(1.0)

        # Try to click the "Task Status" menu link by partial text match
        clicked = False
        for xpath in ["//a[contains(., 'Task Status') or contains(., 'Task status')]", "//nav//a[contains(translate(., 'TASK STATUS', 'task status'), 'task status')]"]:
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
            print("Could not find 'Task Status' link — you may need to adjust selectors.")
            return

        # wait for page header 'Queue Status' or a table to appear
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Queue Status') or contains(., 'Task Status')]") ))
        except Exception:
            # proceed anyway
            pass

        time.sleep(1.0)

        # Attempt to locate a table with tbody rows
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
            # fallback: look for list items or rows in divs
            try:
                items = driver.find_elements(By.CSS_SELECTOR, ".table-responsive tr, .queue-list li, .task-row")
                for it in items:
                    texts = it.text.splitlines()
                    if texts:
                        rows.append([" | ".join(texts)])
            except Exception:
                pass

        out_csv = Path("queue_status.csv")
        if rows:
            # write CSV with dynamic column count
            maxcols = max(len(r) for r in rows)
            headers = [f"col{i+1}" for i in range(maxcols)]
            with out_csv.open("w", encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in rows:
                    # pad
                    writer.writerow(r + [""] * (maxcols - len(r)))
            print(f"Wrote {len(rows)} rows to {out_csv}")
        else:
            print("No table rows found on Task Status page.")

        # screenshot the page
        out_png = Path("queue_status.png")
        driver.save_screenshot(str(out_png))
        print(f"Saved screenshot to {out_png}")

    finally:
        time.sleep(1)
        driver.quit()


if __name__ == '__main__':
    main()
