from bs4 import BeautifulSoup, SoupStrainer
import httplib2
import os
import requests
from urllib.parse import urlparse
import urllib.parse
import getpass
import re

URLS = {"Parallel Programming" : "https://spcl.inf.ethz.ch/Teaching/2020-pp/",
        "Algorithmen und Wahrscheinlichkeit" : "https://www.cadmo.ethz.ch/education/lectures/FS20/AW/index.html",
        "Analysis I" : "https://metaphor.ethz.ch/x/2020/fs/401-0212-16L/",
        "Analysis I/Battilana" : "https://battilana.uk/analysis-i-fs20/",
        "Digitec/Labs" : "https://safari.ethz.ch/digitaltechnik/spring2020/doku.php?id=labs",
        "Digitec/Lectures" : "https://safari.ethz.ch/digitaltechnik/spring2020/doku.php?id=schedule"}

SORT_BY = {r"AW_T(\d)+" : "Serie", "Minitest" : "Ministests", "Lecture" : "Lectures", "solution" : "Solutions",
            "Loesung" : "Solutions", "Note" : "Lecture Notes", "Serie" : "Serie",
            r"PP-L(\d)+" : "Lectures", r"lec(\d)+" : "Lectures", r"L(\d)+" : "Lectures", "exercise" : "Exercises", "assignment" : "Exercises"}

auth = None

def download(links):
    for dir in links:
        for link in links[dir] :
            head = requests.head(link, allow_redirects=True, auth=auth)
            if "Content-Disposition" in head.headers.keys():
                filename = re.findall("filename=(.+)", head.headers["Content-Disposition"])[0].replace("\"", "").replace(";", "")
            else:
                filename = link[link.rfind("/")+1:].replace("%20", " ")
            filename = dir + "/" + sortBy(filename) + filename

            if not os.path.isfile(filename):
                response = requests.get(link, allow_redirects=True, auth=auth)

                if(response.status_code == 200):
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    with open(filename, 'wb') as fd:
                        fd.write(response.content)

                        # add file to the list of downloaded objects
                        fd.close
                        print(filename)
                else:
                    print("Url: {}, Response: {}".format(link, response))


def checkLink(link):
    if (link[-4:] == ".pdf") or (link[-4:] == ".zip") or (link[-5:] == ".docx"):
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

def sortBy(filename):
    for match in SORT_BY.items():
        if len(re.findall(match[0], filename)) > 0:
            return match[1] + "/"
    return ""

userName = input("Username: ")
if (userName != ""):
    userPassword = getpass.getpass()
    auth = (userName, userPassword)

print("Starting...")
links = getLinks(URLS)
download(links)
