from quakefeeds import QuakeFeed
from data_processor import process_data
from datetime import datetime
import os
import sys
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../earthosys_model/model")
from tsunami_predictor import predict_tsunami
from data_processor import get_additional_info

db_file = os.path.dirname(os.path.abspath(__file__)) + "/../../earthosys_site/db.sqlite3"

AUTH_TOKEN = "A1E-Jzxt1BSuMNBTwfRcKt0swcS5pJY2FP"
BASE_URL = "http://things.ubidots.com/api/v1.6/"
TSUNAMI_ID = ""

tsunami_alert = None

def init():
    global tsunami_alert, AUTH_TOKEN, BASE_URL, TSUNAMI_ID
    api = ApiClient(token=AUTH_TOKEN, base_url=BASE_URL)
    tsunami_alert = api.get_variable(TSUNAMI_ID)


def get_feeds():
    init()
    id_buffer, feeds_id = set(), set()
    while True:
        feeds = QuakeFeed("2.5", "day")
        id_buffer = get_ids(feeds) & id_buffer
        for feed in range(len(feeds)):
            if feeds[feed]["id"] not in id_buffer:
                data = []
                id_buffer.add(feeds[feed]["id"])
                magnitude = feeds.magnitude(feed)
                if magnitude >= 4.0:
                    data.append(magnitude)
                    data.append(feeds.depth(feed))
                    data += feeds.location(feed)[::-1]
                    tsunami, region = predict(data)
                    lat, lng = data[2], data[3]
                    additional_info = get_additional_info(lat, lng)
                    try:
                        alert_bot()
                        log_data(data, region, tsunami, additional_info)
                    except Exception as e:
                        print(e)


def alert_bot():
    try:
        _val = tsunami_alert.save_value({"value": 1})
        while _val == 0:
            _val = tsunami_alert.get_values(1)[0]["value"]
        print("Alerted")
    except Exception as e:
        print("Not alerted due to error {}".format(e))


def get_ids(feeds):
    ids = set()
    for feed in feeds:
        ids.add(feed["id"])
    return ids


def predict(data):
    _input = process_data(input_data=data)
    return predict_tsunami([_input]), _input[2]


def log_data(data, region, tsunami, additional_info):
    sql = ''' INSERT INTO feeds_feedprediction(magnitude, depth, latitude, longitude, epicenter, date_time, tsunami, nearest_lat, nearest_lng, distance, location, speed) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '''
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(sql, data + [region, datetime.now(), tsunami, additional_info["nearest_lat"], additional_info["nearest_lng"], additional_info["distance"], additional_info["location"], additional_info["speed"]])
    connection.commit()
    cursor.close()
    connection.close()


def create_connection():
    global db_file
    try:
        connection = sqlite3.connect(db_file)
    except Error as e:
        print(e)
        connection = None
    return connection

if __name__ == "__main__":
    get_feeds()
