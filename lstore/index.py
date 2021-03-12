from lstore.page import *
from lstore.helpers import *
import threading
import math

"""
A data structure holding indices for various columns of a table. Key column should be indexed by default, other columns 
can be indexed through this object. Indices are usually B-Trees, but other data structures can be used as well.
"""


class IndividualIndex:

    def __init__(self, table, column_number):
        # a map between column value and RID
        self.index = {}
        self.lock = threading.Lock()
        self.create_index(table, column_number)

    def create_index(self, table, column_number):
        self.lock.acquire()

        table.bufferpool.commit_all_frames()

        table.bufferpool.commit_all_frames()

        last_rid = table.num_base_records - 1

        last_page_range = math.floor(last_rid / ENTRIES_PER_PAGE_RANGE)
        index = last_rid % ENTRIES_PER_PAGE_RANGE
        last_base_page = math.floor(index / ENTRIES_PER_PAGE)
        last_physical_page_index = index % ENTRIES_PER_PAGE


        for page_range_index in range(0, last_page_range+1):
            page_range_path = f'{table.table_path}/page_range_{page_range_index}'

            last_base_page_index = BASE_PAGE_COUNT
            if page_range_index == last_page_range:
                last_base_page_index = last_base_page  
            for base_page_index in range(0, last_base_page_index+1):
                path_to_file = f'{page_range_path}/base_page_{base_page_index}.bin'

                column_page = Page(META_COLUMN_COUNT+column_number)
                column_page.read_from_disk(path_to_file,META_COLUMN_COUNT+column_number)

                schema_page = Page(SCHEMA_ENCODING_COLUMN)
                schema_page.read_from_disk(path_to_file,SCHEMA_ENCODING_COLUMN)

                rid_page = Page(RID_COLUMN)
                rid_page.read_from_disk(path_to_file, RID_COLUMN)

                indirection_page = Page(INDIRECTION)
                indirection_page.read_from_disk(path_to_file, INDIRECTION)

                last_row_index = ENTRIES_PER_PAGE
                if base_page_index == last_base_page_index:
                    last_row_index = last_physical_page_index+1

                for row in range(last_row_index):
                    schema_encode = schema_page.read(row)
                    schema_encode_bit = get_bit(schema_encode,column_number)

                    rid = rid_page.read(row)
                    base_ind_dict = table.page_directory.get(rid)
                    row_deleted = base_ind_dict.get('deleted')
                    if row_deleted:
                        continue

                    if schema_encode_bit == 1:
                        indirection_rid = indirection_page.read(row)
                        tail_ind_dict = table.page_directory.get(indirection_rid)

                        tail_page = tail_ind_dict.get('tail_page')

                        # read tail page from information

                        physical_tail_page = Page((META_COLUMN_COUNT+column_number))
                        tail_path = f'{page_range_path}/tail_pages/tail_page_{tail_page}.bin'
                        physical_tail_page.read_from_disk(tail_path,META_COLUMN_COUNT+column_number)

                        val = physical_tail_page.read(row)
                        
                        self.index[val] = (self.index.get(val) or []) + [rid]
                    else:
                        val = column_page.read(row)
                        self.index[val] = (self.index.get(val) or [])+[rid]

        self.lock.release()


    def get(self, value):
        """
        returns set of rids containing given value
        """
        return self.index.get(value)

    def insert(self, value, new_rid):
        #self.lock.acquire()
        self.index[value] = (self.index.get(value) or []) + [new_rid]
        #self.lock.release()
    
    def update(self,new_value,old_value, base_rid):
        # remove base rid from the old value's entry
        #self.lock.acquire()
        if base_rid in self.index[old_value]:
            self.index[old_value].remove(base_rid)
        # add base rid to new value's entry
        self.index[new_value] = (self.index.get(new_value) or []) + [base_rid]
        #self.lock.release()

    def delete(self, value, deleted_rid):
        #self.lock.acquire()
        self.index[value].remove(deleted_rid)
        #self.lock.release()



class Index:

    def __init__(self, table):
        # One index for each table. All our empty initially.
        self.indices = [None] * table.num_columns
        self.table = table
    
    def create_default_primary_index(self):
        self.create_index(0)

    def get_index_for_column(self,column):
        """
        # returns the IndividualIndex for given column
        """
        return self.indices[column]

    def create_index(self, column_number):
        """
        # optional: Create index on specific column
        """
        self.indices[column_number] = IndividualIndex(self.table, column_number)

    def drop_index(self, column_number):
        """
        # optional: Drop index of specific column
        """
        if column_number == 0:
            return
        self.indices[column_number] = None
