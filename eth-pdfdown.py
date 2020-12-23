#!/usr/bin/python3
from bs4 import BeautifulSoup
import httplib2
import os
import requests
from urllib.parse import urlparse
import urllib.parse
import getpass
import re
import argparse
import json
from tqdm import tqdm
import multiprocessing
from multiprocessing import Pool
from xdg import XDG_CONFIG_HOME

# Configuration variables
CONFIG = {"DOWNLOAD_DIR" : "", "URLS" : {}, "SORT_BY" : {}}
CONFIG_FILE_PATH = os.path.join(XDG_CONFIG_HOME, "ethpdfdown.json")
EXTENSIONS = ["pdf", "docx", "doc", "zip", "tar", "pptx", "ppt"];

# Auth session
auth = None

# Parser setup
parser = argparse.ArgumentParser(description="Script to download and sort lecture documents")
parser.add_argument("-d", "--set-directory", nargs=1, metavar="DIRECTORY", help="set download directory")
parser.add_argument("-u", "--add-url", nargs=2, metavar=("NAME", "URL"), help="add new lecture url")
parser.add_argument("-s", "--add-subdir", nargs=2, metavar=("REGEX", "SUBDIR"), help="add new regex matched subdirectory")
args = parser.parse_args()

# Load config file
def loadConfig():
    global CONFIG
    if not os.path.isdir(os.path.dirname(CONFIG_FILE_PATH)): os.mkdir(".config/")
    if os.path.isfile(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as configFile:
            CONFIG = json.load(configFile)
    else: writeConfig()

# Write config file
def writeConfig():
    with open(CONFIG_FILE_PATH, "w+") as configFile:
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

# Download files
def download(links):
    for dir in links:
        print("\n{}:".format(dir))
        pbar = tqdm(links[dir])
        for link in pbar:
            response = requests.get(link, allow_redirects=True, auth=auth)

            # Check if the header contains the filename
            if "Content-Disposition" in response.headers.keys():
                filename = re.findall("filename=(.+)", response.headers["Content-Disposition"])[0].replace("\"", "").replace(";", "")
            # Otherwise derive it from the URL
            else:
                filename = link[link.rfind("/")+1:].replace("%20", " ")

            # Create absolute path based on configured download directory
            filePath = os.path.join(CONFIG["DOWNLOAD_DIR"], dir, sortBy(filename), filename)

            if (response.status_code == 200):
                os.makedirs(os.path.dirname(filePath), exist_ok=True)
                with open(filePath, 'wb') as fd:
                    fd.write(response.content)
                    fd.close
            elif (response.status_code == 401):
                tqdm.write("{}: access restricted.".format(filename))
            elif (response.status_code == 404):
                pass
                tqdm.write("{}: not found.".format(filename))
            else:
                pass
                tqdm.write("Url: {}, Response: {}".format(link, response))

# Check if file to download exists in dir
def checkExist(dir, link):
    # Request only head to chek if file already exists
    head = requests.head(link, allow_redirects=True, auth=auth)
    # Check if the header contains the filename
    if "Content-Disposition" in head.headers.keys():
        filename = re.findall("filename=(.+)", head.headers["Content-Disposition"])[0].replace("\"", "").replace(";", "")
    # Otherwise derive it from the URL
    else:
        filename = link[link.rfind("/")+1:].replace("%20", " ")

    # Create absolute path based on configured download directory
    filePath = os.path.join(CONFIG["DOWNLOAD_DIR"], dir, sortBy(filename), filename)

    # Download if the file does not exist
    return not os.path.isfile(filePath)

# Remove links to file that already exist
def removeDownloaded(links):
    POOL = Pool(multiprocessing.cpu_count())
    for dir in links:
        links[dir] = [link for link, keep in zip(links[dir], POOL.starmap(checkExist, [(dir, l) for l in links[dir]])) if keep]
    return links

# Check if link points to a document
def checkLink(link):
    for ext in EXTENSIONS:
        if link.endswith(ext): return True
    return False

# Scrape site dict for links and return dict of directory and link combos
def getLinks(sites):
    links = {}

    for site in sites.items():
        url = site[1]
        dir = site[0]

        response = requests.get(url, auth=auth, headers={'User-Agent': 'Custom'})

        links[dir] = []

        for link in BeautifulSoup(response.text, "html.parser").findAll('a', href=True):
            href = link['href'].replace(" ", "%20")
            if not (href[:4] == "http"):
                href = urllib.parse.urljoin(url, href)
            if checkLink(href):
                links[dir].append(href)
    return removeDownloaded(links)

# Check if filename matches subdirectory rule
def sortBy(filename):
    for match in CONFIG["SORT_BY"].items():
        if re.search(match[0], filename) != None:
            return match[1]
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
        if (CONFIG["DOWNLOAD_DIR"] == ""): print("Downloading to current directory.")
        else: print("Donwloading to", CONFIG["DOWNLOAD_DIR"])

        userName = input("Username: ")
        if (userName != ""):
            userPassword = getpass.getpass()
            auth = (userName, userPassword)

        print("\nDownloading files...")
        links = getLinks(CONFIG["URLS"])
        download(links)
