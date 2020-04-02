#!/usr/bin/python3
import os
import json
import argparse
import re

CONFIG = {"DOWNLOAD_DIR" : "", "URLS" : {}, "SORT_BY" : {}}

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
        # Run download
        pass
