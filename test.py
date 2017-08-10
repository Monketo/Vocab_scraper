import re
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup



response = urlopen("http://www.pythonchallenge.com/pc/def/ocr.html")
bsObj=BeautifulSoup(response)



