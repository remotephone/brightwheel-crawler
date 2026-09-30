import logging
import os
import re
import time
import yaml
import argparse
import random
import sys

import html
import subprocess
from datetime import datetime

import requests
import undetected_chromedriver as uc

from selenium.common.exceptions import ElementNotVisibleException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

"""I was saving pictures ad hoc through the brightwheel app, but got way behind
and didn't want to lose them if my kid changed schools or lost access to the app.
This uses selenium to crawl a BrightWheel (https://mybrightwheel.com/) profile
for images, find all of them, pass the cookies to requests, and then download
all images in bulk. Works with current site design as off 6/24/19"""


def parse_time_to_hms(time_str):
    try:
        t = datetime.strptime(time_str.strip(), "%I:%M %p")
        return t.strftime("%H:%M:%S")
    except Exception:
        return "00:00:00"


def parse_timestamp_from_text(text):
    """Parses date/time strings from Brightwheel feed like 'Jul 22, 2024 2:30 PM' or 'Jul 22, 2024'
    into EXIF format YYYY:MM:DD HH:MM:SS."""
    if not text:
        return None
    # ISO timestamp format: 2024-07-22T14:30:00
    m_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', text)
    if m_iso:
        y, m, d, hh, mm, ss = m_iso.groups()
        return f"{y}:{m}:{d} {hh}:{mm}:{ss}"
    # Path timestamp format e.g. 20240626202803
    m_path = re.search(r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])([01]\d|2[0-3])([0-5]\d)([0-5]\d)\b', text)
    if m_path:
        y, m, d, hh, mm, ss = m_path.groups()
        return f"{y}:{m}:{d} {hh}:{mm}:{ss}"
    # Standard text format e.g. Jul 22, 2024, 2:30 PM or Jul 22, 2024
    m_txt = re.search(r'\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})(?:\s*,?\s*(\d{1,2}:\d{2}\s+[AP]M))?\b', text)
    if m_txt:
        date_part, time_part = m_txt.group(1), m_txt.group(2)
        try:
            if time_part:
                dt = datetime.strptime(f"{date_part} {time_part}", "%b %d, %Y %I:%M %p")
            else:
                dt = datetime.strptime(date_part, "%b %d, %Y")
            return dt.strftime("%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
    return None


def apply_exif_timestamp(filepath, timestamp):
    """Uses exiftool to write DateTimeOriginal and CreateDate onto the image file if exiftool is installed."""
    if not timestamp or not os.path.exists(filepath):
        return
    try:
        cmd = [
            "exiftool",
            "-overwrite_original",
            f"-DateTimeOriginal={timestamp}",
            f"-CreateDate={timestamp}",
            filepath,
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        logger.debug("[-] - Applied EXIF timestamp %s to %s", timestamp, os.path.basename(filepath))
    except FileNotFoundError:
        logger.debug("[-] - exiftool not installed; skipping EXIF tag injection")
    except Exception as exc:
        logger.debug("[!] - Failed setting EXIF timestamp on %s: %s", filepath, exc)



logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_handler = logging.FileHandler("scraper.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def config_parser():
    """parse config file in config.yml if present"""
    try:
        with open("config.yml", "r") as config:
            config = yaml.safe_load(config)
    except FileNotFoundError:
        logger.error("[!] No config file found, check config file!")
        raise SystemExit

    return config


def get_random_time():
    """Randomly wait before sending imput, some time under 4 seconds"""
    random_wait = random.randint(0, 2000)
    return random_wait / 1000


# Get the first URL and populate the fields
def signme_in(browser, username, password, signin_url):
    """Populate and send login info using U/P from config"""

    browser.get(signin_url)
    time.sleep(get_random_time())
    loginuser = browser.find_element(By.XPATH, '//input[@id="username"]')
    loginpass = browser.find_element(By.ID, "password")
    loginuser.click()
    time.sleep(get_random_time())
    loginuser.send_keys(username)
    loginpass.click()
    time.sleep(get_random_time())
    loginpass.send_keys(password)

    # Submit login, have to wait for page to change
    try:
        loginpass.submit()
        WebDriverWait(browser, 45).until(EC.url_changes(signin_url))
    except:
        logger.error("[!] - Unable to authenticate - Check credentials")
        raise SystemExit
    time.sleep(get_random_time() * 3)  # Change this to the amount of time you need to solve the captcha manually
    return browser


def pic_finder(browser, kidlist_url, startdate, enddate, args):
    """This is the core logic of the script, navigate through the site, find
    the page with photos, scroll to the bottom to load them all, load them all
    in a specified date range, and create an iterable list of image URLs"""

    browser.get(kidlist_url)

    time.sleep(get_random_time())

    # This xpath is generic enough to find any student listed.
    # You need to iterate through a list you create if you have more than one
    try:
        students = browser.find_elements(By.XPATH, "//a[contains(@href, '/students/')]")
        logger.info("got students")
        if not students:
            raise Exception("No student URLs found")
        if args.student_number:
            profile_url = students[args.student_number - 1].get_property("href")
        else:
            try:
                logger.info("Select a student:")
                for i, student in enumerate(students):
                    logger.info(f"{i}. {student.text}")
                selection = int(input("Enter a number: "))
                profile_url = students[selection].get_property("href")
                # Replace last part of url path with feed
            except Exception as e:
                logger.error(f"[!] - Unable to find student: {e}")
                raise SystemExit

    except Exception as e:
        logger.error(f"[!] - Unable to find profile page: {e}")
        raise SystemExit

    feed_url = profile_url.rsplit("/", 1)[0] + "/feed"

    time.sleep(get_random_time())

    # Get to feed, this is where the pictures are
    # Open the feed_url
    browser.get(feed_url)
    time.sleep(3)

    # Populate the selector for date range to load all images
    start_date = browser.find_element(By.NAME, "start_date")
    start_date.send_keys(startdate)
    end_date = browser.find_element(By.NAME, "end_date")
    end_date.send_keys(enddate)
    select = browser.find_element(By.ID, "select-input-2")
    select.send_keys("Photo")
    select.send_keys(Keys.ENTER)

    # This is the XPATH for the Apply button.
    browser.find_element(By.XPATH, '//*[@id="main"]/div/div/div[2]/div/form/button').click()
    logger.info("[-] - Applied date range")
    try:
        last_height = browser.execute_script("return document.body.scrollHeight")
        counter = 0
        state = True
        while state is True:
            try:
                button = WebDriverWait(browser, 7).until(EC.presence_of_element_located((By.XPATH, '//button[text()="Load more"]')))
                button.click()
            except:
                if counter == 1:
                    logger.info("[-] No Loading button found, there may not be many pictures")
                else:
                    logger.error("[!] No loading button found")
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            counter += 1

            # Wait to load the page.
            time.sleep(2)

            # Calculate new scroll height and compare with last scroll height.
            new_height = browser.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                logger.info("[!] Page fully loaded, finding images...")
                state = False

            last_height = new_height

    except ElementNotVisibleException:
        logger.info("none")


    text = html.unescape(browser.page_source)
    tokens = []

    # 1. Full date/datetime headers
    date_pattern = r'\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})(?:\s*,?\s*(\d{1,2}:\d{2}\s+[AP]M))?\b'
    for m in re.finditer(date_pattern, text):
        tokens.append((m.start(), "date", m.group(0)))

    # 2. Standalone card post timestamps
    time_pattern = r'\b(\d{1,2}:\d{2}\s+[AP]M)\b'
    for m in re.finditer(time_pattern, text):
        tokens.append((m.start(), "time", m.group(0)))

    # 3. Image URLs matching upstream <img src="..."> pattern
    for m in re.finditer(r'<img\s+[^>]*src="([^"]+)"', text):
        raw_url = m.group(1)
        if raw_url.startswith("http"):
            tokens.append((m.start(), "url", raw_url))

    tokens.sort(key=lambda x: x[0])

    matches = []
    seen_urls = set()
    current_date_str = None
    current_time_str = "00:00:00"

    for _pos, token_type, val in tokens:
        if token_type == "date":
            parsed = parse_timestamp_from_text(val)
            if parsed:
                current_date_str = parsed.split(" ")[0]
                current_time_str = parsed.split(" ")[1] if " " in parsed else "00:00:00"
        elif token_type == "time":
            if current_date_str:
                current_time_str = parse_time_to_hms(val)
        elif token_type == "url":
            if val not in seen_urls:
                seen_urls.add(val)
                if current_date_str:
                    ts = f"{current_date_str} {current_time_str}"
                else:
                    ts = parse_timestamp_from_text(val)
                matches.append((val, ts))

    count_matches = len(matches)
    if count_matches == 0:
        logger.error("[!] No Images found to download! Check the source target page")
    else:
        logger.info("[!] Found {} files to download...".format(count_matches))

    return browser, matches


def get_images(browser, matches, prefix_date=True, write_exif=True):
    """Brightwheel moved their image storage to a CDN with signed urls, so we dont need to use
    cookies anymore. I'm eaving this code in case that behavior ever comes back
    
    Since Selenium doesn't handle saving images well, requests
    can do this for us, but we need to pass it the cookies"""
    # Check if the ./pics/ directory exists, create it if it doesn't
    if not os.path.exists('./pics/'):
        os.makedirs('./pics/')

    # cookies = browser.get_cookies()
    # session = requests.Session()
    # for cookie in cookies:
    #     session.cookies.set(cookie["name"], cookie["value"])
    # for match in matches:
    #     try:
    #         filename = match.split("/")[-1].split("?")[0].split("%2F")[-1]
    #         request = session.get(match)
    #         open("./pics/" + filename, "wb").write(request.content)
    #         logger.info("[-] - Downloading {}".format(filename))
    #     except:
    #         logger.error("[!] - Failed to save {}".format(match))
    # try:
    #     session.cookies.clear()
    #     browser.delete_all_cookies()
    #     logger.info("[-] - Cleared cookies")
    # except:
    #     logger.error("[!] - Failed to clear cookies")

    for item in matches:
        if isinstance(item, (tuple, list)):
            match, timestamp = item[0], item[1] if len(item) > 1 else None
        else:
            match, timestamp = item, None

        try:
            base_filename = match.split("/")[-1].split("?")[0].split("%2F")[-1]

            # If timestamp is available, prefix with YYYY_MM_DD_ to match rename.py convention
            if prefix_date and timestamp:
                date_str = timestamp.split(" ")[0].replace(":", "_")
                if not base_filename.startswith(date_str):
                    filename = f"{date_str}_{base_filename}"
                else:
                    filename = base_filename
            else:
                filename = base_filename

            filepath = os.path.join("./pics/", filename)
            request = requests.get(match)
            with open(filepath, "wb") as f:
                f.write(request.content)

            if write_exif and timestamp:
                apply_exif_timestamp(filepath, timestamp)

            if timestamp:
                logger.info("[-] - Downloading {} (date: {})".format(filename, timestamp))
            else:
                logger.info("[-] - Downloading {}".format(filename))
        except Exception as e:
            logger.error("[!] - Failed to save {}: {}".format(match, e))


def use_chrome_selenium():
    """Init logging and do it"""

    browser = uc.Chrome()
    return browser


def use_existing_chrome_session():
    # Check if chrome is listening on port 9222
    # If not, start it
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.debugger_address = "127.0.0.1:9222"
        browser = webdriver.Chrome(options=chrome_options)
        return browser
    except Exception as e:
        logger.error(f"An error occurred: {e} - Please ensure Chrome is listening on port 9222")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Brightwheel Scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--chrome_selenium", action="store_true", help="Use existing Chrome session to login to Brightwheel")
    group.add_argument("-e", "--chrome_session", action="store_true", help="Use existing Chrome session to login to Brightwheel")
    parser.add_argument(
        "-n", "--student-number", type=int, help="Select a student by number, indexed starting at 0. Look at the student list and count in order"
    )
    parser.add_argument(
        "--no-date-prefix", action="store_true", help="Do not prefix filenames with post date"
    )
    parser.add_argument(
        "--no-exif", action="store_true", help="Do not write EXIF tags using exiftool"
    )
    args = parser.parse_args()

    if args.chrome_selenium:
        browser = use_chrome_selenium()
    elif args.chrome_session:
        browser = use_existing_chrome_session()
    else:
        logger.error("[!] - No browser selected, exiting")

    config = config_parser()
    try:
        username = config["bwuser"]
        password = config["bwpass"]
        signin_url = config["bwsignin"]
        kidlist_url = config["bwlist"]
        startdate = config["startdate"]
        enddate = config["enddate"]
    except KeyError:
        logger.error("[!] - Check config file, missing required values")
        raise SystemExit

    session = signme_in(browser, username, password, signin_url)

    session, matches = pic_finder(session, kidlist_url, startdate, enddate, args)

    get_images(session, matches, prefix_date=not args.no_date_prefix, write_exif=not args.no_exif)


if __name__ == "__main__":
    main()
