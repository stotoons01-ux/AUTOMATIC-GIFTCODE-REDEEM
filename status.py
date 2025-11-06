"""
status.py

Small helper to scrape Task Status (importable version of check_status.py).
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import csv
from pathlib import Path


def scrape_task_status(out_dir='.', user_data_dir=None, profile_directory=None):
    options = Options()
    options.add_argument('--start-maximized')
    if user_data_dir:
        options.add_argument(f'--user-data-dir={user_data_dir}')
    if profile_directory:
        options.add_argument(f'--profile-directory={profile_directory}')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get('https://wosrewards.com/')
        time.sleep(1)
        # click Task Status
        try:
            el = driver.find_element(By.XPATH, "//a[contains(., 'Task Status')]")
            el.click()
            time.sleep(1)
        except Exception:
            pass

        rows = []
        try:
            table = driver.find_element(By.XPATH, "//table")
            tbody = table.find_element(By.TAG_NAME, 'tbody')
            tr_list = tbody.find_elements(By.TAG_NAME, 'tr')
            for tr in tr_list:
                cells = tr.find_elements(By.TAG_NAME, 'td')
                rows.append([c.text.strip() for c in cells])
        except Exception:
            pass

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / 'queue_status.csv'
        if rows:
            maxcols = max(len(r) for r in rows)
            with csv_path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = [f'col{i+1}' for i in range(maxcols)]
                writer.writerow(headers)
                for r in rows:
                    writer.writerow(r + [''] * (maxcols - len(r)))
        screenshot = out_dir / 'queue_status.png'
        driver.save_screenshot(str(screenshot))

        return {'rows': rows, 'csv': str(csv_path) if rows else None, 'screenshot': str(screenshot)}
    finally:
        try:
            driver.quit()
        except Exception:
            pass
