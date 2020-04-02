#!/usr/bin/python3
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
import os
import requests
from urllib.parse import urlparse
import urllib.parse
import getpass
import re

CONFIG = {"DOWNLOAD_DIR" : "", "URLS" : {}, "SORT_BY" : {}}

auth = None

parser = argparse.ArgumentParser(description="Script to download and sort lecture documents")
parser.add_argument("-d", "--set-directory", nargs=1, metavar="DIRECTORY", help="set download directory")
parser.add_argument("-u", "--add-url", nargs=2, metavar=("NAME", "URL"), help="add new lecture url")
parser.add_argument("-s", "--add-subdir", nargs=2, metavar=("REGEX", "SUBDIR"), help="add new regex matched subdirectory")
args = parser.parse_args()

def loadConfig():
    if not os.path.isdir(".config/"): os.mkdir(".config/")
    if os.path.isfile(".config/ethpdfdown.json"):
        with open(".config/ethpdfdown.json", "r") as configFile:
            CONFIG = json.load(configFile)
    else: writeConfig()

def writeConfig():
    with open(".config/ethpdfdown.json", "w+") as configFile:
        json.dump(CONFIG, configFile)

def addUrl(dir, url):
    CONFIG["URLS"][dir] = url
    writeConfig()

def addSortRule(reg, subDir):
    CONFIG["SORT_BY"][reg] = subDir
    writeConfig()

def setDownloadDir(dir):
    CONFIG["DOWNLOAD_DIR"] = dir
    writeConfig()

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
        if re.search(match[0], filename) != None:
            return match[1] + "/"
    return ""

if __name__ == "__main__":
    loadConfig()

    hasArgs = False
    for arg in vars(args):
        params = getattr(args, arg)
        if params == None: continue
        else: hasArgs = True

        if (arg == "set_directory"):
            setDownloadDir(params[0])
        elif (arg == "add_url"):
            addUrl(params[0], params[1])
        elif (arg == "add_subdir"):
            addSortRule(params[0], params[1])

    if not hasArgs:
        userName = input("Username: ")
        if (userName != ""):
            userPassword = getpass.getpass()
            auth = (userName, userPassword)

        print("\nDownloading files...")
        links = getLinks(URLS)
        download(links)
