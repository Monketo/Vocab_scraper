# coding: utf-8

# In[3]:
import sys
import re
from selenium.webdriver import PhantomJS
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
import nltk
import pymysql
from pymysql import InternalError, ProgrammingError
import itertools
from http.client import RemoteDisconnected
import http
import urllib

# In[4]:

from abc import abstractmethod, ABC


class Scraper(ABC):
    def __init__(self, start_link, dynamic=False):

        self.browser = self.get_crawler(dynamic)
        self.db_executer = self.connect_to_database()
        self.start_link = start_link
        self.temporary_memory = set()
        if(len(sys.argv)<3):
            self.end_point=0
        else:
            self.end_point = int(sys.argv[2])

    def connect_to_database(self):
        global conn
        global cur
        conn = pymysql.connect(host='35.198.176.76', user='root', passwd=None, db='mysql', charset='utf8')
        cur = conn.cursor()
        cur.execute("USE definitions")
        return cur

    def get_crawler(self, dynamic):
        crawler = None
        if (dynamic):
            crawler = PhantomJS()
        return crawler

    @abstractmethod
    def scraping_strategy(self):
        pass

    def insert_to_database(self, row):

        term, definition, example = row
        if example is None:
            example = ""

        cur = self.db_executer
        cur.execute("SELECT definitions,examples FROM terms WHERE term = '{}'".format(term))
        res = cur.fetchall()
        try:
            examples_alr = res[0][1]
            definitions_alr = res[0][0]
        except IndexError:

            examples_alr = ""
            definitions_alr = ""

        if len(definitions_alr) > 1:
            definitions_alr = [defin.replace("'", "`") for defin in definitions_alr]
            definitions_alr = "".join(definitions_alr)

        print("Already in database - ", res)

        try:
            if (len(res) > 0):

                if definition not in res[0][0]:
                    cur.execute(
                        "UPDATE terms SET definitions = '{0} &$ {1}',examples = '{2} &$ {3}' WHERE term = '{4}'".format(
                            definitions_alr, definition, examples_alr, example, term))

            else:
                query = "INSERT into terms (term,definitions,examples) VALUES ('{0}','{1}','{2}')".format(term,
                                                                                                          definition,
                                                                                                          example)
                cur.execute(query)

            conn.commit()
        except ProgrammingError:
            print("Programming Error")
            print(definitions_alr)

    def finalize(self):
        cur.close
        conn.close()

    def find_pos_tag(self, sentence, needed_word):
        pattern = re.compile(r"" + needed_word + r"e?s?", re.M | re.I)
        tokenizer = nltk.word_tokenize
        pos_tags = nltk.pos_tag(tokenizer(sentence))
        needed_tag = [y for x, y in pos_tags if len(re.findall(pattern, x)) > 0]
        try:
            needed_tag = needed_tag[0]
        except IndexError:
            needed_tag = ""
        return needed_tag

    def handle_internal_error(self):
        cur = self.db_executer
        queries = ["SHOW FULL PROCESSLIST"]
        [cur.execute(query) for query in queries]
        results = (cur.fetchall())
        thread_ids = [result[0] for result in results]
        queries = ["KILL " + thrd_id for thrd_id in thread_ids]
        [cur.execute(query) for query in queries]
        self.db_executer = self.connect_to_database


# In[16]:


class VocabularyScraper(Scraper):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


    def preprocess_exs_defs(self, term):
        webdriver = self.browser


        term = term.replace("'", "`")

        definitions = list(itertools.chain(*[webdriver.find_elements_by_css_selector(name) for name in
                                             [".wordPage .blurb .short", ".wordPage .blurb .long",
                                              ".wordPage .definition h3"]]))

        examples = webdriver.find_elements_by_css_selector(".wordPage .example")

        definitions = self.remove_redund_chars(definitions)
        examples = self.remove_redund_chars(examples)

        examples = " &$ ".join(['&%s& %s' % (self.find_pos_tag(example, term), example) for example in examples])

        definitions = " &$ ".join([definition for definition in definitions])

        row = tuple((term, definitions, examples))
        return row

    def remove_redund_chars(self, iterable):

        if iterable is not None:
            filtered = [element.text.replace("'", '`') for element in iterable]
            return filtered

    def enter_search_field(self, key):
        webdriver = self.browser
        search_field = webdriver.find_element_by_id("search")
        search_field.clear()
        search_field.send_keys(key)

        # search_field.send_keys(Keys.ENTER)



        WebDriverWait(webdriver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "entry")))

    def preparation(self, key):

        found = False
        while not found:
            try:
                webdriver = self.browser
                webdriver.get(self.start_link)
                self.enter_search_field(key)
                found = True
            except  TimeoutException:
                print("Exceeded time.. Retrying to get search field")

    def load_more(self):
        webdriver = self.browser
        div = webdriver.find_element_by_class_name("hasmore")
        webdriver.execute_script("arguments[0].scrollTop += arguments[0].scrollHeight", div)

    def scraping_strategy(self):

        try:
            counter = 0
            scraped = self.temporary_memory
            point = self.end_point

            letter = sys.argv[1]
            self.preparation(letter)
            webdriver = self.browser

            # Just to initialize for checking

            while True:
                try:
                    print(counter, " words")
                    self.load_more()
                    counter += 20
                    time.sleep(0.2)
                except NoSuchElementException:
                    break

            words = webdriver.find_elements_by_css_selector(".autocomplete .word")

            if self.end_point != 0:
                words = words[self.end_point:]

                
            time_started1 = time.time()

            term = None

            for index,word in enumerate(words):

                try:

                    term = word.get_attribute("innerHTML")
                    if term not in scraped:
                        scraped.add(term)

                        time_started2 = time.time()
                        word.click()
                        time.sleep(1)

                        print("Term is ", term)

                        row = self.preprocess_exs_defs(term)

                        print(row)

                        self.insert_to_database(row)
                        time_ended = time.time()
                        print("{}s  took to scrape {}".format(round(time_ended - time_started2, 3), term))

                except StaleElementReferenceException:

                    print("Word %s was not loaded into dataset" % term)
                    continue


                except InternalError:
                    print("Trying to handle multiple threading error")
                    self.handle_internal_error()


        except (http.client.HTTPException, RemoteDisconnected, urllib.error.URLError, WebDriverException):
            print("Handling connection error")
            self.end_point = index
            print("Scraping ended on ", index)
            self.scraping_strategy()













                # except ProgrammingError:
                #     print("Programming error")
                #     self.finalize()
                #     self.db_executer = self.connect_to_database()

            time.sleep(.5)


        time_ended = time.time()

        print(
            "Scraping of the letter '{}' was successfuly finished, were scraped {} words , it took it {} seconds".format(
                letter, counter,
                time_ended - time_started1))
        self.finalize()


test = VocabularyScraper("https://www.vocabulary.com/dictionary/", dynamic=True)

# In[17]:

test.scraping_strategy()

