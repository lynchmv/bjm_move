#!/usr/bin/env python
""" Script to build and populate Ben Jones database """
# pylint: disable=line-too-long

import datetime
import requests
import mysql.connector as mysql
import urllib3
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = open('db_config.yml', 'r')
CONFIG_DATA = yaml.load(CONFIG_FILE, Loader=yaml.FullLoader)

CATEGORY_URL = 'https://www.benjones.com/api/categories.php'
MACHINE_URL = 'https://www.benjones.com/api/machines.php'
PICTURE_URL = 'https://www.benjones.com/api/pictures.php'
VIDEO_URL = 'https://www.benjones.com/api/videos.php'
PARAMS_DICT = {'key': CONFIG_DATA['api_key']}

CURRENT_TIME = datetime.datetime.now()

VERIFY_SSL = True

DB = mysql.connect(
        host=CONFIG_DATA['db_host'],
        user=CONFIG_DATA['db_user'],
        passwd=CONFIG_DATA['db_pass'],
        database=CONFIG_DATA['db_name']
)
CURSOR = DB.cursor()

def create_tables(drop_first=0):
    """ Create database tables """
    if drop_first != 0:
        drop_statement = "DROP TABLE IF EXISTS vids"
        CURSOR.execute(drop_statement)
        drop_statement = "DROP TABLE IF EXISTS pics"
        CURSOR.execute(drop_statement)
        drop_statement = "DROP TABLE IF EXISTS machines"
        CURSOR.execute(drop_statement)
        drop_statement = "DROP TABLE IF EXISTS categories"
        CURSOR.execute(drop_statement)

    sql_statement = ("CREATE TABLE IF NOT EXISTS categories ( "
                     "cid INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                     "name varchar(255), "
                     "created_at TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', "
                     "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP "
                     ")")
    CURSOR.execute(sql_statement)

    sql_statement = ("CREATE TABLE IF NOT EXISTS machines ( "
                     "mid INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                     "cid INTEGER NOT NULL, "
                     "scid INTEGER DEFAULT 0, "
                     "pid INTEGER NOT NULL, "
                     "name VARCHAR(255), "
                     "manufacturer VARCHAR(255), "
                     "description LONGTEXT, "
                     "notes LONGTEXT, "
                     "location VARCHAR(255), "
                     "cost DECIMAL(13,2), "
                     "rigging DECIMAL(13,2), "
                     "price DECIMAL(13,2), "
                     "owned TINYINT NOT NULL DEFAULT 0, "
                     "active TINYINT NOT NULL DEFAULT 0, "
                     "featured TINYINT NOT NULL DEFAULT 0, "
                     "pending TINYINT NOT NULL DEFAULT 0, "
                     "sold TINYINT NOT NULL DEFAULT 0, "
                     "listed VARCHAR(255), "
                     "created_at TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', "
                     "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                     "INDEX (cid), "
                     "FOREIGN KEY (cid) REFERENCES categories (cid) "
                     "ON UPDATE CASCADE "
                     ")")
    CURSOR.execute(sql_statement)

    sql_statement = ("CREATE TABLE IF NOT EXISTS pics ( "
                     "pid INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                     "mid INTEGER, "
                     "name VARCHAR(255), "
                     "title VARCHAR(255), "
                     "active TINYINT NOT NULL DEFAULT 0, "
                     "picorder INTEGER, "
                     "created_at TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', "
                     "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                     "INDEX (mid), "
                     "FOREIGN KEY (mid) REFERENCES machines (mid) "
                     "ON UPDATE CASCADE "
                     ")")
    CURSOR.execute(sql_statement)

    sql_statement = ("CREATE TABLE IF NOT EXISTS vids ( "
                     "vid INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                     "mid INTEGER, "
                     "link VARCHAR(255), "
                     "created_at TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', "
                     "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                     "INDEX (mid), "
                     "FOREIGN KEY (mid) REFERENCES machines (mid) "
                     "ON UPDATE CASCADE "
                     ")")
    CURSOR.execute(sql_statement)
    get_categories()

def get_categories():
    """ Get categories """
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    if response.status_code != 200:
        raise RuntimeError('GET /categories/ {}'.format(response.status_code))
    sql_statement = ("INSERT INTO categories VALUES (%s, %s, now(), now()) "
                     "ON DUPLICATE KEY UPDATE updated_at = now()")
    for category in response.json():
        values = (int(category['cid']), category['name'])
        CURSOR.execute(sql_statement, values)
        DB.commit()
        get_category(category['cid'])

def get_category(category_id):
    """ Get machines from a category """
    PARAMS_DICT.update({'cid': category_id})
    response = requests.get(CATEGORY_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    for machine in response.json():
        get_machine(machine['mid'], category_id)

def get_machine(machine_id, category_id):
    """ Get machine details """
    PARAMS_DICT.update({'mid': machine_id})
    machine_info = requests.get(MACHINE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    sql_statement = ("INSERT INTO machines VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                     "%s, %s, %s, %s, %s, %s, %s, %s, %s, now()) ON DUPLICATE KEY "
                     "UPDATE scid = %s, updated_at = now()")
    for machine in machine_info.json():
        machine['pid'] = (0, machine['pid'])[isinstance(machine['pid'], str)]
        values = (int(machine['mid']), int(category_id), int(category_id), int(machine['pid']), machine['name'], machine['mfg'],
                  machine['descr'], machine['notes'], machine['location'], machine['cost'], machine['rigging'],
                  machine['price'], machine['owned'], machine['active'], machine['feat'], machine['pending'],
                  machine['sold'], machine['listed'], machine['added'], int(category_id))
        CURSOR.execute(sql_statement, values)
        DB.commit()
    machine_pics = requests.get(PICTURE_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    try:
        for picture in machine_pics.json():
            sql_statement = f"INSERT INTO pics ( {picture['pid']}, {picture['mid']}, '{picture['name']}', '{picture['title']}', {picture['active']}, {picture['picorder']}, now(), now());\n"
    except StopIteration:
        pass
    machine_vids = requests.get(VIDEO_URL, params=PARAMS_DICT, verify=VERIFY_SSL)
    try:
        for video in machine_vids.json():
            sql_statement = f"INSERT INTO vids ({video['vid']}, {video['mid']}, '{video['link']}', now(), now());\n"
    except StopIteration:
        pass

create_tables(1)
