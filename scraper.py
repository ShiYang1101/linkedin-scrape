from bs4 import BeautifulSoup as bs

import numpy as np
import re


def get_title(soup):
    title_elem = soup.find_all(class_='t-24 t-bold jobs-unified-top-card__job-title')
    assert len(title_elem) == 1, "More than 1 job title found on page!"

    title = title_elem[0].contents[0]
    assert isinstance(title, str)

    return title


def set_execute(func):
    func.execute = True
    return func

class linkedin_soup(object):

    def __init__(self, soup):
        self.soup = soup

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
            self.company =  np.nan

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
        self.employee, self.company = tuple([data.strip() for data in emp_comp.split("·")])

    @set_execute
    def get_salary(self):
        try:
            self.salary = self.soup.find(href='#SALARY').text
        except AttributeError:
            self.salary = np.nan

    @set_execute
    def get_job_desc(self):
        self.job_desc = self.soup.select("div#job-details > span")[0].get_text(separator="\n")
    
    def auto_generate(self):
        for method in dir(self):
            if getattr(getattr(self, method), 'execute', False):
                getattr(self, method)()