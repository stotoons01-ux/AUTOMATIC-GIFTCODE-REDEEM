"""
automation.py

Expose apply_player_ids(player_ids, out_dir=None, user_data_dir=None, profile_directory=None)
which performs the same steps as the previous apply_players script but is importable.
"""
import os
import shutil
import tempfile
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def _copy_profile_to_temp(user_data_dir, profile_directory):
    src_profile = os.path.join(user_data_dir, profile_directory)
    if not os.path.exists(src_profile):
        raise FileNotFoundError(src_profile)
    temp_dir = tempfile.mkdtemp(prefix='wos_profile_')
    dest_profile_parent = os.path.join(temp_dir, 'User Data')
    os.makedirs(dest_profile_parent, exist_ok=True)
    shutil.copytree(src_profile, os.path.join(dest_profile_parent, profile_directory))
    return dest_profile_parent


def apply_player_ids(player_ids, out_dir=None, user_data_dir=None, profile_directory=None, headless=False):
    """Apply given player_ids (list) on wosrewards.com. Returns dict with paths."""
    if isinstance(player_ids, (str,)):
        pids = [player_ids]
    else:
        pids = list(player_ids)

    out_dir = Path(out_dir or '.')
    out_dir = out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--start-maximized')

    temp_copy = None
    if user_data_dir and profile_directory:
        try:
            temp_copy = _copy_profile_to_temp(user_data_dir, profile_directory)
            options.add_argument(f"--user-data-dir={temp_copy}")
        except Exception:
            options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--profile-directory={profile_directory}")
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get('https://wosrewards.com/')
        time.sleep(1.0)

        # find textarea
        try:
            textarea = wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "textarea[placeholder*='player IDs']"))
        except Exception:
            textarea = driver.find_element(By.CSS_SELECTOR, 'textarea')

        textarea.clear()
        textarea.send_keys(' '.join(pids))
        time.sleep(0.3)

        # click Apply Codes
        try:
            btn = driver.find_element(By.XPATH, "//button[normalize-space()='Apply Codes']")
        except Exception:
            btn = driver.find_element(By.CSS_SELECTOR, 'button')
        btn.click()
        time.sleep(1.0)

        apply_screenshot = out_dir / 'apply_result.png'
        driver.save_screenshot(str(apply_screenshot))

        # navigate to Task Status and scrape table (reuse status.py functionality)
        try:
            link = driver.find_element(By.XPATH, "//a[contains(., 'Task Status')]")
            link.click()
            time.sleep(1.0)
        except Exception:
            pass

        # try to scrape table rows
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

        # write CSV
        status_csv = out_dir / 'task_status.csv'
        try:
            import csv
            if rows:
                maxcols = max(len(r) for r in rows)
                with status_csv.open('w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    headers = [f'col{i+1}' for i in range(maxcols)]
                    writer.writerow(headers)
                    for r in rows:
                        writer.writerow(r + [''] * (maxcols - len(r)))
        except Exception:
            status_csv = None

        return {'apply_screenshot': str(apply_screenshot), 'status_rows': rows, 'status_csv': str(status_csv) if status_csv and status_csv.exists() else None}

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        # cleanup temp copy
        if temp_copy and os.path.exists(temp_copy):
            try:
                shutil.rmtree(temp_copy)
            except Exception:
                pass
