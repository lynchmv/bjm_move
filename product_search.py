#!/usr/bin/env python3
""" Script to build and populate Ben Jones database """
# pylint: disable=line-too-long

import datetime
import cgi
import itertools
import json
import logging
import os
import requests
import sys
import urllib3
from woocommerce import API
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = open('local_config.yml', 'r')
CONFIG_DATA = yaml.load(CONFIG_FILE, Loader=yaml.FullLoader)

LOGLEVEL = CONFIG_DATA['log_lvl'].upper()
logging.basicConfig(filename='product_search.log', filemode='w', format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL)

GET_IT_ALL = 'http://benjones.local/api/machines_dos.php'
PARAMS_DICT = {'key': CONFIG_DATA['api_key']}

CURRENT_TIME = datetime.datetime.now()

VERIFY_SSL = False

# https://github.com/woocommerce/wc-api-python
wcapi = API(
    url=CONFIG_DATA['woocommerce_store'],
    consumer_key=CONFIG_DATA['consumer_key'],
    consumer_secret=CONFIG_DATA['consumer_secret'],
    version="wc/v3",
    timeout=900,
    query_string_auth=True
)

def get_machines():
    """ Search all products """
    # product_search = f"products?sku=58030"
    product_search = f"products?sku=98818"
    item_info = wcapi.get(product_search).json()
    print(json.dumps(item_info))

get_machines()
