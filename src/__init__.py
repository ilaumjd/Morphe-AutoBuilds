import os
import logging
from curl_cffi import requests
from curl_cffi.requests.impersonate import DEFAULT_CHROME
from github import Github

session = requests.Session(impersonate=DEFAULT_CHROME)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Env Vars
github_token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')

# APKmirror base url
base_url = "https://www.apkmirror.com"

if github_token:
    logging.info("GitHub token detected; using authenticated GitHub API client")
    gh = Github(github_token)
else:
    if os.getenv("CI"):
        logging.warning("No GITHUB_TOKEN/GH_TOKEN detected in CI; GitHub release lookups may fail")
    else:
        logging.warning("No GitHub token detected; using anonymous GitHub API client")
    gh = Github()
