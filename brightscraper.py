import logging
import re
import time
import yaml

import requests
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


def config_parser():
    """parse config file in config.yml if present"""
    try:
        with open("config.yml", 'r') as config:
            cfg = yaml.safe_load(config)
        username = cfg['bwuser']
        password = cfg['bwpass']
        signin_url = cfg['bwsignin']
        kidlist_url = cfg['bwlist']
        startdate = cfg['startdate']
        enddate = cfg['enddate']
    except FileNotFoundError:
        logging.error('[!] No config file found, check config file!')
        raise SystemExit

    return username, password, signin_url, kidlist_url, startdate, enddate


# Get the first URL and populate the fields
def signme_in(browser, username, password, signin_url):
    """Populate and send login info using U/P from config"""

    browser.get(signin_url)
    time.sleep(2)
    loginuser = browser.find_element(By.XPATH, '//input[@id="username"]')
    loginpass = browser.find_element(By.ID, 'password')
    loginuser.click()
    time.sleep(2)
    loginuser.send_keys(username)
    loginpass.click()
    time.sleep(2)
    loginpass.send_keys(password)

    # Submit login, have to wait for page to change
    try:
        loginpass.submit()
        WebDriverWait(browser, 5).until(EC.url_changes(signin_url))
    except:
        logging.error('[!] - Unable to authenticate - Check credentials')
        raise SystemExit

    return browser


def pic_finder(browser, kidlist_url, startdate, enddate):
    """ This is the core logic of the script, navigate through the site, find
    the page with photos, scroll to the bottom to load them all, load them all
    in a specified date range, and create an iterable list of image URLs"""

    browser.get(kidlist_url)

    time.sleep(3)

    # This xpath is generic enough to find any student listed.
    # You need to iterate through a list you create if you have more than one
    try:
        students = browser.find_element(By.XPATH,
            "//a[contains(@href, '/students/')]"
            )
        profile_url = students.get_property('href')
        browser.get(profile_url)
    except:
        logging.error('[!] - Unable to find profile page, check target')
        raise SystemExit

    time.sleep(3)

    # Get to feed, this is where the pictures are
    pics = browser.find_element(By.LINK_TEXT, 'Feed')
    pics.click()
    time.sleep(3)

    # Populate the selector for date range to load all images
    start_date = browser.find_element(By.NAME, 'activity-start-date')
    start_date.send_keys(startdate)
    end_date = browser.find_element(By.NAME, 'activity-end-date')
    end_date.send_keys(enddate)
    select = browser.find_element(By.ID, 'select-input-2')
    select.send_keys('Photo')
    select.send_keys(Keys.ENTER)

    # This is the XPATH for the Apply button.
    browser.find_element(By.XPATH,
        '/html/body/div[2]/div/main/div/div/div[2]/div/form/button'
        ).click()

    try:
        last_height = browser.execute_script(
            "return document.body.scrollHeight"
            )
        counter = 0
        state = True
        while state is True:
            try:
                counter += 1
                button = WebDriverWait(browser, 7).until(
                    EC.presence_of_element_located((
                        By.XPATH, '//button[text()="Load more"]')))
                button.click()
            except:
                if counter == 1:
                    logging.info('[!] No Loading button found!')
                else:
                    logging.debug('[!] No loading button found')
            browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load the page.
            time.sleep(2)

            # Calculate new scroll height and compare with last scroll height.
            new_height = browser.execute_script(
                "return document.body.scrollHeight")

            if new_height == last_height:
                logging.info('[!] Page fully loaded, finding images...')
                state = False

            last_height = new_height

    except ElementNotVisibleException:
        print('none')

    matches = re.findall(
        r'(?<=href=\")https:\/\/cdn\.mybrightwheel\.com\/media_images\/images\/[0-9a-zA-Z\/]*\.(?:jpg|png)(?="?)',
        browser.page_source)
    count_matches = len(matches)
    if count_matches == 0:
        logging.error(
            '[!] No Images found to download! Check the source target page')
    else:
        logging.info('[!] Found {} files to download...'.format(count_matches))

    return browser, matches


def get_images(browser, matches):
    """ Since Selenium doesn't handle saving images well, requests
    can do this for us, but we need to pass it the cookies"""
    cookies = browser.get_cookies()

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    for match in matches:
        try:
            filename = match.split("/")[-1]
            request = session.get(match)
            open('./pics/' + filename, 'wb').write(request.content)
            logging.info('[-] - Downloading {}'.format(filename))
        except:
            logging.error('[!] - Failed to save {}'.format(match))

    try:
        session.cookies.clear()
        browser.delete_all_cookies()
        logging.info('[-] - Cleared cookies')
    except:
        logging.error('[!] - Failed to clear cookies')


def main():
    """Init logging and do it"""
    logging.basicConfig(filename='scraper.log', filemode='w')

    browser = webdriver.Firefox()

    username, password, signin_url, kidlist_url, startdate, enddate = config_parser()

    browser = signme_in(browser, username, password, signin_url)

    browser, matches = pic_finder(browser, kidlist_url, startdate, enddate)

    get_images(browser, matches)


if __name__ == "__main__":
    main()
