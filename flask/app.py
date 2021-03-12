from flask import Flask, jsonify, request
import json

# needed to import from lstore
import sys
sys.path.append('../')

from lstore.db import Database
from lstore.query import Query

'''
json_object = '{"sid":100, "grades": [15,10,8,17]}'
'''

app = Flask(__name__)

db = Database()
db.open('../ECS165')
grades_table = db.create_table('Grades', 5, 0)
query = Query(grades_table)

'''
@app.route('/')
def hello():
    return "Hello, World!"
'''

@app.route('/insert', methods=['POST'])
def insert():
    record = request.get_json()

    if record is None:
        print("Could not parse json Object")
        return 'None', 200

    # convert json object to dict
    insert_success = query.insert(record["sid"], record["grades"][0], record["grades"][1], record["grades"][2], record["grades"][3])
    
    ret = "Inserted SID " + str(record["sid"]) + " successfully"

    return ret, 200

@app.route('/delete', methods=['POST'])
def delete(sid):
    query.delete(sid)
    return 'None', 200

@app.route('/select', methods=['GET'])
def select(sid):
    record = query.select(sid, 0, [1,1,1,1,1])
    if not record:
        return 'None', 200
    
    # convert record into json and send
    ret = {
        "sid": sid,
        "grades": [record.user_data[1], record.user_data[2], record.user_data[3], record.user_data[4]]
    }
    json_ret = json.dumps(ret)

    return json_ret, 200

app.run()
