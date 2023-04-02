import json
import logging
import pickle
import subprocess
import sys
import time

import boto3
import numpy as np
import pandas as pd
import pymysql
import selenium
from bs4 import BeautifulSoup as bs
from scraper.linkedindb import (config_to_dict, linkedin_driver, linkedin_soup,
                                scrape_page, scrape_pages)
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# rds settings
rds_host  = "linkedindb.cfgrnqd26sws.eu-west-2.rds.amazonaws.com"
user_name = "shiya"
# create the database connection outside of the handler to allow connections to be

password = "Chromeing1!"
db_name = "linkedin_db"

logger = logging# re-used by subsequent function invocations.
try:
    conn = pymysql.connect(host=rds_host, user=user_name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def credential_decrypt(KeyId, region = 'eu-west-2'):
    client = boto3.client('kms', region_name = region)
    with open('credential', 'rb') as f:
        credential = pickle.load(f)

    return {key: client.decrypt(CiphertextBlob = item['CiphertextBlob'], KeyId = KeyId)['Plaintext'].decode() 
            for key, item in credential.items()}


# Getting config variables
config_dict = config_to_dict()

try:
    num_page = 10
except IndexError:
    num_page = int(config_dict['DEFAULT_PAGE_NUM'])

def lambda_handler(event, context):
    options = webdriver.ChromeOptions()

    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu-sandbox')
    options.add_argument("--single-process")
    options.add_argument('window-size=1920x1080')
    options.add_argument(
        '"user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"')

    options.binary_location = "/bin/headless-chromium"


    curr = conn.cursor()

    credential = credential_decrypt('alias/linkedin-key')

    # Connecting to webdriver
    print("Connecting to Linkedin from driver...")
    driver = linkedin_driver(debug = True, executable_path="/bin/chromedriver", options=options)
    print("Connection established!")

    print("Login into Linkedin...")
    driver.login(credential['Username'], credential['Password'])
    print("Login successful.")

    # Redirecting to job page
    print("Directing to job page...")
    driver.go_job()

    time.sleep(20)
    job_search = driver.find_element(By.XPATH, '//*[contains(@id, "jobs-search-box-keyword")]')
    job_search.send_keys('data')

    time.sleep(2)
    location_search = driver.find_element(By.XPATH, '//*[contains(@id, "jobs-search-box-location")]')
    location_search.send_keys('United Kingdom')

    time.sleep(2)
    job_search.send_keys(Keys.RETURN)

    time.sleep(20)
    driver.apply_date_filter()


    print("Initialize scraping...")
    skill_df, job_df = scrape_pages(driver, curr, conn=conn, page_num= num_page)
    print("Scraping done! Updating database...")
    print("Update finished")



    # try:
    #     _ = subprocess.run(["mkdir", '-p', './data'])
    # except:
    #     pass

    # skill_df.to_csv('./data/skill.csv')
    # job_df.to_csv('./data/job.csv')

