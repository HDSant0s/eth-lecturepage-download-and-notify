from bs4 import BeautifulSoup, SoupStrainer
import httplib2
import pickle
import os
import requests
import ssl
from urllib.parse import urlparse
import urllib.parse
import getpass

URLS = {"Parallel Programming" : "https://spcl.inf.ethz.ch/Teaching/2020-pp/",
        "Algorithmen und Wahrscheinlichkeit" : "https://www.cadmo.ethz.ch/education/lectures/FS20/AW/index.html",
        "Analysis I" : "https://metaphor.ethz.ch/x/2020/fs/401-0212-16L/",
        "Analysis I/Battilana" : "https://battilana.uk/analysis-i-fs20/"}

# URLS = ["https://spcl.inf.ethz.ch/Teaching/2020-pp/",
#         "https://www.cadmo.ethz.ch/education/lectures/FS20/AW/index.html",
#         "https://metaphor.ethz.ch/x/2020/fs/401-0212-16L/"]

usedLinks = []

auth = None

def download(links):
    for dir in links:
        for link in links[dir] :
            response = requests.get(link, allow_redirects=True, auth=auth)
            #print("Url: {}, Respnse:{}".format(url, response))
            if(response.status_code == 200):
                filename = dir + "/" + link[link.rfind("/")+1:].replace("%20", " ")
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'wb') as fd:
                    fd.write(response.content)
                    # add file to the list of downloaded objects
                    usedLinks.append(link)
                    fd.close
                    print(filename)
            else:
                print("Url: {}, Response: {}".format(link, response))


def checkLink(link):
    if (link[-4:] == ".pdf") or (link[-4:] == ".zip"):
        if not (link in usedLinks):
            return True

def getLinks(sites):
    links = {}

    for site in sites.items():
        url = site[1]
        dir = site[0]

        response = requests.get(url, auth=auth)

        links[dir] = []

        for link in BeautifulSoup(response.text, "html.parser", parse_only=SoupStrainer('a')):
            if link.has_attr('href'):
                href = link['href'].replace(" ", "%20")
                if not (href[:4] == "http"):
                    href = urllib.parse.urljoin(url, href)
                if checkLink(href):
                    links[dir].append(href)

    return links

try:
    dmp = open(__file__ + ".dmp", "rb")
    usedLinks = pickle.load(dmp)
except EOFError:
    dmp.close()
    pass
except FileNotFoundError:
    pass
else:
    dmp.close()


userName = input("Username: ")
if (userName != ""):
    userPassword = getpass.getpass()
    auth = (userName, userPassword)

links = getLinks(URLS)
download(links)

dmp = open(__file__ + ".dmp", "wb")
pickle.dump(usedLinks, dmp)
dmp.close()
