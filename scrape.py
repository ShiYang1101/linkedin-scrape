import time
import subprocess

import numpy as np
import pandas as pd
import selenium
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scraper import *

import sys
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

# options = Options()
# ua = UserAgent()
# userAgent = ua.random
# print(userAgent)
# options.add_argument(f'user-agent={userAgent}')


# Getting config variables
config_dict = config_to_dict()

try:
    num_page = int(sys.argv[1])
except IndexError:
    num_page = int(config_dict['DEFAULT_PAGE_NUM'])

# Connecting to webdriver
driver = webdriver.Chrome()

# Directing to Linkedin website
driver.get('https://www.linkedin.com')

# Reading login credentials
with open('./login_credential.txt') as f:
    lines = f.read().splitlines()

# Locating login WebElement

# Sending login credential to WebElements

username = driver.find_element(By.ID, 'session_key')
password = driver.find_element(By.ID, 'session_password')
username.send_keys(lines[0])
time.sleep(1)
password.send_keys(lines[1])

driver.find_element(By.CLASS_NAME, 'sign-in-form__submit-button').click()

time.sleep(5)


if EC.presence_of_element_located((By.ID, 'home_children_button')):
    time.sleep(2)
    inp = input("Captcha detectedd. Finish captcha and press any key to continue:")

# ChallengeSelectableOverlay__StyledElement-sc-6lu34v-0 jHFDJk


# Redirecting to job page
driver.get('https://linkedin.com/jobs')
time.sleep(20)
job_search = driver.find_element(By.XPATH, '//*[contains(@id, "jobs-search-box-keyword")]')
job_search.send_keys('data')

time.sleep(2)
location_search = driver.find_element(By.XPATH, '//*[contains(@id, "jobs-search-box-location")]')
location_search.send_keys('United Kingdom')

time.sleep(2)
job_search.send_keys(Keys.RETURN)
time.sleep(5)

skill_df, job_df = scrape_pages(driver, num_page)

try:
    _ = subprocess.run(["mkdir", '-p', './data'])
except:
    pass

skill_df.to_csv('./data/skill.csv')
job_df.to_csv('./data/job.csv')

