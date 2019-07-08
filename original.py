import re
import time

from urllib.parse import urlparse
import requests
from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# Authentication - form filled
username = 'email@domain.com'
password = 'mypassword'

# URLs - signing and list of kids, need to iterate per kid if multiple
signin_url = 'https://schools.mybrightwheel.com/sign-in'
kidlist_url = 'https://schools.mybrightwheel.com/children/list'


# Set up the driver, using firefox



options = Options()
options.set_preference("browser.download.folderList",2)
options.set_preference("browser.download.manager.showWhenStarting", False)
options.set_preference("browser.download.dir","/data")
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "image/png")
browser = webdriver.Firefox(firefox_options=options)



browser.delete_all_cookies()


# Get the first URL and populate the fields 
browser.get(signin_url)

loginElemUser = browser.find_element_by_id('textfield-input-2')
loginElemPass = browser.find_element_by_id('textfield-input-3')
loginElemUser.send_keys(username)
loginElemPass.send_keys(password)

# Submit login, have to wait for page to change
loginElemPass.submit()

WebDriverWait(browser, 5).until(EC.url_changes(signin_url))

# Once authed, request kid list page
kidlist = browser.get(kidlist_url)

WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, '//*[contains(@href, "/students/")]')))

# This is the class name specific to my kid, there may be a more generic way to find this
students = browser.find_element_by_xpath("//*[contains(@href, '/students/')]")

profile_url = students.get_property('href')
browser.get(profile_url)


WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.LINK_TEXT, 'Feed')))

# Get to feed, this is where the picutres ared
pics = browser.find_element_by_link_text('Feed')

pics.click()

WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.NAME, 'activity-start-date')))
start_date = browser.find_element_by_name('activity-start-date')
start_date.send_keys('01/01/2018')
end_date = browser.find_element_by_name('activity-end-date')
end_date.send_keys('06/13/2019')



select = browser.find_element_by_id('select-input-2')
select.send_keys('Photo')
select.send_keys(Keys.ENTER)

browser.find_element_by_xpath('/html/body/div[2]/div/div/div[2]/div/main/div/form/button').click()


# browser.find_element_by_xpath('//button[text()="Load more"]').click()



try:
    last_height = browser.execute_script("return document.body.scrollHeight")
    state = True
    while state == True:
        try:
            button = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//button[text()="Load more"]')))
            button.click()
        except:
            print('No Loading button found!')
       # Scroll down to the bottom.
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load the page.
        time.sleep(2)

        # Calculate new scroll height and compare with last scroll height.
        new_height = browser.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            state = False
            print('heights match')

        last_height = new_height

except ElementNotVisibleException:
    print('none')
    
matches = re.findall(
    r'(?<=src=\")https:\/\/cdn\.mybrightwheel\.com\/media_images\/images\/.*png(?="?)', browser.page_source)

# Get all the images:
# 
# 

cookies = browser.get_cookies()

s = requests.Session()
for cookie in cookies:
    s.cookies.set(cookie['name'], cookie['value'])

for match in matches:
    filename = match.split("/")[-1]
    r = s.get(match)
    open('./pics/' + filename, 'wb').write(r.content)

