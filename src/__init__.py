import os
import logging
from curl_cffi import requests
from curl_cffi.requests.impersonate import DEFAULT_CHROME

session = requests.Session(impersonate=DEFAULT_CHROME)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Env Vars
github_token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')

if not github_token:
    logging.warning("No GITHUB_TOKEN/GH_TOKEN detected; GitHub API requests are rate limited")
