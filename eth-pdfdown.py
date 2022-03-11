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

# Auth
auth = None
auth_cookies = None

# Parser setup
parser = argparse.ArgumentParser(description="Script to download and sort lecture documents")
parser.add_argument("--directory", nargs=1, metavar="DIRECTORY", help="Set download directory")
parser.add_argument("-a", "--add-url", nargs=2, metavar=("NAME", "URL"), help="Add new lecture url")
parser.add_argument("-r", "--add-rule", nargs=2, metavar=("REGEX", "SUBDIR"), help="Add new regex matched subdirectory")
parser.add_argument("-d", "--delete", nargs=2, metavar=("[l|r]", "INDEX"), help="Delete lecture or rule")
parser.add_argument("-l", "--list", action='store_true', help='List current letcture URLs')
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

# ETHZ login to get auth cookie
def login_ethz(username, password):
    s = requests.Session()
    s.post("https://ethz.ch/login/j_security_check", headers={"User-Agent":"Custom"}, data={"j_username":username, "j_password":password, "j_validate":True}, allow_redirects=True)

    return s

def addUrl(directory, url):
    CONFIG["URLS"][directory] = url
    writeConfig()

def addSortRule(reg, subDir):
    CONFIG["SORT_BY"][reg] = subDir
    writeConfig()

def setDownloadDir(directory):
    CONFIG["DOWNLOAD_DIR"] = directory
    writeConfig()

def listLectures():
    print("Download directory: " + (CONFIG["DOWNLOAD_DIR"] if CONFIG["DOWNLOAD_DIR"] != "" else "None"))
    print("Lecture URLs:")
    for i, (d, url) in enumerate(CONFIG["URLS"].items()):
        print("\t" + str(i) + ". " + d + ": " + url)
    print("Sorting rules:")
    for i, (rule, d) in enumerate(CONFIG["SORT_BY"].items()):
        print("\t" + str(i) + ". " + rule + ": " + d)

# Download files
def download(links):
    for directory in links:
        print("\n{}:".format(directory))

        dirpath = os.path.join(CONFIG["DOWNLOAD_DIR"], directory)

        creds = None
        if os.path.exists(dirpath) and ".creds" in os.listdir(dirpath):
            with open(os.path.join(dirpath, ".creds"), "r") as credfile:
                credsj = json.load(credfile)
                creds = (credsj["user"], credsj["password"])

        pbar = tqdm(links[directory])
        for link in pbar:
            response = requests.get(link, allow_redirects=True, auth=auth if not creds else creds,
                                    cookies=auth_cookies)

            # Check if the header contains the filename
            # https://stackoverflow.com/questions/37060344/how-to-determine-the-filename-of-content-downloaded-with-http-in-python
            if "Content-Disposition" in response.headers.keys():
                filename = re.findall("filename\*=([^;]+)", response.headers["Content-Disposition"], flags=re.IGNORECASE)
                if not filename:
                    filename = re.findall("filename=([^;]+)", response.headers["Content-Disposition"], flags=re.IGNORECASE)
                if "utf-8''" in filename[0].lower():
                    filename = re.sub("utf-8''", '', filename[0], flags=re.IGNORECASE)
                else:
                    filename = filename[0]

            # Otherwise derive it from the URL
            else:
                filename = link[link.rfind("/")+1:].replace("%20", " ")

            # Create absolute path based on configured download directory
            filePath = os.path.join(dirpath, sortBy(filename), filename)

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

def checkExist(directory, link):
    # Request only head to chek if file already exists
    head = requests.head(link, allow_redirects=True, auth=auth, cookies=auth_cookies)
    # Check if the header contains the filename
    if "Content-Disposition" in head.headers.keys():
        filename = re.findall("filename=(.+)", head.headers["Content-Disposition"])[0].replace("\"", "").replace(";", "")
    # Otherwise derive it from the URL
    else:
        filename = link[link.rfind("/")+1:].replace("%20", " ")

    # Create absolute path based on configured download directory
    filePath = os.path.join(CONFIG["DOWNLOAD_DIR"], directory, sortBy(filename), filename)

    # Download if the file does not exist
    return not os.path.isfile(filePath)

# Remove links to file that already exist
def removeDownloaded(links):
    POOL = Pool(multiprocessing.cpu_count())
    for directory in links:
        links[directory] = [link for link, keep in zip(links[directory], POOL.starmap(checkExist, [(directory, l) for l in links[directory]])) if keep]
    return links

def onedriveDownload (link):
    import base64
    data_bytes64 = base64.b64encode(bytes(link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

# Check if link points to a document
def checkLink(link):
    for ext in EXTENSIONS:
        if link.endswith(ext): return link
    if re.search("https:\/\/polybox.ethz.ch\/", link) != None:
        return (link + "/download")
    elif re.search("https:\/\/1drv.ms\/", link) != None:
        return onedriveDownload(link)
    else: return None

# Scrape site dict for links and return dict of directory and link combos
def getLinks(sites):
    links = {}

    for site in sites.items():
        url = site[1]
        directory = site[0]

        response = requests.get(url, auth=auth, headers={'User-Agent': 'Custom'}, cookies=auth_cookies)

        links[directory] = []

        for link in BeautifulSoup(response.text, "html.parser").findAll('a', href=True):
            href = link['href'].replace(" ", "%20")
            if not (href[:4] == "http"):
                href = urllib.parse.urljoin(url, href)
            if checkLink(href): links[directory].append(checkLink(href))
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
        if not params: continue
        else: hasArgs = True

        if (arg == "directory"):
            setDownloadDir(params[0])
        elif (arg == "add_url"):
            addUrl(params[0], params[1])
        elif (arg == "add_rule"):
            addSortRule(params[0], params[1])
        elif (arg == "delete"):
              if (params[0] == "l"):
                  if (int(params[1]) < len(CONFIG["URLS"])):
                    del CONFIG["URLS"][list(CONFIG["URLS"].keys())[int(params[1])]]
                    writeConfig()
              elif (params[0] == "r"):
                  if (int(params[1]) < len(CONFIG["SORT_BY"])):
                    del CONFIG["SORT_BY"][list(CONFIG["SORT_BY"].keys())[int(params[1])]]
                    writeConfig()
              else: print("Invalid argument " + params[0])
        elif (arg == "list" and params):
            listLectures()

    if not hasArgs:
        if (CONFIG["DOWNLOAD_DIR"] == ""): print("Downloading to current directory.")
        else: print("Donwloading to", CONFIG["DOWNLOAD_DIR"])

        userName = input("Username: ")
        if (userName != ""):
            userPassword = getpass.getpass()
            auth = (userName, userPassword)
            sess = login_ethz(userName, userPassword)
            auth_cookies = sess.cookies

        print("\nDownloading files...")
        links = getLinks(CONFIG["URLS"])
        download(links)
