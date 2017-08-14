
# coding: utf-8

# In[1]:

import selenium
from bs4 import BeautifulSoup
import re
import requests
from selenium.webdriver import PhantomJS
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from fake_useragent import UserAgent
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.common.
import string
from selenium.common.exceptions import TimeoutException
import nltk
from itertools import zip_longest
import pymysql
import itertools


# In[2]:

from abc import abstractmethod,ABC

class Scraper(ABC):
    
    
    def __init__(self,start_link,dynamic=False):
            
        self.browser = self.get_crawler(dynamic)
        self.db_executer = self.connect_to_database() 
        self.start_link = start_link
        self.temporary_memory = set() 
        
    
    def connect_to_database(self):
        global conn
        conn = pymysql.connect(host='35.198.176.76', user='root', passwd=None, db='mysql', charset='utf8')
        cur = conn.cursor()
        cur.execute("USE definitions")
        return cur
    
    
  
    
    
    def get_crawler(self,dynamic):
        crawler = None
        if(dynamic):
            crawler = PhantomJS("/Users/mac/Desktop/Web scraping/phantomjs-2.1.1-macosx/bin/phantomjs")
        return crawler
  

    @abstractmethod
    def scraping_strategy(self):
        pass
    
    
    def insert_to_database(self,row):
    
            term,definition,example = row
            
            cur = self.db_executer
            cur.execute("SELECT definitions,examples FROM terms WHERE term = '{}'".format(term))
            res=cur.fetchall()
            print(res)
            if(len(res)>0):
                
                cur.execute("UPDATE terms SET definitions = '{0} #$ {1}',examples = '{2} #$ {3}'".format(res[0][0], definition ,result[0][1],example))
            else:
                query = "INSERT into terms (term,definitions,example) VALUES ('{0}','{1}','{2}')".format(term,definition,example)
                print(query)
                cur.execute(query)
            
            conn.commit()
        
    def finalize():
        conn.close()
    
    def find_pos_tag(self,sentence,needed_word):
        tokenizer = nltk.word_tokenize 
        pos_tags = nltk.pos_tag(tokenizer(sentence))
        needed_tag = [y for x,y in pos_tags if x==needed_word]
        return needed_tag
        
    
    
    
    


# In[8]:

class VocabularyScraper(Scraper):
    
    def __init__ (self,*args,**kwargs):
        super(self.__class__,self).__init__(*args,**kwargs)
        
    def preprocess_exs_defs(self):
        webdriver=self.browser
        definitions = list(itertools.chain(*[webdriver.find_elements_by_class_name(name) for name in ["short","long","definition"]]))
        examples = webdriver.find_elements_by_css_selector(".wordPage .example")          
        examples = " #$ ".join(["&{0}& {1}".format(self.find_pos_tag(example.text,term),example.text) for example in examples])
        examples = [example.replace("'",'"') for example in examples]
        definitions = [definition.replace("'",'"') for definition in definitions]
        definitions = " #$ ".join([definition.text for definition in definitions])
        row = tuple((term,definitions,examples))
        return row
      
    
    def preparation(self,key):
        webdriver = self.browser
        webdriver.get(self.start_link)
        search_field = webdriver.find_element_by_id("search")
        search_field.clear()
        search_field.send_keys(key)
        #search_field.send_keys(Keys.ENTER)
        
        WebDriverWait(webdriver,20).until(EC.presence_of_element_located((By.CLASS_NAME,"entry"))) 
        
    
    def scraping_strategy(self):   
        
        self.preparation("a")
        scraped = self.temporary_memory
        webdriver = self.browser
        
        #Just to initialize for checking 
        clicked = set((0,1))
    
        words = set()
        
        while(len(clicked  - words)!=0):
            
            words = set(webdriver.find_elements_by_css_selector(".autocomplete .word"))
            clicked = clicked | words
        
            for word in words:
                term = word.text
                if term not in scraped:
                    word.click()
                    print(term)
                    
                    scraped.add(term)
                    webdriver.save_screenshot("test1.png")
                    row = self.preprocess_exs_defs()
                    print(row)
                    self.insert_to_database(row)
                    time.sleep(1)
                    
                    if(len(scraped)>3):
                        print(scraped)
                        break
                
        
            div = webdriver.find_element_by_class_name("hasmore")
            webdriver.execute_script("arguments[0].scrollTop += arguments[0].scrollHeight",div)

  
        
test=VocabularyScraper("https://www.vocabulary.com/dictionary/",dynamic=True)


# In[39]:

string.ascii_lowercase


# In[207]:

import pymysql
import re
import pandas.io.sql



try:
    conn = pymysql.connect(host='35.198.176.76', user='root', passwd=None, db='mysql', charset='utf8')
    cur = conn.cursor()
    
    queries=["USE definitions",             "INSERT  into terms (term,definitions,examples) VALUES ('sophisticated','very subtly',             'sophisticated work')",             "SELECT * FROM terms"]
    
    query = [cur.execute(query) for query in queries]
   
    result=(cur.fetchall())
    conn.commit()
    #pandas.io.sql.read_sql("USE definitions;",conn)
          
finally:
    cur.close()
    conn.close()


# In[208]:

result


# In[9]:

test.scraping_strategy()


# In[ ]:



