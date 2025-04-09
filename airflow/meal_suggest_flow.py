import json
import sqlite3
import random
import os
import dotenv
from pandas import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client
from datetime import datetime, timedelta
# from flask import Flask, jsonify
import requests

app = FastAPI()
# Database setup


# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


global_cache = {}

dotenv.load_dotenv()
account_sid = os.getenv("account_sid")
auth_token = os.getenv('auth_token')

client = Client(account_sid, auth_token)
SENDER_DETAILS_FILE = "/home/prashant.jha/PycharmProjects/pythonProject/opt/airflow/data/twilio_number.txt"
DB_NAME = "food_items.db"
META_DB_NAME = "meta.db"
FILE_PATH = "../airflow/data/menu_items.txt"  # Path to your text file
RECIPIENT_FILE = "/home/prashant.jha/PycharmProjects/pythonProject/opt/airflow/data/recipients.txt"
INCREASE_VALUE = 1  # Value to increase weightage by each day
APP_NAME = "meal_predict"
API_URL = "https://api-inference.huggingface.co/models/facebook/mbart-large-50-many-to-many-mmt"
hugging_face_token = os.getenv("HF_API_KEY")
headers = {"Authorization": f"Bearer {hugging_face_token}"}


def get_template_msg(items):
    template_msg = "Today's menu is: \n {menu_items} \n Enjoy your meal!"
    msg = template_msg.replace("{menu_items}", items)
    return msg


def create_table():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS food_items (
                name TEXT PRIMARY KEY,
                weightage INTEGER,
                original_weightage INTEGER
            )
        ''')

        conn.commit()
        conn.close()

        conn = sqlite3.connect(META_DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_run_details (
                app_name TEXT PRIMARY KEY,
                last_run_time TEXT
            )
        ''')

        cursor.execute('''
            INSERT OR IGNORE INTO last_run_details (app_name, last_run_time)
            VALUES (?, ?)
        ''', (APP_NAME, datetime.now()))
        # read LAST_RUN_TIME from db and assign the value to the variable
        cursor.execute('SELECT last_run_time FROM last_run_details where app_name = ?', (APP_NAME,))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Error creating table: {e}")


def read_food_items(file_path):
    try:
        items = {}
        print(f"Reading file: {file_path}")
        with open(file_path, 'r') as file:
            for line in file:
                # Split by whitespace example "item name" 5
                name, weightage = line.strip().rsplit(' ', 1)
                name = name.strip()
                items[name] = int(weightage)
        return items
    except Exception as e:
        print(f"Error reading file: {e}")
        return {}


def update_database(items):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for name, weightage in items.items():
        # insert if items do not exist
        cursor.execute('''
            INSERT OR IGNORE INTO food_items (name, weightage, original_weightage)
            VALUES (?, ?, ?)
        ''', (name, weightage, weightage))
    conn.commit()
    conn.close()


def select_item():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT name, weightage FROM food_items where weightage = (select max(weightage) from food_items)')
    items = cursor.fetchall()

    if not items:
        return None
    selected_item = random.choice(items)[0]
    return selected_item


def update_last_run_time():
    conn = sqlite3.connect(META_DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE last_run_details
        SET last_run_time = ?
    ''', (datetime.now(),))
    conn.commit()
    conn.close()


def update_weightages(selected_item, increase_value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Reset the selected item's weightage
    cursor.execute('''
        UPDATE food_items
        SET weightage = original_weightage
        WHERE name = ?
    ''', (selected_item,))

    # Increase weightage for non-selected items
    cursor.execute('''
        UPDATE food_items
        SET weightage = weightage + ?
        WHERE name != ?
    ''', (increase_value, selected_item))

    conn.commit()
    conn.close()


def printAllItems():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    menu = []

    cursor.execute('SELECT * FROM food_items order by weightage desc')
    items = cursor.fetchall()

    for name, weightage, original_weightage in items:
        row = {}
        row['name'] = name
        row['weightage'] = weightage
        row['original_weightage'] = original_weightage
        menu.append(row)

    # print(items)
    conn.close()
    return menu


def get_current_menu_from_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    data = {}
    cursor.execute('select name,original_weightage FROM food_items')
    rows = cursor.fetchall()
    for name, original_weightage in rows:
        data[name] = original_weightage
    return data


def delete_items_database(items):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for name in items:
        # insert if items do not exist
        cursor.execute('''
                    delete from food_items where name =?
                ''', (name,))
    conn.commit()
    conn.close()


def update_menu_database(items):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for name, weightage in items:
        # insert if items do not exist
        cursor.execute('''
                update food_items SET original_weightage = ?
                where name =?
            ''', (name, weightage))
    conn.commit()
    conn.close()


@app.put('/menu')
def update_menu():
    old_menu = get_current_menu_from_db()
    new_menu = read_food_items(FILE_PATH)
    update_items = {}
    non_updated_items = []
    for item, weightage in new_menu.items():
        if old_menu.__contains__(item):
            if old_menu[item] == new_menu[item]:
                non_updated_items.append(item)
        else:
            update_items[item] = weightage

    to_be_deleted_items = old_menu.keys() - non_updated_items
    delete_items_database(to_be_deleted_items)
    update_database(update_items)
    return 'updated'


@app.get('/menu')
def get_menu():
    return printAllItems()


@app.get('/suggest_meal/today')
def suggest_meal():
    todays_date = getTodaysDate()
    # if (global_cache.__contains__(todays_date)):
    #     return global_cache[todays_date]

    suggested_meal = {}
    lunch_item = next_meal()
    dinner_item = next_meal()

    suggested_meal["lunch"] = lunch_item
    suggested_meal["dinner"] = dinner_item

    response = {}
    response[todays_date] = suggested_meal
    global_cache[todays_date] = response

    print(f"Selected item: {response}")
    # update cache
    return suggested_meal

@app.get('/suggest_meal/tomorrow')
def suggest_meal_tomorrow():
    todays_date = getTodaysDate()
    # if (global_cache.__contains__(todays_date)):
    #     return global_cache[todays_date]

    suggested_meal = {}
    lunch_item = read_next_meal()
    dinner_item = read_next_meal()

    suggested_meal["lunch"] = lunch_item
    suggested_meal["dinner"] = dinner_item

    response = {}
    response[todays_date] = suggested_meal
    global_cache[todays_date] = response

    print(f"Selected item: {response}")
    # update cache
    return suggested_meal

def getTodaysDate():
    return datetime.now().today().strftime('%d-%m-%Y')


def next_meal():
    selected_item = select_item()
    update_weightages(selected_item, INCREASE_VALUE)
    return selected_item
def read_next_meal():
    selected_item = select_item()
    update_weightages(selected_item, INCREASE_VALUE)
    return selected_item

def force_re_read():
    global LAST_RUN_TIME
    # update last_run in db
    conn = sqlite3.connect(META_DB_NAME)
    cursor = conn.cursor()
    # set last_run_time to current time - 1 year
    last_year_time = datetime.now() - timedelta(days=365)
    cursor.execute('''
        UPDATE last_run_details
        SET last_run_time = ?
    ''', (last_year_time,))
    conn.commit()
    conn.close()


def get_last_run_time():
    conn = sqlite3.connect(META_DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT last_run_time FROM last_run_details where app_name = ?', (APP_NAME,))
    last_run_time = cursor.fetchone()
    conn.close()
    # if last_run is not present in db, set it to current time - 1 year

    if last_run_time is None:
        return datetime.now()
    else:
        # convert string value last_run_time to datetime object
        print(last_run_time)
        last_run_time = datetime.strptime(last_run_time[0], '%Y-%m-%d %H:%M:%S.%f')
        return last_run_time

# update_menu()
# update_last_run_time()
# force_re_read()
# suggest_meal()
# printAllItems()
# if __name__ == "__main__":
#     app.run(debug=True)
