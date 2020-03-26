import requests
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()

def getSession(loginUrl, username, password, headless=True):
    options.headless = headless
    s = requests.Session()

    # Open URL
    driver = webdriver.Chrome("./chromedriver", chrome_options=options)
    driver.get(loginUrl)

    # Select ETH
    driver.find_element_by_xpath("//select[1]/option[2]").click()
    driver.find_element_by_class_name("btn-primary").click()

    # Fill in login info
    driver.find_element_by_id("username").send_keys(username)
    driver.find_element_by_id("username").click() # It does not work without this sometimes
    driver.find_element_by_id("password").send_keys(password)
    driver.find_element_by_name("_eventId_proceed").click()

    # Get the cookies
    s = requests.Session()
    cookies = driver.get_cookies()
    for c in cookies: s.cookies.set(c['name'], c['value'])

    # Close driver
    driver.close()

    return s
