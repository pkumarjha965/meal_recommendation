import sqlite3

DB_NAME = "food_items.db"


def get_meal_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meal_history")
    meal_history = cursor.fetchall()
    conn.close()
    meal_items = {}

    for date, meal_type, item in meal_history:
        if date not in meal_items:
            meal_items[date] = {}
        meal_items[date][meal_type] = item

    print(meal_items)
    return meal_items


def get_meal_history_for_day(date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    meals = {}
    cursor.execute('SELECT date_col, meal_type, item FROM meal_history where date_col = ?', (date,))
    rows = cursor.fetchall()
    for date_col, meal_type, item in rows:
        meals[meal_type] = item
    conn.close()
    return meals