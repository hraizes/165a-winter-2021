from lstore.db import *
from lstore.table import *
from lstore.config import *
from lstore.query import *
from lstore.helpers import *
from random import choice, randint, sample, seed
from datetime import *

help_menu = """
                                                   *** HELP ***
    |-----------------------------------------------------------------------------------------------------------|
    | COMMAND FORMAT                                    | COMMAND INFO                                          |
    |---------------------------------------------------|-------------------------------------------------------|
    | exit                                              | exit the program                                      |
    |---------------------------------------------------|-------------------------------------------------------|
    | table                                             | view table columns                                    |
    |---------------------------------------------------|-------------------------------------------------------|
    | insert [student ID] [Grade 1] [Grade 2] [Grade 3] | insert record to database                             |
    |---------------------------------------------------|-------------------------------------------------------|
    | select [student ID]                               | find record with key Student ID in table              |
    |---------------------------------------------------|-------------------------------------------------------|
    | delete [student ID]                               | delete record                                         |
    |---------------------------------------------------|-------------------------------------------------------|
    | update [student ID] [col0,col1,col2,col3]         | update record                                         |
    |---------------------------------------------------|-------------------------------------------------------|
    | sum [start] [end] [column to sum]                 | sum the elements of column to sum betweent the ranges |
    |---------------------------------------------------|-------------------------------------------------------|
    | bufferpool                                        | get info about bufferpool & bufferpool record info    |
    |-----------------------------------------------------------------------------------------------------------|
    """

def run_demo():
    path = './ECS165-Demo'
    clear_database(path)
    db = Database()
    db.open('./ECS165-Demo')

    table = db.create_table('Grades', 5, 0)
    query = Query(table)
    bufferpool = table.bufferpool

    index = None

    num_students = input('How many students in the class? > ')
    num_students = int(num_students)

    print(f'Making Database & inserting {num_students} records...')
    print("|----------------------------------------|")

    # repopulate with random data
    records = {}
    seed(3562901)
    for i in range(0, num_students):
        key = i
        num1 = randint(0, 20)
        num2 = randint(0, 20)
        num3 = randint(0, 20)
        num4 = randint(0, 20)
        records[key] = [key, num1, num2, num3, num4]
        query.insert(*records[key])
        print(f'|            {key:03d}: {num1:02d} {num2:02d} {num3:02d} {num4:02d}            |')
    print("|----------------------------------------|")

    keys = sorted(list(records.keys()))

    # select all data
    for key in keys:
        record = query.select(key, 0, [1, 1, 1, 1, 1])[0]

    while (1):
        # Take user input
        usr_in = input("ecs165.m1 > ")
        commands = usr_in.split(' ')  

        # exit
        if commands[0] == "exit":
            print("exiting database...")
            break

        # show table details
        elif commands[0] == "table":
            print("|----------------------------------------|")
            for key in keys:
                record = query.select(key, 0, [1, 1, 1, 1, 1])[0]
                print(f'|            {key:03d}: {record.user_data[1]:02d} {record.user_data[2]:02d} {record.user_data[3]:02d} {record.user_data[4]:02d}            |')
            print("|----------------------------------------|")
        
        # insert new record
        elif commands[0] == "insert":
            record = []
            for i in commands[1:]:
                record.append(int(i))
            exists = table.record_does_exist(record[0])

            if exists:
                print("record already exists")
                continue

            q = query.insert(record[0], record[1], record[2], record[3], record[4])
            
            if q:
                print("successfully inserted", record)
                records[record[0]] = [record[0], record[1], record[2], record[3], record[4]]
                keys = sorted(list(records.keys()))
            else:
                print("failed to insert", record)
        
        # get record details
        elif commands[0] == "select":
            sid_arr = []
            # case one: get multiple records
            if len(commands) > 2:
                for sid in commands[1:]:
                    sid_arr.append(int(sid))
            else:
                sid_range = commands[1].split('-')
                # case two: get one record
                if len(sid_range) == 1:
                    sid_arr.append(int(sid_range[0]))
                else:
                    # case three: get range of records
                    start = int(sid_range[0])
                    end = int(sid_range[1])+1
                    for i in range(start, end):
                        sid_arr.append(i)
            
            print("|----------------------------------------|")
            for sid in sid_arr:
                record = query.select(sid, 0, [1,1,1,1,1])[0]
                if record == False:
                    print(f'-----Could not find record {sid}-----')
                else:
                    print(f'|            {sid:03d}: {record.user_data[1]:02d} {record.user_data[2]:02d} {record.user_data[3]:02d} {record.user_data[4]:02d}            |')
            print("|----------------------------------------|")

        # delete record
        elif commands[0] == "delete":
            sid = int(commands[1])
            
            delete = query.delete(sid)
            
            if delete:
                print("Successfully deleted", sid)
                del records[sid]
                keys = sorted(list(records.keys()))
            else:
                print("failed to delete", sid)
        
        # sum record
        elif commands[0] == "sum":
            start = int(commands[1])
            end = int(commands[2])
            col_index = int(commands[3])
            sum = query.sum(start, end, col_index)
            if (sum == False):
                print("Could not calculate sum")
            else:
                print("Sum is", sum)
        
        # update record
        elif commands[0] == "update":
            sid = int(commands[1])
            updates = []
            for i in commands[2:]:
                if i == "None":
                    updates.append(None)
                else:
                    updates.append(int(i))
            ret = query.update(sid, None, updates[0], updates[1], updates[2])
            if not ret:
                print("Failed to update")
            else:
                print(f'Updated {sid} with {updates}')
        
        # create index
        elif commands[0] == "index":
            if index is None:
                index = Index(table)
                index.create_default_primary_index()

                counter = 0
                for key in keys:
                    index_records = index.indices[0].get(key)
                    if (index_records == None):
                        record = query.select(key, 0, [1, 1, 1, 1, 1])[0]
                        if record:
                            print(f'Record {key} expected at position {counter} but found None')
                    counter += 1
            if len(commands) > 1:
                # creating or looking at index of other column
                index.create_index(int(commands[1]))
            
        
        # get bufferpool info
        elif commands[0] == "bufferpool":
            if bufferpool.at_capacity():
                print("    * Bufferpool is at capacity")
            else:
                print("    * Bufferpool is not at capacity")


            count = 1
            print("    Frame info:")
            for frame in bufferpool.frames:
                load_time = frame.time_in_bufferpool.strftime('%Y-%m-%d %H:%M:%S.%f')
                print(f'      Frame {count} has been in the bufferpool since {load_time}')
                print(f'      Frame {count} has been accessed {frame.access_count} times')
                if frame.dirty_bit:
                    print(f'      Frame {count} needs to be merged')
                else:
                    print(f'      Frame {count} does not need to be merged')
                count += 1
        
        # commit changes
        elif commands[0] == "commit":
            bufferpool.commit_all_frames()
        
        # show commands
        elif commands[0] == "help":
            print(help_menu)
        else:
            print("Invalid command")

    return

run_demo()