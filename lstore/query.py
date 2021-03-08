from lstore.record import Record
from lstore.config import *
from lstore.helpers import *
from lstore.transaction import *

from copy import deepcopy
from math import ceil
import threading


class Query:
    """
    # Creates a Query object that can perform different queries on the specified table 
    Queries that fail must return False
    Queries that succeed should return the result or True
    Any query that crashes (due to exceptions) should return False
    """

    def __init__(self, table):
        self.table = table     

    def delete(self, key):
        """
        # internal Method
        # Read a record with specified key
        # Returns True upon successful deletion
        # Return False if record doesn't exist or is locked due to 2PL
        # Current implementation of delete only sets the delete value to true in the page_directory
        """
        q_op = QueryOp()
        q_op.add_query(DELETE, self.__delete, key)
        return q_op

    def __delete(self, key):
        # Make sure key exists 
        rid = self.table.record_does_exist(key)
        if rid is None:
            return False
        
        # Once found, update delete value to true in page directory
        self.table.page_directory[rid]["deleted"] = True

        # remove rid of deleted row from all indexes
        record = self.table.read_record(rid)
        for i in range(len(record.user_data)):
            key = record.user_data[i]
            if self.table.index.indices[i] is not None:
                self.table.index.get_index_for_column(i).delete(key,rid)
        return True

    def insert(self, *columns):
        """
        Create an Insert transaction
        """
        q_op = QueryOp()
        q_op.add_query(INSERT, self.__insert, *columns)
        return q_op

    def __insert(self, *columns):
        """
        Insert a record with specified columns
        Return True upon successful insertion
        Return False if insert fails for whatever reason
        """

        unique_identifier = columns[0]
        columns_list = list(columns)
        if len(columns_list) != self.table.num_columns:
            return False
        if not self.check_values_are_valid(columns_list):
            return False

        # New record passed the checks, set schema encoding to 0, create a new record, and write to the table
        blank_schema_encoding = 0
        new_rid = self.table.new_base_rid()

        new_record = Record(key=unique_identifier, rid=new_rid, base_rid=new_rid, schema_encoding=blank_schema_encoding,
                            column_values=columns_list)
        did_successfully_write = self.table.write_new_record(record=new_record, rid=new_rid)

        if did_successfully_write:
            # print('INSERT SUCCESSFUL')
            for i in range(len(columns_list)):
                column_index = self.table.index.get_index_for_column(i)
                # print(f'column_index = {column_index}')
                if column_index is not None:
                    column_index.insert(columns_list[i], new_rid)
                    # print(f'post insert col index = {column_index.index}')
            # print(f'INSERT RID = {self.table.index.indices[0].index}')
            return True

        return False

    def select(self, key, column, query_columns):
        """
        # Read a record with specified key
        # :param key: the key value to select records based on
        # :column: the index where key is stored in our table
        # :param query_columns: what columns to return. array of 1 or 0 values.
        # Returns a list of Record objects upon success
        # Returns False if record locked by TPL
        # Assume that select will never be called on a key that doesn't exist
        """
        q_op = QueryOp()
        q_op.add_query(SELECT, self.__select, key, column, query_columns)
        return q_op

    def __select(self, key, column, query_columns):
        # Check that the incoming user arguments to select are valid
        if column > self.table.num_columns or column < 0:
            # column argument out of range
            # print('bad column input 1')
            return False
        if len(query_columns) != self.table.num_columns:
            # length of query columns must equal the number of columns in the table
            # print('bad column input 2')
            return False
        for value in query_columns:
            # incoming query column values must be 0 or 1
            if value != 0 and value != 1:
                # print('bad column input 3')
                return False

        # Make sure that the record selected by the user exists in our database
        valid_rids = self.table.records_with_rid(column, key)
        if len(valid_rids) == 0:
            # print('no valid rids', key, column)
            return False
        record_return_list = []
        for rid in valid_rids:
            selected_record = self.table.read_record(rid=rid)
            for i in range(len(query_columns)):
                if query_columns[i] == 1:
                    continue
                else:
                    selected_record.user_date[i] = None
            record_return_list.append(selected_record.user_data)

        # print(f"__SELECT RETURNING {record_return_list[0].all_columns}")
        return record_return_list

    def update(self, key, *columns):
        """
        # Update a record with specified key and columns
        # Returns True if update is successful
        # Returns False if no records exist with given key or if the target record cannot be accessed due to 2PL locking
        """
        q_op = QueryOp()
        q_op.add_query(UPDATE, self.__update, key, columns)
        return q_op

    def __update(self, key, columns):
        columns_list = columns

        if len(columns_list) != self.table.num_columns:
            return False

        if columns_list[0] is not None:
            # print('columns_list[0] is not None')
            # You cannot update the primary key
            return False

        valid_rid = self.table.record_does_exist(key=key)
        if valid_rid is None:
            # print('valid_rid is None')
            return False

        self.table.merge_check(valid_rid)

        # print(f'*************************** UPDATE FOR {key} ******************************')
        current_record = self.table.read_record(rid=valid_rid)  # read record need to give the MRU
        # print("current_record", current_record.all_columns)
        schema_encoding_as_int = current_record.all_columns[SCHEMA_ENCODING_COLUMN]
        current_record_data = current_record.user_data
        # print('schema as int ', schema_encoding_as_int)
        for i in range(len(columns)):
            # print(f"colummns[i] {i}", columns[i])
            if columns[i] is None:
                if not get_bit(value=schema_encoding_as_int, bit_index=i):
                    # print(f'NOT @ i = {i}; set_bit == {set_bit(value=schema_encoding_as_int, bit_index=i)}')
                    current_record_data[i] = 0
                else:
                    # print(f' CON @ i = {i}; set_bit == {set_bit(value=schema_encoding_as_int, bit_index=i)}')
                    continue
            else:
                # print(f'ELSE @ i = {i}; set_bit == {set_bit(value=schema_encoding_as_int, bit_index=i)}')
                schema_encoding_as_int = set_bit(value=schema_encoding_as_int, bit_index=i)
                current_record_data[i] = columns[i]
        # print(f'MERGE valid_rid = {valid_rid}')
        new_tail_record = Record(key=key, rid=None, base_rid=valid_rid,
                                 schema_encoding=schema_encoding_as_int, column_values=current_record_data)
        # print(f'QUERY New Tail Record {new_tail_record.all_columns}')

        # TODO: this is untested, because m2 tester does ever not select non-primary key values
        # updating indices
        for i in range(len(columns_list)):
            if columns_list[i] is not None:
                column_index = self.table.index.get_index_for_column(i)
                if column_index is not None:
                    old_value = current_record.user_data[i]
                    base_rid = current_record.get_rid()
                    column_index.update(columns_list[i], old_value, base_rid)

        return self.table.update_record(updated_record=new_tail_record, rid=valid_rid)

    def sum(self, start_range, end_range, aggregate_column_index):
        """
        :param start_range: int             # Start of the key range to aggregate
        :param end_range: int               # End of the key range to aggregate
        :param aggregate_column_index: int  # Index of desired column to aggregate
        # this function is only called on the primary key.
        # Returns the summation of the given range upon success
        # Returns False if no record exists in the given range
        """
        # Check the aggregate_column_index is in range
        if aggregate_column_index < 0 or aggregate_column_index > self.table.num_columns:
            # Invalid user input to sum
            return False

        if start_range < 0 or end_range < 0:
            # Primary keys must be positive
            return False

        column_sum = 0
        record_found = False

        # This is traversing every base record, needing to load it into the buffer to check the key column
        for rid in self.table.page_directory:
            rid_info = self.table.page_directory.get(rid)
            if rid_info.get('is_base_record') and not rid_info.get('deleted'):
                record = self.table.read_record(rid)
                key = record.all_columns[KEY_COLUMN]
                if start_range <= key <= end_range:
                    column_sum += record.user_data[aggregate_column_index]
                    record_found = True

        if not record_found:
            return False
        
        return column_sum

    def increment(self, key, column):
        """
        increments one column of the record
        this implementation should work if your select and update queries already work
        :param key: the primary of key of the record to increment
        :param column: the column to increment
        # Returns True is increment is successful
        # Returns False if no record matches key or if target record is locked by 2PL.
        """
        r = self.select(key, self.table.key, [1] * self.table.num_columns)[0]
        if r is not False:
            updated_columns = [None] * self.table.num_columns
            updated_columns[column] = r[column] + 1
            u = self.update(key, *updated_columns)
            return u

        return False

    @staticmethod
    def check_values_are_valid(list_of_values) -> bool:
        for val in list_of_values:
            if val < 0:
                return False
            elif ceil(val.bit_length() / 8.0) >= 8:
                return False
            elif not isinstance(val, int):
                return False
            elif val is None:
                return False
            else:
                continue

        return True  
