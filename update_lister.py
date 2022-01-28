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
from wordpress import API as WPAPI
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = open('local_config.yml', 'r')
CONFIG_DATA = yaml.load(CONFIG_FILE, Loader=yaml.FullLoader)

LOGLEVEL = CONFIG_DATA['log_lvl'].upper()
logging.basicConfig(filename='update_lister.log', filemode='w', format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL)

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

    # wp_pass="yhuU I4wo EmTP sKjy olua DVFj",
wpapi = WPAPI(
    url=CONFIG_DATA['woocommerce_store'],
    consumer_key='jJd3A1hTTTAfUgZG3wo4NswqxpgkPJKRawOihgSl',
    consumer_secret='BzUwdzPHhtocfJetIdBdngwtkvwTuZzn13fgAeWX',
    api="wp-json",
    version="wp/v2",
    wp_user="wpapiuser",
    wp_pass="8HsFn$OS5PF9%vrJzLgOqeWK",
    oauth1a_3leg=False,
    creds_store="~/.wc-api-creds.json"
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
        # if int(new_sku) > 0:
        if int(new_sku) == 58030:
            meta_list = []
            meta_list.clear()
            if machine['listed'] is not None:
                listed_id = 0
                listed = machine['listed']
                if listed == 'kdickert':
                    listed_id = 4
                if listed == 'edoss':
                    listed_id = 5
                if listed == 'jlichucki':
                    listed_id = 7
                if listed == 'wdickert':
                    listed_id = 11
                if listed == 'ddickert':
                    listed_id = 8
                if listed == 'pperry':
                    listed_id = 9
                if listed == 'jlyndsey':
                    listed_id = 7273
                if listed == 'jposey':
                    listed_id = 7274
                if listed == 'sdegonia':
                    listed_id = 10
                if listed_id == 0:
                    listed_id = 4
                bjm_listed = {"key": "post_author", "value": listed_id}
                meta_list.append(dict(bjm_listed))
            machine_json['meta_data'] = meta_list
            logging.info(f"Listing info for SKU {machine_json['sku']}:")
            logging.info(f"    - {machine_json['meta_data']}")
            product_search = f"products?sku={new_sku}"
            item_info = wcapi.get(product_search).json()
            # if len(item_info) >= 0 and item_info[0]['id'] > 66987:
            # if len(item_info) >= 0:
            if len(item_info) >= 0 and item_info[0]['id'] is not None:
                logging.info(f"    - {item_info}")
                print(f"Updating item: {item_info[0]['id']}")
                update_item = f"posts/{item_info[0]['id']}"
                # update_item = f"products/{item_info[0]['id']}"
                # result = wcapi.put(update_item, machine_json)
                result = wpapi.put(update_item, machine_json)
                if result.status_code > 202:
                    logging.error(json.dumps(machine_json))
                    logging.error(f"Result status: {result.status_code}")
                    logging.error(f"Result text: {result.text}")
                else:
                    logging.info(json.dumps(machine_json))
        else:
            logging.info(f"Skipping {new_sku}")

get_machines()
