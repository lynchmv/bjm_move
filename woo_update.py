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

CONFIG_FILE = open('db_config.yml', 'r')
CONFIG_DATA = yaml.load(CONFIG_FILE, Loader=yaml.FullLoader)

LOGLEVEL = CONFIG_DATA['log_lvl'].upper()
logging.basicConfig(filename='woo_update.log', filemode='w', format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL)

CATEGORY_URL = 'https://www.old.benjones.com/api/categories.php'
MACHINE_URL = 'https://www.old.benjones.com/api/machines.php'
PICTURE_URL = 'https://www.old.benjones.com/api/pictures.php'
VIDEO_URL = 'https://www.old.benjones.com/api/videos.php'
GET_IT_ALL = 'https://www.old.benjones.com/api/machines_dos.php'
PARAMS_DICT = {'key': CONFIG_DATA['api_key']}

CURRENT_TIME = datetime.datetime.now()

VERIFY_SSL = True

# https://github.com/woocommerce/wc-api-python
wcapi = API(
    url=CONFIG_DATA['woocommerce_store'],
    consumer_key=CONFIG_DATA['consumer_key'],
    consumer_secret=CONFIG_DATA['consumer_secret'],
    version="wc/v3",
    timeout=900,
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

def stock_qty(sold):
    logging.debug(f"Machine sold status for stock quantity: {sold}")
    result = 0
    if sold == '0':
        result = 1
    return result

def active_status(active):
    logging.debug(f"Machine active status: {active}")
    result = 'hidden'
    if active == '1':
        result = 'visible'
    return result

def get_category(category_id):
    """ Get info for a category """
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    for category in response.json():
        if category['cid'] == category:
            return category['name']

def get_brand(brand_name):
    all_brands = wcapi.get("brands").json()
    for brand in all_brands:
        if brand['name'] == brand_name:
            return brand['term_id']

def get_machines():
    """ Get all machines """
    machine_info = requests.get(GET_IT_ALL, params=PARAMS_DICT, verify=VERIFY_SSL)
    # for machine in itertools.islice(machine_info.json(), 10):
    json_data = machine_info.json()
    for machine in json_data:
        machine_json = {'type': 'simple'} # Type
        if machine['origid'] is None:
            new_sku = int(machine['mid']) + 50000
            machine_json['sku'] = str(new_sku)
        else:
            new_sku = machine['origid']
            machine_json['sku'] = str(new_sku)
        if machine['name'] is None: # Name
            machine_json['name'] = 'Unknown'
        else:
            machine_json['name'] = machine['name']
        machine_json['description'] = (machine['descr']) # Description
        machine_json['manage_stock'] = True # Manage stock
        machine_json['stock_status'] = inventory_status(machine['sold']) # In stock?
        machine_json['stock_quantity'] = stock_qty(machine['sold']) # Stock quantity
        machine_json['catalog_visibility'] = active_status(machine['active']) # Catalog visibility
        machine_json['reviews_allowed'] = False # Allow customer reviews
        machine_json['price'] = machine['price'] # Regular price
        machine_json['regular_price'] = machine['price'] # Regular price
        if len(machine['cat']) > 0:
            '''
            +-----+------------------------------+
            | cid | name                         |
            +-----+------------------------------+
            |   8 | Canters & Slabbers           |
            |  17 | Complete Plants & Operations |
            |  25 | Hogs & Wood Grinders         |
            |  29 | Linebars & Infeed Tables     |
            |  33 | Magnets & Metal Detectors    |
            |  42 | Plywood & Veneer Equipment   |
            |  43 | Post & Pole Peelers          |
            |  44 | Power Units & Generators     |
            |  59 | Truck Scales & Dumpers       |
            +-----+------------------------------+
            '''
            bjm_cat_name = machine['cat'][0]['name']
            if bjm_cat_name == 'Canters & Slabbers':
                woo_cat_id = 479
            elif bjm_cat_name == 'Complete Plants & Operations':
                woo_cat_id = 487
            elif bjm_cat_name == 'Hogs & Wood Grinders':
                woo_cat_id = 495
            elif bjm_cat_name == 'Linebars & Infeed Tables':
                woo_cat_id = 499
            elif bjm_cat_name == 'Magnets & Metal Detectors':
                woo_cat_id = 503
            elif bjm_cat_name == 'Plywood & Veneer Equipment':
                woo_cat_id = 512
            elif bjm_cat_name == 'Post & Pole Peelers':
                woo_cat_id = 513
            elif bjm_cat_name == 'Power Units & Generators':
                woo_cat_id = 514
            elif bjm_cat_name == 'Truck Scales & Dumpers':
                woo_cat_id = 529
            else:
                cat_info = wcapi.get("products/categories", params={"search": cgi.escape(machine['cat'][0]['name'])}).json()
                for item in cat_info:
                    woo_cat_id = item['id']
        else:
            cat_info = wcapi.get("products/categories", params={"search": 'Uncategorized'}).json()
            for item in cat_info:
                woo_cat_id = item['id']
        machine_json['categories'] = [ {"id": woo_cat_id} ] # Categories
        machine_pics = machine['pics']
        picture_list = []
        picture_list.clear()
        try:
            for picture in machine_pics:
                root, ext = os.path.splitext(picture['name'])
                if not ext:
                    ext = '.jpg'
                    pic_src = {'src': 'https://www.old.benjones.com/machines/' + picture['name'] + ext}
                    picture_list.append(dict(pic_src))
                else:
                    pic_src = {'src': 'https://www.old.benjones.com/machines/' + picture['name']}
                    picture_list.append(dict(pic_src))
        except StopIteration:
            pass
        machine_vids = machine['vids']
        try:
            for video in machine_vids:
                video_src = {'src': video['link']}
                picture_list.append(dict(video_src))
        except StopIteration:
            pass
        if picture_list:
            machine_json['images'] = picture_list
        if machine['mfg'] is not None: # Brand
            machine_json['brands'] = get_brand(machine['mfg'].title())
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
        notes = machine['notes'] or ' '
        admin_notes = {"key": "_pans_ta", "value": notes}
        meta_list.append(dict(admin_notes))
        cost = machine['cost'] or '0'
        cog_cost = {"key": "_bjm_cost", "value": cost}
        meta_list.append(dict(cog_cost))
        owned = machine['owned'] or 'No'
        bjm_owned = {"key": "_bjm_owned", "value": owned}
        meta_list.append(dict(bjm_owned))
        rigging = machine['rigging'] or '0'
        cor_cost = {"key": "_bjm_rigging", "value": rigging}
        meta_list.append(dict(cor_cost))
        bjm_sold = {"key": "_bjm_sold", "value": machine['sold']}
        meta_list.append(dict(bjm_sold))
        bjm_location = {"key": "_bjm_location", "value": machine['location']}
        meta_list.append(dict(bjm_location))
        machine_json['meta_data'] = meta_list
        product_search = f"products?sku={new_sku}"
        item_info = wcapi.get(product_search).json()
        if len(item_info) > 0:
            print(f"Updating item: {item_info[0]['id']}")
            update_item = f"products/{item_info[0]['id']}"
            result = wcapi.put(update_item, machine_json)
        else:
            print("Adding new item")
            result = wcapi.post("products", machine_json)
        if result.status_code > 202:
            logging.error(json.dumps(machine_json))
            logging.error(f"Result status: {result.status_code}")
            logging.error(f"Result text: {result.text}")
        else:
            logging.info(json.dumps(machine_json))

get_machines()
