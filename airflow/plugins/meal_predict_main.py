 import sqlite3
import random
import os

from datetime import datetime, timedelta
# from flask import Flask, jsonify
from messaging_util import get_template_msg, send_sms
from AIUtil import translate_to_hindi

# app = Flask(__name__)
# Database setup
DB_NAME = "food_items.db"
META_DB_NAME = "meta.db"
FILE_PATH = "/opt/airflow/data/menu_items.txt"  # Path to your text file
RECIPIENT_FILE = "/opt/airflow/data/recipients.txt"
INCREASE_VALUE = 1  # Value to increase weightage by each day
APP_NAME = "meal_predict"


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
        ''', (APP_NAME, datetime.now().timestamp()))
        #read LAST_RUN_TIME from db and assign the value to the variable
       # cursor.execute('SELECT last_run_time FROM last_run_details where app_name = ?', (APP_NAME,))

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

    cursor.execute('SELECT * FROM food_items')
    items = cursor.fetchall()
    print(items)
    conn.close()


def init_db():
    create_table()
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        print("MENU FILE NOT FOUND")
        return

    file_mod_time = os.path.getmtime(FILE_PATH)
    last_run_time = get_last_run_time()
    print(f"File modified time: {file_mod_time}")
    print(f"Last run time: {last_run_time}")

    # ensure both the timings are in seconds
    # if last_run_time < file_mod_time:
    print("Updating food items")
    items = read_food_items(FILE_PATH)
    update_database(items)


# @app.route('/suggest_meal', methods=['GET'])
def suggest_meal():
    init_db()

    # # Read and update food items if the file has been modified
    # if os.path.exists(FILE_PATH):
    #     LAST_RUN_TIME = get_last_run_time().timestamp()
    #     file_mod_time = os.path.getmtime(FILE_PATH)
    #     print(f"File modified time: {file_mod_time}")
    #     print(f"Last run time: {LAST_RUN_TIME}")
    #     current_time = datetime.now().timestamp()
    #     print(f"Last run since seconds: {current_time - LAST_RUN_TIME}")
    #     print(f"Last modified since seconds: {current_time - file_mod_time}")
    #
    #     if current_time - file_mod_time < current_time - LAST_RUN_TIME:  # 24 hours in seconds
    #         print("Updating food items")
    #         items = read_food_items(FILE_PATH)
    #         update_database(items)

    selected_item = select_item()
    print(f"Selected item: {selected_item}")
    update_weightages(selected_item, INCREASE_VALUE)
    update_last_run_time()
    printAllItems()

    template_msg = get_template_msg(selected_item)
    translated_msg = translate_to_hindi(template_msg)
    send_notification(translated_msg)
    # return jsonify({"suggested_meal": selected_item})


def send_notification(notification_msg):
    to_numbers = open(RECIPIENT_FILE).read().splitlines()
    for number in to_numbers:
        send_sms(number, notification_msg)
        print(f"Sending notification to number {number}")


def force_re_read():
    global LAST_RUN_TIME
    #update last_run in db
    conn = sqlite3.connect(META_DB_NAME)
    cursor = conn.cursor()
    #set last_run_time to current time - 1 year
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
        return datetime.now().timestamp()
    else:
        # convert string value last_run_time to timestamp
        last_run_time = last_run_time[0]
        #create a timestamp object from the string which is in epoch format
        print(last_run_time)
        # Last run time is date time in string format, convert it to timestamp to millisecond precision
        last_run_time = datetime.strptime(last_run_time, '%Y-%m-%d %H:%M:%S.%f').timestamp()
        return last_run_time

# update_last_run_time()
# force_re_read()
# suggest_meal()
# printAllItems()
# if __name__ == "__main__":
#     app.run(debug=True)

