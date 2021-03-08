from lstore.db import Database
from lstore.query import Query
from lstore.transaction import *
from lstore.helpers import *
import threading

# QUERIES NEED TO BE APPENDED IN ORDER OF INSTANTIATION

def m3_tester():
    path = './MS3'
    clear_database(path)
    db = Database()
    db.open('./MS3')
    grades_table = db.create_table('Grades', 5, 0)
    query = Query(grades_table)

    transaction1 = Transaction()
    query_1 = query.insert(*[1,2,3,4,5])
    query_2 = query.select(1,0,[1, 1, 1, 1, 1])
    query_3 = query.insert(*[6, 7, 8, 9, 10])
    transaction1.queries.append(query_1)
    transaction1.queries.append(query_2)
    transaction1.queries.append(query_3)
    db.batcher.enqueue_xact(transaction1)

    transaction2 = Transaction()
    query_4 = query.insert(*[5, 7, 8, 9, 10])
    transaction2.queries.append(query_4)
    db.batcher.enqueue_xact(transaction2)

    transaction3 = Transaction()
    query_5 = query.insert(*[2, 7, 8, 9, 10])
    query_8 = query.select(2,0,[1, 1, 1, 1, 1])
    transaction3.queries.append(query_5)
    transaction3.queries.append(query_8)
    db.batcher.enqueue_xact(transaction3)

    transaction4 = Transaction()
    query_6 = query.insert(*[3, 7, 8, 9, 10])
    transaction4.queries.append(query_6)
    db.batcher.enqueue_xact(transaction4)

    transaction5 = Transaction()
    query_7 = query.insert(*[4, 7, 8, 9, 10])
    query_9 = query.select( 5, 0, [1, 1, 1, 1, 1])
    query_12 = query.delete(2)
    transaction5.queries.append(query_7)
    transaction5.queries.append(query_9)
    transaction5.queries.append(query_12)
    db.batcher.enqueue_xact(transaction5)

    transaction6 = Transaction()
    query_10 = query.update(5, *[None, 10, 11, 12, 13])
    query_11 = query.select(5, 0, [1, 1, 1, 1, 1])
    transaction6.queries.append(query_10)
    transaction6.queries.append(query_11)
    db.batcher.enqueue_xact(transaction6)

    db.close()

main_thread = threading.Thread(target=m3_tester)
main_thread.start()

