#!/usr/bin/env python3
""" Script to build and populate Ben Jones database """
# pylint: disable=line-too-long

import csv
import datetime
import logging
import requests
import urllib3
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

def write_header(line):
    with open('products_import.csv', 'w') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(line)
    return

def write_line(line):
    with open('products_import.csv', 'a+') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(line)
    return

def get_categories():
    """ Get categories """
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    if response.status_code != 200:
        raise RuntimeError('GET /categories/ {}'.format(response.status_code))
    for category in response.json():
        get_category(category['cid'], category['name'])

def get_category(category_id, category_name):
    """ Get machines from a category """
    PARAMS_DICT.update({'cid': category_id})
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    for machine in response.json():
        get_machine(machine['mid'], category_id, category_name)

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

def get_machine(machine_id, category_id, category_name):
    """ Get machine details """
    PARAMS_DICT.update({'mid': machine_id})
    machine_info = requests.get(MACHINE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    machine_csv = []
    machine_csv.append("simple") # Type
    for machine in machine_info.json():
        machine_csv.append(machine['mid']) # SKU
        logging.debug(f"Machine ID: {machine['mid']}")
        if machine['name'] is None: # Name
            machine_csv.append('Unknown')
        else:
            machine_csv.append(machine['name'])
        logging.debug(f"Machine name: {machine['name']}")
        machine_csv.append(1) # Published
        machine_csv.append(0) # Is Featured
        machine_csv.append("visible") # Visibility in catalog
        machine_csv.append(machine['descr']) # Description
        logging.debug(f"Machine description: {machine['descr']}")
        machine_csv.append("taxable") # Tax status
        machine_csv.append(1) # In stock?
        machine_csv.append(0) # Backorders allowed?
        machine_csv.append(0) # Sold individually
        machine_csv.append(0) # Allow customer reviews
        machine_csv.append(machine['price']) # Regular price
        logging.debug(f"Machine price: {machine['price']}")
        machine_csv.append(category_name.title()) # Categories
        logging.debug(f"Machine category: {category_name.title()}")
    machine_pics = requests.get(PICTURE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    picture_list = []
    try:
        for picture in machine_pics.json():
            root, ext = os.path.splitext(picture['name'])
            if not ext:
                ext = '.jpg'
                picture_list.append("https://benjones.com/machines/" + picture['name'] + ext)
            else:
                picture_list.append("https://benjones.com/machines/" + picture['name'])
    except StopIteration:
        pass
    machine_vids = requests.get(VIDEO_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    try:
        for video in machine_vids.json():
            picture_list.append(video['link'])
    except StopIteration:
        pass
    if picture_list:
        import_pics = ', '.join(picture_list)
        machine_csv.append(import_pics) # Images
    else:
        machine_csv.append('')
    logging.debug(f"Machine pictures: {picture_list}")
    machine_csv.append(0) # Position
    if machine['mfg'] is None: # Brand
        machine_csv.append('Unknown')
    else:
        machine_csv.append(machine['mfg'].title())
    logging.debug(f"Machine manufacturer: {machine['mfg']}")
    machine_csv.append(machine['notes'] or ' ') # _pans_ta
    logging.debug(f"Machine notes: {machine['notes']}")
    machine_csv.append(machine['cost'] or '0') # _wc_cog_cost
    machine_csv.append(machine['owned'] or '0') # _bjm_owned
    machine_csv.append(machine['rigging'] or '0') # _wc_cor_cost
    machine_csv.append(machine['sold']) # _bjm_sold
    machine_csv.append(inventory_status(machine['sold'])) # In stock?
    write_line(machine_csv)

header_line = ["Type","SKU","Name","Published","Is featured?","Visibility in catalog","Description","Tax status","In stock?","Backorders allowed?","Sold individually?","Allow customer reviews?","Regular price","Categories","Images","Position","Brand","Meta: _pans_ta","Meta: _wc_cog_cost","Meta: _bjm_owned","Meta: _wc_cor_cost","Meta: _bjm_sold","In Stock?"]
write_header(header_line)
get_categories()
