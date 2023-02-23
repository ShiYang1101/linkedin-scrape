import time

from tqdm.auto import tqdm
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
    """
    Helper function to read configuration file, creating a dictionary with 
    matching variable and values.
    
    Input: str, path to config file.
    Output: dict.
    """

    with open('./config.txt', 'r') as f:
        lines = f.readlines()
    f.close()
    # Splitting variables and values, creating dictionary
    return dict([[y.strip() for y in x] for x in \
                [x.strip().split(':') for x in lines] if x != ['']])


config_dict = config_to_dict()

def apply_date_filter(driver, filter):
    assert filter.lower() in ['a', 'd', 'm', 'w', 'any','day', 'week', 'month'], \
                        "Please provide available filter, :\n'a', 'd', 'm', 'w' or 'any', 'day', 'week' or 'month"
    driver.find_element(By.XPATH, "//span/button[contains(@aria-label, 'Date posted filter')]").click()
    


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
    """
    Support function for getting the skill section from single job posting on Linkedin.
    Assumed that the relevant job posting has been clicked.
    
    Input: selenium.driver, driver used to navigate webpage.
    Output: list, list of skills in job posting.
    """

    time.sleep(5)
    try:
        # Open skills page for relevant job posting

        # Wait until skills section available
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, 
                        "//button[contains(@aria-label, 'View strong skill match modal')]"))
        )

        # Openeing skill section
        try:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()

        # Try again if skill section's Webelement changed
        except StaleElementReferenceException:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()

    # No skill section found, return False
    except TimeoutException:
        return False

    try:
        # Find WebElement containg list of skills
        WebDriverWait(driver, 90).until(
            EC.presence_of_all_elements_located((By.XPATH, 
                        "//ul[contains(@class, 'job-details-skill-match-status-list')]"))
        )
    except TimeoutException:
        # Try again in case WebElement changes 
        driver.find_element(By.XPATH, "//div[contains(@aria-labelledby, 'jobs-skill-match-modal-header')]//button").click()
        try:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()
        except StaleElementReferenceException:
            driver.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'View strong skill match modal')]").click()
            WebDriverWait(driver, 50).until(
                EC.presence_of_all_elements_located((By.XPATH, 
                            "//ul[contains(@class, 'job-details-skill-match-status-list')]"))
            )


    time.sleep(0.1)

    # Acquiring skills listed in WebElement
    skill = driver.find_elements(By.XPATH, 
                            "//ul[contains(@class, 'job-details-skill-match-status-list')]")

    # SKills not loaded in time, returning False and exit function
    try:
        text = skill[0].text.replace("Add", '')
    except IndexError:
        # Closing skill section page
        driver.find_element(By.XPATH, "//div[contains(@aria-labelledby, 'jobs-skill-match-modal-header')]//button").click()
        return False
    
    # Closing skill section page
    driver.find_element(By.XPATH, "//div[contains(@aria-labelledby, 'jobs-skill-match-modal-header')]//button").click()

    return [skill for skill in text.split("\n") if skill != '']
    
    
def generate_skill_df(driver, elem):
    """Support function generating dataframe for skills for each job posting.
    
    Input:
    driver: selenium.driver, driver used to navigate web pages.
    elem: selenium.WebElement, WebElement of a single job posting.
    """

    # Move navigator to relevant job posting
    action = ActionChains(driver)
    action.move_to_element(elem).perform()

    # Acquiring id for corresponding job posting
    _id = get_id(elem)

    # Acquiring list of skills
    _skills = get_skills(driver)

    # If no skills provided, exit function
    if _skills == False:
        return 

    _df = pd.DataFrame({'id': [_id for x in range(len(_skills))], \
                        'skills': _skills})

    return(_df)

def generate_all_skill_df(driver, elems):
    """
    Testing function for generating and concatenating dataframe for skills in whole page.
    """
    df_list = []
    for elem in elems:
        _df = generate_skill_df(elem)
        df_list.append(_df)
    
    df_list = [df for df in df_list if ~isinstance(df, type(None))]
    return pd.concat(df_list)

def set_execute(func):
    """
    Helper function to set function to auto execute.
    Functions set to auto execute will be run immediately after instance of linkedin_soup
    has been create
    
    Input: function
    Output: function
    """
    func.execute = True
    return func


class linkedin_soup(object):
    """
    Class for processing BeautifulSoup object of linkeding job posting pages.
    Method include scraping job titles, company type, salary, skills required and job description.
    """

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
        try: 
            emp_comp = [string for string in [match.find(string=re.compile(".*employees.*")) 
                                    for match in insight] if string][0]
        except IndexError:
            self.employee = np.nan
            self.company_type = np.nan
            return
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

def scrape_page(driver, pbar = None):
    """
    Helper function to scrape all job posting in a single Linkedin job posting
    page. Utilized Class of linkedin_soup

    Input: selenium.driver, driver used to navigate web pages.
    Output: tuple, tuple containing dataframe containing skill information and job details.
    """
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, 
    #                         "//ul[contains(@class, 'scaffold-layout__list-container')]")))

    # Wait until page is fully loaded
    time.sleep(30)

    # Acquiring WebElement of all job posting existing on page.
    job_elems = get_job_elems(driver)

    # Instantiating empty list to contain dataframe generated for each job posting.
    skill_dfs = []
    job_dfs = []

    # Scraping information for each job posting
    for elem in job_elems:

        # Moving cursor to corresponding job posting to avoid error in Webelement not 
        # correctly clicked.
        action = ActionChains(driver)
        action.move_to_element(elem).perform()
        elem_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(elem))
        time.sleep(0.2)
        try:
            elem_button.click()
        except:
            elem_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(elem))
            elem_button.click()

        # Wait until job posting correctly loaded
        # Either 'apply' or 'already applied' button should appear
        try:
            WebDriverWait(driver, 40, ignored_exceptions=StaleElementReferenceException).until(EC.element_to_be_clickable((By.XPATH, 
                                        "//div[contains(@class, 'jobs-apply-button')]//button")))
        except TimeoutException:
            WebDriverWait(driver, 40, ignored_exceptions=StaleElementReferenceException).until(EC.presence_of_element_located((By.XPATH, 
                                        "//div[contains(@class, 'feedback--success')]")))
        
        # Populating dataframe of skills and job details
        skill_dfs.append(generate_skill_df(driver, elem))
        _soup = bs(driver.page_source, features="html.parser")

        # Initiating linkedin_soup instance for scraping job details
        _linkedin_soup = linkedin_soup(_soup)
        job_dfs.append(_linkedin_soup.generate_df())

        # Updating progress bar if available
        if not isinstance(pbar, type(None)):
            pbar.update(1)

    return (pd.concat(skill_dfs, ignore_index=True), pd.concat(job_dfs, ignore_index=True))

def scrape_pages(driver, page_num = 40):
    skill_dfs = []
    job_dfs = []


    with tqdm(total=page_num * 25, position=1, leave=True) as pbar:
        with tqdm(range(1, page_num + 1), position=0, leave=True, ncols = 1, 
                    bar_format = "{l_bar}|{bar}") as page_bar:
            for page in page_bar:
                page_bar.set_description(f"Page {page}/{page_num}")
                if page != 1:
                    driver.refresh()
                WebDriverWait(driver, 50, ignored_exceptions=StaleElementReferenceException).until(EC.element_to_be_clickable((By.XPATH, 
                                            f"//button[contains(@aria-label, 'Page {page}')]")))

                page_button = driver.find_element(By.XPATH, f"//button[contains(@aria-label, 'Page {page}')]")
                action = ActionChains(driver)
                action.move_to_element(page_button)
                page_button.click()

                time.sleep(15)

                _skill_df, _job_df = scrape_page(driver, pbar)

                skill_dfs.append(_skill_df)
                job_dfs.append(_job_df)

    # except Exception as err:
    #     print(f"Error encountered: {err=}")
    # finally:
    return (pd.concat([df for df in skill_dfs if ~isinstance(df, type(None))], ignore_index=True), \
            pd.concat([df for df in job_dfs if ~isinstance(df, type(None))], ignore_index=True))
