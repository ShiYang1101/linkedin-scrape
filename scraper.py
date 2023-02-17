import time

from tqdm import tqdm
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

import re

JOB_LISTING_XPATH = '//*[@id="main"]/div/section[1]/div/ul/*' 
LINK_XPATH = '//div[contains(@class, "jobs-unified-top-card t-14")]//a[@href]'

def config_to_dict(file = './config.txt'):

    with open('./config.txt', 'r') as f:
        lines = f.readlines()
    f.close()
    return dict([[y.strip() for y in x] for x in \
                [x.strip().split(':') for x in lines] if x != ['']])


def get_job_elems(driver):
    """
    Suppporting function used for getting the WebElements of individual job posts
    
    Input: selenium.webdriver, driver used to navigate browsers
    Output: list of WebElement.
    """
    return driver.find_elements(By.XPATH, JOB_LISTING_XPATH)


def get_id(driver):
    """
    Suppporting function used for getting the WebElements of job posting's ID. 
    
    Input: selenium.webdriver, driver used to navigate browsers
    Output: WebElement.
    """

    # Acquiring the WebElement containing href of job posting.
    link_elem = driver.find_element(By.XPATH, LINK_XPATH)

    # Acquiring link to job posting
    link = link_elem.get_attribute('href')

    # Using regex to acquire job ID from link
    _id = re.findall('(?<=view/)(.*)(?=/)', link)

    assert len(_id) == 1, "Multiple Id found for same job posting!"

    return int(_id[0]) 

def get_skills(driver):
    time.sleep(0.5)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, 
                        "//button[contains(@aria-label, 'View strong skill match modal')]"))
        )
        try:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()
        except StaleElementReferenceException:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()
    except TimeoutException:
        return False

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, 
                        "//ul[contains(@class, 'job-details-skill-match-status-list')]"))
        )
    except TimeoutException:
        return

    skill = driver.find_elements(By.XPATH, 
                            "//ul[contains(@class, 'job-details-skill-match-status-list')]")

    text = skill[0].text.replace("Add", '')

    driver.find_element(By.XPATH, "//div[contains(@aria-labelledby, 'jobs-skill-match-modal-header')]//button").click()

    return [skill for skill in text.split("\n") if skill != '']
    
    
def generate_skill_df(driver, elem):
    action = ActionChains(driver)
    action.move_to_element(elem).perform()
    elem.click()
    _id = get_id(elem)
    _skills = get_skills(driver)

    if _skills == False:
        return 

    _df = pd.DataFrame({'id': [_id for x in range(len(_skills))], \
                        'skills': _skills})

    return(_df)

def generate_all_skill_df(driver, elems):
    df_list = []
    for elem in elems:
        _df = generate_skill_df(elem)
        df_list.append(_df)
    
    df_list = [df for df in df_list if ~isinstance(df, type(None))]
    return pd.concat(df_list)

def set_execute(func):
    func.execute = True
    return func

class linkedin_soup(object):

    def __init__(self, soup, auto_execute = True):
        self.soup = soup
        if auto_execute:
            self.auto_generate()
    
    @set_execute
    def get_link(self):
        self.link = 'https://www.linkedin.com' + self.soup.find(class_=re.compile('jobs-unified-top-card__content.*')).\
                                                        find('a')['href']

    @set_execute
    def get_id(self):
        if 'link' not in self.__dict__.keys():
            self.get_link()
        _id = re.findall('(?<=view/)(.*)(?=/)', self.link)

        assert len(_id) == 1, 'Multiple id detected'
        self.id = int(_id[0])


    @set_execute
    def get_title(self):
        title_elem = self.soup.find_all(class_='t-24 t-bold jobs-unified-top-card__job-title')
        assert len(title_elem) == 1, "More than 1 job title found on page!"

        title = title_elem[0].contents[0]
        assert isinstance(title, str)

        self.title = title

    @set_execute
    def get_company(self):
        try:
            self.company =  self.soup.find(class_ = 'jobs-unified-top-card__company-name').text.strip()
        except AttributeError:
            self.company_name =  np.nan

    @set_execute
    def get_location(self):
        try:
            self.location =  self.soup.find(class_="jobs-unified-top-card__bullet").text.strip()
        except AttributeError:
            self.location =  np.nan

    @set_execute
    def get_job_type(self):
        try:
            self.job_type =  self.soup.find(class_=re.compile(".*workplace-type")).text
        except AttributeError:
            self.job_type =  np.nan
        
    @set_execute
    def get_employees_company(self):
        insight = self.soup.find_all(class_=re.compile('jobs-unified-top-card__job-insight'))
        emp_comp = [string for string in [match.find(string=re.compile(".*employees.*")) 
                                for match in insight] if string][0]
        try:
            self.employee, self.company_type = tuple([data.strip() for data in emp_comp.split("·")])
        except ValueError:
            self.employee = emp_comp.strip()
            self.company_type = np.nan

    @set_execute
    def get_salary(self):
        try:
            self.salary = self.soup.find(href='#SALARY').text
        except AttributeError:
            self.salary = np.nan

    @set_execute
    def get_job_desc(self):
        self.job_desc = self.soup.select("div#job-details > span")[0].get_text(separator="\n").strip()
    
    def auto_generate(self):
        for method in dir(self):
            if getattr(getattr(self, method), 'execute', False):
                getattr(self, method)()
    
    def generate_df(self):
        return pd.DataFrame({key:item for key, item in self.__dict__.items() if key != 'soup'}, 
            index = [0])

        

class listing_wait(object):

    def __init__(self, locator, xpath):
        self.locator = locator
        self.xpath = xpath

    def __call__(self, driver):
        _elements = driver.find_elements(self.locator, self.xpath)
        if len(_elements) == 0:
            return False
        else:
            return _elements

# driver.refresh()
# # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, 
# #                         "//ul[contains(@class, 'scaffold-layout__list-container')]")))

# time.sleep(15)

# job_elems = get_job_elems(driver)
# print(len(job_elems))
# action = ActionChains(driver)

# for elem in job_elems:
#     action.move_to_element(elem).perform()
#     WebDriverWait(driver, 10).until(EC.element_to_be_clickable(elem))
#     elem.click()
#     # test = WebDriverWait(driver, 10).until(listing_wait(By.XPATH, 
#     #                     "//h2[contains(@class, 't-24 t-bold jobs-unified-top-card__job-title')]"))
#     WebDriverWait(driver, 10, ignored_exceptions=StaleElementReferenceException).until(EC.element_to_be_clickable((By.XPATH, 
#                                 "//div[contains(@class, 'jobs-apply-button')]//button")))
#     # time.sleep(1)
#     soup = bs(driver.page_source)
#     print(get_title(soup), get_company(soup), get_location(soup))
def scrape_page(driver, pbar = None):
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, 
    #                         "//ul[contains(@class, 'scaffold-layout__list-container')]")))

    time.sleep(15)

    job_elems = get_job_elems(driver)
    assert len(job_elems) == 25, "Job listing less than 25, web page not properly loaded!"

    skill_dfs = []
    job_dfs = []
    for elem in job_elems:
        action = ActionChains(driver)
        action.move_to_element(elem).perform()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(elem))
        elem.click()
        # test = WebDriverWait(driver, 10).until(listing_wait(By.XPATH, 
        #                     "//h2[contains(@class, 't-24 t-bold jobs-unified-top-card__job-title')]"))
        try:
            WebDriverWait(driver, 10, ignored_exceptions=StaleElementReferenceException).until(EC.element_to_be_clickable((By.XPATH, 
                                        "//div[contains(@class, 'jobs-apply-button')]//button")))
        except TimeoutException:
            WebDriverWait(driver, 10, ignored_exceptions=StaleElementReferenceException).until(EC.presence_of_element_located((By.XPATH, 
                                        "//div[contains(@class, 'feedback--success')]")))
        
        skill_dfs.append(generate_skill_df(driver, elem))
        _soup = bs(driver.page_source, features="html.parser")
        _linkedin_soup = linkedin_soup(_soup)
        job_dfs.append(_linkedin_soup.generate_df())
        if ~isinstance(pbar, type(None)):
            pbar.update(1)

    return (pd.concat(skill_dfs, ignore_index=True), pd.concat(job_dfs, ignore_index=True))

def scrape_pages(driver, page_num = 40):
    skill_dfs = []
    job_dfs = []

    with tqdm(total=page_num * 25) as pbar:
        for page in range(1, page_num + 1):
            print(f"Page {page}")
            if page != 1:
                driver.refresh()
            WebDriverWait(driver, 10, ignored_exceptions=StaleElementReferenceException).until(EC.element_to_be_clickable((By.XPATH, 
                                        f"//button[contains(@aria-label, 'Page {page}')]")))

            page_button = driver.find_element(By.XPATH, f"//button[contains(@aria-label, 'Page {page}')]")
            action = ActionChains(driver)
            action.move_to_element(page_button)
            page_button.click()

            time.sleep(15)

            _skill_df, _job_df = scrape_page(driver, pbar)

            skill_dfs.append(_skill_df)
            job_dfs.append(_job_df)
    return (pd.concat(skill_dfs, ignore_index=True), pd.concat(job_dfs, ignore_index=True))
