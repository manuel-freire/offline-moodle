#!/usr/bin/python3

import requests
from timeit import default_timer as timer
from bs4 import BeautifulSoup

import argparse
import sys, re, json
from pathlib import Path

def utfchar(matchobj):
    return chr(int(matchobj.group(0)[2:], 16))

def main(config_file, output_file):  

    with open(config_file, 'r') as config_f:
        config = json.load(config_f)

    token = config["wstoken"]
    url = config["url"]
    print(f"User {token} @{url}...")

    session = requests.Session();
    prefix = f"wstoken={token}"
    function = "wsfunction=block_recentlyaccesseditems_get_recent_items"
    suffix = "moodlewsrestformat=json"

    start = timer()
    q = f"{url}?{prefix}&{function}&{suffix}"
    print(f"{q} ...")
    r = session.post(q)
    end = timer()

    print(f'--> {r.status_code} in {end - start} seconds') 
    print(f'--> {r.text} <--')
    ru = re.sub(r"\\u[a-f0-9]{4}", utfchar, r.text)
    print(f'--> {ru} <--')
    if (r.status_code != 200):
        raise Exception(f"Bad result: {ru}")      
    try:
        result = json.loads(ru)
    except AttributeError as e:
        print(f"Bad JSON.")
        return

    with open(output_file, 'w', encoding="utf-8") as output_f:
        json.dump(result, output_f, ensure_ascii=False, sort_keys=False, indent=2)

if __name__ == '__main__':	
    parser = argparse.ArgumentParser(description=\
        "Download Moodle assignment for offline correction; and upload feedback to Moodle.")
    parser.add_argument("--config_file", 
            help="Configuration file to use, with credentials. Default is 'config.json'")        
    parser.add_argument("--output_file", 
            help="Where to write the output")             
    args = parser.parse_args()
    
    main(
        args.config_file, 
        args.output_file)
    