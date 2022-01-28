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
logging.basicConfig(filename='update_contacts.log', filemode='w', format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL)

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
    """ Get all machines """
    machine_info = requests.get(GET_IT_ALL, params=PARAMS_DICT, verify=VERIFY_SSL)
    json_data = machine_info.json()
    for machine in json_data:
        machine_json = {'type': 'simple'} # Type
        if machine['origid'] is None:
            new_sku = int(machine['mid']) + 50000
            machine_json['sku'] = str(new_sku)
        else:
            new_sku = machine['origid']
            machine_json['sku'] = str(new_sku)
        if int(new_sku) > 58017:
            meta_list = []
            meta_list.clear()
            if machine['contact'] is not None:
                if not isinstance(machine['contact'], (int, float)) and len(machine['contact']) > 0:
                    if machine['contact'][0]['contact'] is not None:
                        contact = machine['contact'][0]['contact']
                        clean_contact = contact.replace(", ,", "")
                        clean_contact = clean_contact.replace(" No Company", "")
                        bjm_contact = {"key": "_bjm_contact", "value": clean_contact}
                        meta_list.append(dict(bjm_contact))
            machine_json['meta_data'] = meta_list
            logging.info(f"Contact info for SKU {machine_json['sku']}:")
            logging.info(f"    - {machine_json['meta_data']}")
            product_search = f"products?sku={new_sku}"
            item_info = wcapi.get(product_search).json()
            # if len(item_info) >= 0 and item_info[0]['id'] > 66987:
            # if len(item_info) >= 0:
            if len(item_info) >= 0 and item_info[0]['id'] is not None:
                logging.info(f"    - {item_info}")
                print(f"Updating item: {item_info[0]['id']}")
                update_item = f"products/{item_info[0]['id']}"
                result = wcapi.put(update_item, machine_json)
                if result.status_code > 202:
                    logging.error(json.dumps(machine_json))
                    logging.error(f"Result status: {result.status_code}")
                    logging.error(f"Result text: {result.text}")
                else:
                    logging.info(json.dumps(machine_json))
        else:
            logging.info(f"Skipping {new_sku}")

get_machines()
