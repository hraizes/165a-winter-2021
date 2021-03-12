from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import json

# needed to import from lstore
import sys
sys.path.append('../')

from lstore.db import Database
from lstore.transaction import Transaction
from lstore.query import Query

'''
json_object = '{"sid":100, "grades": [15,10,8,17]}'
'''

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

db = Database()
db.open('../ECS165')
grades_table = db.create_table('Grades', 5, 0)
query = Query(grades_table)


@app.route('/transaction', methods=['POST'])
@cross_origin()
def transaction():
    queries = request.get_json()
    if queries is None:
        print("Could not parse json Object")
        return 'None', 200

    transaction = Transaction()
    for query in queries:
        if query["type"] == 'insert':
            transaction.add_query(query.insert(*[query["col1"],query["col2"],query["col3"],query["col4"],query["col5"]]))
        elif query["type"] == 'select':
            transaction.add_query(query.select(query["value"], query["key"], [1, 1, 1, 1, 1]))
        elif query["type"] == 'update':
            transaction.add_query(query.update(query["primarykey"], *[query["col2"],query["col3"],query["col4"],query["col5"]]))
        elif query["type"] == 'delete':
            transaction.add_query(query.delete(query["key"]))
    
    db.batcher.enqueue_xact(transaction)
    db.let_execution_threads_complete()

    return queries, 200

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
