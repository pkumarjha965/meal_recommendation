import os
import sqlite3
from datetime import datetime, timedelta

import dotenv
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client

import datahandler

# from flask import Flask, jsonify

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
INCREASE_VALUE = 2  # Value to increase weightage by each day
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

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS meal_history (
                                date_col varchar(10),
                                meal_type varchar(10),
                                item varchar(50),
                                PRIMARY KEY (date_col, meal_type)
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


def reset_menu():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE food_items
        SET weightage = original_weightage
    ''')

    cursor.execute('''
        DELETE FROM meal_history where date_col = ?
    ''', (getTodaysDate(),))

    conn.commit()
    conn.close()


def read_food_items(file_path):
    try:
        items = {}
        print(f"Reading file: {file_path}")
        with open(file_path, 'r') as file:
            for line in file:
                # Split by whitespace example "item name" 5
                if line.strip() == "":
                    continue
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

    cursor.execute(
        'SELECT name, weightage FROM food_items where weightage = (select max(weightage) from food_items) limit 1')
    items = cursor.fetchall()

    if not items or len(items) == 0:
        return None
    selected_item = items[0][0]
    return selected_item


def getTopTwoMeals():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    selected_item = []
    cursor.execute('SELECT name, weightage FROM food_items order by weightage desc limit 2')
    items = cursor.fetchall()

    if not items:
        return None
    for item in items:
        selected_item.append(item[0])
    return selected_item


def getAndUpdateTopTwoMeals():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    selected_item = []
    cursor.execute('SELECT name, weightage FROM food_items order by weightage desc limit 2')
    items = cursor.fetchall()

    if not items:
        return None
    for item in items:
        selected_item.append(item[0])

    update_weightages(selected_item)
    return selected_item


def move_to_meal_history(date, meal_type, item):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('INSERT or REPLACE into meal_history (date_col,meal_type,item) values (?,?,?)',
                   (date, meal_type, item,))
    conn.commit()
    conn.close()


def update_last_run_time():
    conn = sqlite3.connect(META_DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE last_run_details
        SET last_run_time = ?
    ''', (datetime.now(),))
    conn.commit()
    conn.close()


def update_weightages(selected_items):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Convert string into a list.
    if isinstance(selected_items, str):
        selected_items = [selected_items]

    placeholder = ','.join('?' * len(selected_items))

    print(f"Selected items: {selected_items}")
    # Reset the selected item's weightage
    cursor.execute(f'''
        UPDATE food_items
        SET weightage = original_weightage
        WHERE name in ({placeholder})
    ''', (*selected_items,))

    # Increase weightage for non-selected items
    cursor.execute(f'''
        UPDATE food_items
        SET weightage = weightage + ?
        WHERE name not in ({placeholder})
    ''', (INCREASE_VALUE, *selected_items))

    conn.commit()
    conn.close()


def printAllItems():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    menu = []

    cursor.execute('SELECT * FROM food_items order by weightage desc')
    items = cursor.fetchall()

    for name, weightage, original_weightage in items:
        row = {'name': name, 'weightage': weightage, 'original_weightage': original_weightage}
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


@app.put('/api/menu')
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
    print(f"Items to be deleted: {to_be_deleted_items}")
    print(f"Items to be updated: {update_items}")

    delete_items_database(to_be_deleted_items)
    update_database(update_items)

    return 'updated'


@app.on_event("startup")
def startup_event():
    # create the database and tables if they don't exist
    create_table()
    # read food items from file and update the database
    update_menu()
    # force_re_read()
    # force_re_read()
    # update_last_run_time()


@app.get('/api/menu')
def get_menu():
    return printAllItems()


@app.get('/api/reset')
def reset():
    # read food items from file and update the database
    reset_menu()
    # force_re_read()
    # force_re_read()
    # update_last_run_time()
    return 'reset'


@app.get('/api/suggest_meal/today')
def suggest_meal_today():
    todays_date = getTodaysDate()
    # if (global_cache.__contains__(todays_date)):
    #     return global_cache[todays_date]
    print(todays_date)

    suggested_meal = get_next_meals(todays_date)

    response = {}
    response[todays_date] = suggested_meal
    # global_cache[todays_date] = response
    print(f"Selected item: {response}")
    # update cache
    return suggested_meal


@app.get('/api/suggest_meal/tomorrow')
def suggest_meal_tomorrow():
    # todays_date = getTodaysDate()
    # if (global_cache.__contains__(todays_date)):
    #     return global_cache[todays_date]

    #  Pick today's meal first if not picked
    suggest_meal_today()
    suggested_meal = {}
    menu = getTopTwoMeals()

    suggested_meal["lunch"] = menu[0]
    suggested_meal["dinner"] = menu[1]

    # response = {}
    # response[todays_date] = suggested_meal
    # global_cache[todays_date] = response

    # print(f"Selected item: {response}")
    # update cache
    return suggested_meal


@app.get('/suggest_meal')
def suggest_meal():
    # Get the top two meals
    meals = getAndUpdateTopTwoMeals()
    # Create a message with the meal suggestions
    # message = f"Suggested meals for today:\nLunch: {meals[0]}\nDinner: {meals[1]}"
    # print(message)
    # Send the message via Twilio.
    suggested_meal = {"lunch": meals[0], "dinner": meals[1]}
    return suggested_meal


@app.get('/api/meal_history')
def meal_history():
    return datahandler.get_meal_history()


def getTodaysDate():
    return datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m-%Y')

def getTomorrowsDate():
    return (datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days=1)).strftime('%d-%m-%Y')


def get_next_meals(date):
    meals = datahandler.get_meal_history_for_day(date)
    if not meals or len(meals) == 0:
        meals = pick_next_meals()
    return meals


# make this method transactional
def pick_next_meals():
    items = getAndUpdateTopTwoMeals()
    todays_date = getTodaysDate()
    move_to_meal_history(todays_date, 'lunch', items[0])
    move_to_meal_history(todays_date, 'dinner', items[1])
    meals = {}
    meals['lunch'] = items[0]
    meals['dinner'] = items[1]
    return meals

