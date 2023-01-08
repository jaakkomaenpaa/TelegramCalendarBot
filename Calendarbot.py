"""
Calendar app for Telegram
"""

from telegram.ext import Updater, CommandHandler
from datetime import date, timedelta
import sqlite3

API_TOKEN = "token"

YEAR = 2023

updater = Updater(API_TOKEN, use_context=True)
dispatcher = updater.dispatcher

def get_description(update, context, message):

    if message.count('"') != 2:
        update.message.reply_text('Needs quotation marks. Try again.')
        return

    desc_start = message.find('"')
    desc_end = message.rfind('"')

    description = message[desc_start + 1:desc_end]
    return description

def format_date(update, context, date):

    if len(date) < 2:
        update.message.reply_text("Invalid format of date. Try again.")
        return

    day = str(date[0])
    month = str(date[1])

    if len(day) == 1:
        day = "0" + day
    if len(month) == 1:
        month = "0" + month

    formatted_date = f'{YEAR}-{month}-{day}'
    if not is_valid_date(formatted_date):
        update.message.reply_text("Invalid day or month. Try again.")
        return

    return formatted_date

def is_valid_date(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def send_results(update, context, days):

    cursor, table_name = get_table_name(update, context)
    today = date.today()

    match days:
        case -1 :
            cursor.execute(f"SELECT date, description FROM {table_name} "
                   f"WHERE date(date) <= date('{today}') ORDER BY date ASC")
        case 0:
            cursor.execute(f"SELECT date, description FROM {table_name} "
                   f"WHERE date(date) >= date('{today}') ORDER BY date ASC")
        case _:
            cursor.execute(f"SELECT date, description FROM {table_name} "
                           f"WHERE date(date) BETWEEN ('{today}') "
                           f"AND ('{today + timedelta(days=days)}')ORDER BY date ASC")

    results = cursor.fetchall()

    result_list = []

    for result in results:
        resultdate = result[0].split("-")
        month = resultdate[1]
        day = resultdate[2]
        result_string = f"{day}.{month}. {result[1]}"

        result_list.append(result_string)

    if len(result_list) == 0:
        update.message.reply_text("No events matching the criteria.")
        return

    message = "\n".join(result_list)
    update.message.reply_text(message)

    cursor.close()
    database.close()

def start(update, context):


    update.message.reply_text(
        """
        Help window
        
        To add an event, write: 
        '/add <day.month.> <"description">'.
        
        The year is 2023 by default, and the description 
        should not exceed 50 characters.
        The description should be wrapped inside quotation
        marks.
        
        To list all upcoming events, use command /list.
        Or:
        '/list month' to list events for the next 30 days
        '/list week' to list events for the next 7 days
        '/list day' to list events for tomorrow
        '/list past' to list events that have already happened
        
        To remove an event, write either:
        '/remove date <date>', 
        which clears all events from given date,
        '/remove desc <description>', 
        which deletes all events with given description, or:
        '/remove spec <date> <description>', 
        which removes the specific event with given info.
        
        Use command /examples to see an example of each 
        available command.
        
        Use command /help to access this text again.
        """
    )

def examples(update, context):
    update.message.reply_text(
        """
        Example commands:
        
        /add 13.2. "Going to Helsinki"
        
        /list
        /list past
        /list day
        /list week
        /list month
        
        /remove date 13.2.
        /remove desc "Going to Helsinki"
        /remove spec 13.2. "Going to Helsinki"
        """
    )

def get_defaults(update, context):

    database = sqlite3.connect("calendardatabase.db")
    cursor = database.cursor()

    user_id = update.message.from_user.id
    table_name = f"calendar_{user_id}"

    if not user_table_exists(table_name, cursor):
        cursor.execute(f"CREATE TABLE {table_name} ("
                       f"id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       f"date DATE,"
                       f"description VARCHAR(50))")
    return cursor, table_name

def user_table_exists(table_name, cursor):
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    result = cursor.fetchall()
    return len(result) > 0




    """
    TODO: 
    - check if user already has a table, if doesn't create a new one
    - call at the start of every command function
    - return the user id
    """

def add_event(update, context):
    # str maybe
    message = update.message.text

    description = get_description(update, context, message)
    if description is None:
        return

    info = message.split(" ")

    if len(info) < 2:
        update.message.reply_text("Needs a date. Try again.")
        return

    date = info[1].split(".")
    formatted_date = format_date(update, context, date)
    if formatted_date == "":
        return

    if len(description) > 50:
        update.message.reply_text("Description is too long. Try again.")
        return

    try:
        database = sqlite3.connect("calendardatabase.db")
    except sqlite3.Error as e:
        print(f"Error connecting to the database: {e}")
        sys.exit()

    # Create a cursor object
    cursor, table_name = get_defaults(update, context)
    # Insert a row into the table
    try:
        cursor.execute(f"INSERT INTO {table_name} VALUES (NULL, "
                       f"'{formatted_date}', '{description}')")
    except sqlite3.Error as e:
        print(f"Error executing the INSERT INTO statement: {e}")

    # Commit the changes to the database
    try:
        database.commit()
    except sqlite3.Error as e:
        print(f"Error committing the changes to the database: {e}")

    # Close the cursor and the database connection
    cursor.close()
    database.close()

def list_events(update, context):
    info = update.message.text.split(" ")

    if len(info) == 1:
        info.append("default")

    command = info[1]

    match command:
        case "past":
            send_results(update, context, -1)
        case "default":
            send_results(update, context, 0)
        case "day":
            send_results(update, context, 1)
        case "week":
            send_results(update, context, 7)
        case "month":
            send_results(update, context, 30)
        case _:
            update.message.reply_text("Invalid command. Try again.")

def remove_event(update, context):

    cursor, table_name = get_defaults(update, context)

    message = update.message.text
    if len(message) < 2:
        update.message.reply_text("Invalid command. Try again.")
        return

    info = message.split(" ")
    command = info[1]

    if command == "date":

        if len(info) < 3:
            update.message.reply_text("Needs a date. Try again.")
            return
        date = info[2].split(".")
        formatted_date = format_date(update, context, date)
        if formatted_date == "":
            return

        try:
            cursor.execute(f"DELETE FROM {table_name} "
                           f"WHERE date(date) = '{formatted_date}'")
        except sqlite3.Error as e:
            update.message.reply_text(f"Error removing the event: {e}")

    elif command == "desc":

        description = get_description(update, context, message)
        if description is None:
            return
        try:
            cursor.execute(f"DELETE FROM {table_name} "
                           f"WHERE description = '{description}'")
        except sqlite3.Error as e:
            update.message.reply_text(f"Error removing the event: {e}")

    elif command == "spec":
        if len(info) < 4:
            update.message.reply_text("Missing either a date or "
                                      "a description. Try again.")
            return
        description = get_description(update, context, message)
        if description == "":
            return
        formatted_date = format_date(update, context, info[2].split("."))
        if formatted_date == "":
            return

        try:
            cursor.execute(f"DELETE FROM {table_name} "
                           f"WHERE description = '{description}' AND "
                           f"date(date) = '{formatted_date}'")
        except sqlite3.Error as e:
            update.message.reply_text(f"Error removing the event: {e}")

    else:
        update.message.reply_text("Invalid command. Try again.")

    database.commit()

    cursor.close()
    database.close()

dispatcher.add_handler(CommandHandler('add', add_event))
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', start))
dispatcher.add_handler(CommandHandler('list', list_events))
dispatcher.add_handler(CommandHandler('remove', remove_event))
dispatcher.add_handler(CommandHandler('examples', examples))

updater.start_polling()

