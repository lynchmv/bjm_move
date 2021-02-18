#!/usr/bin/env python3
""" Script to build and populate Ben Jones database """
# pylint: disable=line-too-long

import datetime
import json
import logging
import os
import requests
import sys
import urllib3
from woocommerce import API
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = open('db_config.yml', 'r')
CONFIG_DATA = yaml.load(CONFIG_FILE, Loader=yaml.FullLoader)

LOGLEVEL = CONFIG_DATA['log_lvl'].upper()
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL)

CATEGORY_URL = 'https://www.benjones.com/api/categories.php'
MACHINE_URL = 'https://www.benjones.com/api/machines.php'
PICTURE_URL = 'https://www.benjones.com/api/pictures.php'
VIDEO_URL = 'https://www.benjones.com/api/videos.php'
PARAMS_DICT = {'key': CONFIG_DATA['api_key']}

CURRENT_TIME = datetime.datetime.now()

VERIFY_SSL = True

# https://github.com/woocommerce/wc-api-python
wcapi = API(
    url=CONFIG_DATA['woocommerce_store'],
    consumer_key=CONFIG_DATA['consumer_key'],
    consumer_secret=CONFIG_DATA['consumer_secret'],
    version="wc/v3",
    query_string_auth=True
)

def inventory_status(sold):
    logging.debug(f"Machine sold status: {sold}")
    result = "unknown"
    if sold == '0':
        result = "instock"
    if sold == '1':
        result = "onbackorder"
    if sold == '2':
        result = "outofstock"
    logging.debug(f"inventory_status result: {result}")
    return result

def get_brand(brand_name):
    all_brands = wcapi.get("brands").json()
    for brand in all_brands:
        if brand['name'] == brand_name:
            return brand['term_id']

def get_categories():
    """ Get categories """
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    if response.status_code != 200:
        raise RuntimeError('GET /categories/ {}'.format(response.status_code))
    for category in response.json():
        cat_id = wcapi.get("products/categories", params={"search": category['name']}).json()
        for item in cat_id:
            get_category(category['cid'], category['name'], item['id'])

def get_category(category_id, category_name, woo_cat_id):
    """ Get machines from a category """
    PARAMS_DICT.update({'cid': category_id})
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    for machine in response.json():
        get_machine(machine['mid'], category_id, category_name, woo_cat_id)

def get_machine(machine_id, category_id, category_name, woo_cat_id):
    """ Get machine details """
    PARAMS_DICT.update({'mid': machine_id})
    machine_info = requests.get(MACHINE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    machine_json = {'type': 'simple'} # Type
    for machine in machine_info.json():
        machine_json['sku'] = machine['mid']
        if machine['name'] is None: # Name
            machine_json['name'] = 'Unknown'
        else:
            machine_json['name'] = machine['name']
        machine_json['description'] = (machine['descr']) # Description
        machine_json['manage_stock'] = True # Manage stock
        machine_json['stock_status'] = inventory_status(machine['sold']) # In stock?
        machine_json['reviews_allowed'] = False # Allow customer reviews
        machine_json['price'] = machine['price'] # Regular price
        machine_json['categories'] = [ {"id": woo_cat_id} ] # Categories
    machine_pics = requests.get(PICTURE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    picture_list = []
    try:
        for picture in machine_pics.json():
            root, ext = os.path.splitext(picture['name'])
            if not ext:
                ext = '.jpg'
                pic_src = {'src': 'https://benjones.com/machines/' + picture['name'] + ext}
                picture_list.append(dict(pic_src))
            else:
                pic_src = {'src': 'https://benjones.com/machines/' + picture['name']}
                picture_list.append(dict(pic_src))
    except StopIteration:
        pass
    machine_vids = requests.get(VIDEO_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    try:
        for video in machine_vids.json():
            video_src = {'src': video['link']}
            picture_list.append(dict(video_src))
    except StopIteration:
        pass
    if picture_list:
        machine_json['images'] = picture_list
    if machine['mfg'] is not None: # Brand
        machine_json['brands'] = get_brand(machine['mfg'].title())
    meta_list = []
    notes = machine['notes'] or ' '
    admin_notes = {"key": "_pans_ta", "value": notes}
    meta_list.append(dict(admin_notes))
    cost = machine['cost'] or '0'
    cog_cost = {"key": "_wc_cog_cost", "value": cost}
    meta_list.append(dict(cog_cost))
    owned = machine['owned'] or '0'
    bjm_owned = {"key": "_bjm_owned", "value": owned}
    meta_list.append(dict(bjm_owned))
    rigging = machine['rigging'] or '0'
    cor_cost = {"key": "_wc_cor_cost", "value": rigging}
    meta_list.append(dict(cor_cost))
    bjm_sold = {"key": "_bjm_sold", "value": machine['sold']}
    meta_list.append(dict(bjm_sold))
    machine_json['meta_data'] = meta_list
    # print(json.dumps(machine_json))
    result = wcapi.post("products", machine_json)
    if result.status_code > 202:
        print(json.dumps(machine_json))
        print(f"Result status: {result.status_code}")
        print(f"Result text: {result.text}")
        sys.exit("Check the above output for issues")

get_categories()
