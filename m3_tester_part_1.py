from lstore.db import Database
from lstore.query import Query
from lstore.transaction import Transaction
from lstore.helpers import clear_database

from random import choice, randint, sample, seed

clear_database('./ECS165')

db = Database()
db.open('./ECS165')
grades_table = db.create_table('Grades', 5, 0)
num_threads = 8

keys = []
records = {}
seed(3562901)
q = Query(grades_table)
insert_transactions = []

# Make 1000 Transactions with Insert Queries in them
for i in range(1000):
    key = 916841696 + i
    records[key] = [key, randint(0, 20), randint(0, 20), randint(0, 20), randint(0, 20)]
    transaction = Transaction()
    transaction.add_query(q.insert(*records[key]))
    insert_transactions.append(transaction)

# Submit the 1000 Transactions to be committed
for i in range(1000):
    db.batcher.enqueue_xact(insert_transactions[i])


# Create multiple transactions with multiple updates
query_transactions = []
select_transactions = []
for i in range(1000):
    transaction = Transaction()
    query_transactions.append(transaction)
    transaction2 = Transaction()
    select_transactions.append(transaction2)

for i in range(1000):
    for j in range(5):
        key = 916841696 + i
        records[key] = [None, randint(0,100), randint(0,100), randint(0,100), randint(0,100)]
        query = q.update(key, *records[key] )
        query_transactions[i].add_query(query)

# Submit the 1000 Transactions to be committed
for i in range(1000):
    db.batcher.enqueue_xact(query_transactions[i])

for i in range(1000):
    for j in range(5):
        query = q.select(randint(916841696, 916842695), 0, [1, 1, 1, 1, 1] )
        select_transactions[i].add_query(query)

# Submit the 1000 Transactions to be committed
for i in range(1000):
    db.batcher.enqueue_xact(select_transactions[i])

db.let_execution_threads_complete()

# Check updates are what we expected, NOT USING OUR WORKER THREADS
# TODO needs to be setup to do string compare
for i in range(1000):
    q_op = q.select(916841696 + i, 0, [1, 1, 1, 1, 1])
    print(f'SELECTING {q_op.run()} should be {records[916841696 + i]}')

db.close()
