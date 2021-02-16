from lstore.page import *
from lstore.index import Index
from lstore.config import *
from lstore.record import *
from lstore.helpers import *
from lstore.bufferpool import *
from time import time
import math
import json
import os
from inspect import currentframe, getframeinfo

frameinfo = getframeinfo(currentframe())

'''
              *** Table Diagram ***

    -----------------------------------------
    |       Table: Holds Page_range(s)      |
    |   ------   ------   ------   ------   |
    |   | PR |   | PR |   | PR |   | PR |   |
    |   ------   ------   ------   ---|--   |
    |                  ...            |     |
    ----------------------------------|------
                                      |---------|  
                                                |
    -----------------------------------------   |
    |     Page_range: Holds Base_page(s)    |   |
    |   ------   ------   ------   ------   |<--|
    |   | BP |   | BP |   | BP |   | BP |   |
    |   ------   ------   ------   ------   |
    |   ------   ------   ------   ------   |
    |   | BP |   | BP |   | BP |   | BP |   |
    |   ------   ------   ------   ------   |
    |   ------   ------   ------   ------   |
    |   | BP |   | BP |   | BP |   | BP |   |
    |   ------   ------   ------   ------   |
    |   ------   ------   ------   ------   |
    |   | BP |   | BP |   | BP |   | BP |   |
    |   ------   ------   ------   ---|---  |
    |                  ...            |     |
    ----------------------------------|------
                                      |--------|         
                                               |                                            
    ----------------------------------------   |                                   
    |       Base_page: Holds Page(s)       |<--|    
    |   -----   -----   -----   -----      |    
    |   | P |   | P |   | P |   | P |      |
    |   |   |   |   |   |   |   |   |  ... |
    |   |   |   |   |   |   |   |   |      |
    |   -----   -----   --|--   -----   |  |                     Each Base_page has a
    ----------------------|-------------|---                list of Tail_page(s) for updates
                          |             |               ----------------------------------------
                          |             |-------------->|       Tail_page: Holds Page(s)       |
                          |                             |   -----   -----   -----   -----      | 
                          |                             |   | P |   | P |   | P |   | P |      | 
                          |                             |   |   |   |   |   |   |   |   |  ... |
                          |                             |   |   |   |   |   |   |   |   |      |
                          |                             |   -----   -----   -----   -----      |
                          |                             ----------------------------------------
                          |----------------------|
                                                 |
    -------------------------------------        |       
    |   Page: Array of 8 Byte Integers  |        |
    |     These are the data columns    |<-------|
    |   -----------------------------   | 
    | 0 |      8 - byte Integer     |   |   This mapping is provide in page.py
    |   -----------------------------   | 
    | 1 |      8 - byte Integer     |   |
    |   -----------------------------   | 
    | 2 |      8 - byte Integer     |   |
    |   -----------------------------   | 
    | 3 |      8 - byte Integer     |   |
    |   -----------------------------   | 
    | - |            ...            |   |
    |   -----------------------------   | 
    -------------------------------------   

'''

class BasePage:
    '''
    :param columns_list: list        Stores a list of all Page objects for the Base_page, these are the data columns
    :param pr_key: int               Holds the integer key of the parent Page Range
    :param key: int                  Holds the integer key of itself as it maps to the Parent Page_range list
    '''
    def __init__(self, num_columns: int, parent_key: int, bp_key: int):
        # Create a list of Physical Pages num_columns long plus Indirection, RID, TimeStamp, and Schema columns
        self.columns_list = [Page(column_num=i) for i in range(num_columns + META_COLUMN_COUNT)]
        self.pr_key = parent_key
        self.key = bp_key
    

class TailPage:
    '''
    :param columns_list: list       Stores a list of all Page objects for the Tail_page, these are the data columns
    :param bp_key: int              Holds the integer key of the parent Base_page
    '''
    def __init__(self, num_columns: int, key: int):
        self.key = key
        # Create a list of Physical Pages num_columns long plus Indirection, RID, TimeStamp, and Schema columns
        self.columns_list = [Page(column_num=i) for i in range(num_columns+ META_COLUMN_COUNT)]
        
    
class PageRange:
    '''
    :param pages: list      Stores a list of all Base_page objects in the Page_range
    :param table_key: int   Holds the integer key of the parent Table
    :param key: int         Holds the integer key of the Page_range as it is mapped in the parent Table list
    '''
    def __init__(self, num_columns: int, parent_key: int, pr_key:int):
        self.table_key = parent_key
        self.num_columns = num_columns
        self.key = pr_key
        self.num_tail_pages = 1
        self.num_tail_records = 0
    
        
class Table:
    """
    :param name: string             Name of the Table
    :param num_columns: int         Number of data columns in the table
    :param key: int                 Integer key value associated with the table
    :param page_directory: dict     Mapping of a 'RID' to the record's location
    :param index: Index             Holds created index for the table #not presently implementing for MS1
    :param book: list               List of Page_range objects, Page_range >> Base_page >> Page
    :param num_records: int         Number of records in the table
    :param num_columns: dict        dict of names associated with columns according to column keys
    """
    def __init__(self, name: str, num_columns: int, key: int, path: str = None, bufferpool: Bufferpool = None):
        self.name = name
        self.bufferpool = bufferpool
        self.table_path = path
        self.key = key
        self.index_on_primary_key = {}
        self.num_columns = num_columns
        self.page_directory = {}
        self.index = Index(self)
        self.num_page_ranges = 0
        self.page_range_data = {}
        self.page_ranges = [PageRange(num_columns=num_columns, parent_key=key, pr_key=0)] 
        self.page_ranges_in_disk = self._allocate_page_range_to_disk()
        self.num_records = 0
        self.num_base_records = 0
        self.num_tail_records = 0
        self.column_names = { 
            0: 'Indirection',
            1: 'RID', 
            2: 'Base_RID',
            3: 'Timestamp',
            4: 'Schema'
        }

    def _allocate_page_range_to_disk(self):
        page_range_path_name = f"{self.table_path}/page_range_{self.num_page_ranges}"
        if os.path.isdir(page_range_path_name):
            # TODO page range not incremeneted error
            print("Page range was not incrememnted")
            return False
        else:

            os.mkdir(page_range_path_name)

            for i in range(BASE_PAGE_COUNT):

                base_page_file_name = f"{page_range_path_name}/base_page_{i}.bin"
                base_page_file = open(base_page_file_name, "wb")
                
                physical_page = bytearray(PAGE_SIZE)
                for i in range(self.num_columns+META_COLUMN_COUNT):
                    base_page_file.write(physical_page)
                
                # print(f"The size using getSize of {base_page_file_name} is {getSize(base_page_file)}\n")
                base_page_file.close()
            
            tail_page_directory_path_name = f"{page_range_path_name}/tail_pages"
            os.mkdir(tail_page_directory_path_name)

            self.page_range_data[self.num_page_ranges] = {
                "tail_page_count": 0,
                "num_tail_records": 0,
                "path_to_tail_pages": f"{self.table_path}/page_range_{self.num_page_ranges}/tail_pages"
            }

            tail_page_count = self.page_range_data[self.num_page_ranges].get("tail_page_count")
            self._allocate_new_tail_page(self.num_page_ranges, tail_page_count)
            
            self.num_page_ranges += 1


    def _allocate_new_tail_page(self, num_page_ranges, tail_page_count):
            # Create new tail page
            new_tail_file_name = f"{self.table_path}/page_range_{num_page_ranges}/tail_pages/tail_page_{tail_page_count}.bin"
            new_tail_file = open(new_tail_file_name, "wb")

            physical_page = bytearray(PAGE_SIZE)
            for i in range(self.num_columns + META_COLUMN_COUNT):
                new_tail_file.write(physical_page)

            new_tail_file.close()
            self.page_range_data[num_page_ranges]["tail_page_count"] += 1


    def __merge(self):
        pass


    def save_table_data(self):
        table_data = {
            "name": self.name,
            "key": self.key,
            "table_path": self.table_path,
            "num_columns": self.num_columns,
            "num_records": self.num_records,
            "num_base_records": self.num_base_records,
            "num_tail_records": self.num_tail_records,
            "column_names": self.column_names,
            "num_page_ranges": self.num_page_ranges,
            "page_range_data": self.page_range_data,
            "index_on_primary_key": self.index_on_primary_key
        }
        self.page_directory["table_data"] = table_data


    def close_table_page_directory(self):
        self.save_table_data()
        page_directory_as_json = json.dumps(self.page_directory)
        # TODO make sure this opens and writes, else should return false
        page_directory_file = open(f"{self.table_path}/page_directory.json", "w")
        page_directory_file.write(page_directory_as_json)
        page_directory_file.close()
        return True


    def new_base_rid(self) -> int:
        '''
        Function that creates a new RID, increments the amount of records in the table,
        then creates a RID dict that is mapped in the Table page_directory.
        '''
        rid = self.num_records
        self.num_records += 1
        self.page_directory[rid] = self.__new_base_rid_dict()
        self.num_base_records += 1

        return rid
    

    def __new_base_rid_dict(self) -> dict:
        '''
        Helper function that returns a dict object holding values associated with a record's RID for use
        in the Table page_directory. Values not relavent to a particular record should keep the None value.

        :param page_range: int      Integer value associated with the record's Page_range index in the Table
        :param base_page: int       Integer value associated with the record's Base_page index within the Page_range
        :param base_index: int      Integer value associated with the record's Page index within the Base_page
        :param deleted: bool        Specifies whether the record was deleted
        '''
        relative_rid = self.num_base_records
        page_range_index = math.floor(relative_rid / ENTRIES_PER_PAGE_RANGE)
        index = relative_rid % ENTRIES_PER_PAGE_RANGE
        base_page_index = math.floor(index / ENTRIES_PER_PAGE)
        physical_page_index = index % ENTRIES_PER_PAGE

        # Check if current page range has space for another record
        if page_range_index > self.num_page_ranges - 1:
            self.create_new_page_range()
            self._allocate_page_range_to_disk()

        record_info = {
            'page_range': page_range_index,
            'base_page': base_page_index,
            'page_index': physical_page_index,
            'deleted': False,
            'is_base_record': True
        }
        
        return record_info
    

    def new_tail_rid(self, page_range_index: int) -> int:
        '''
        Function that creates a new TID, increments the amount of records in the Base_page,
        then creates a TID dict that is mapped in the BP tail_page_directory.
        '''
        rid = self.num_records
        self.num_records += 1
        self.page_directory[rid] = self.__new_tail_rid_dict(page_range_index=page_range_index)
        
        self.page_ranges[page_range_index].num_tail_records += 1
        self.page_range_data[page_range_index]["num_tail_records"] += 1 # TODO do we need to be updating this or is it done at save?
        self.num_tail_records += 1

        return rid


    def __new_tail_rid_dict(self, page_range_index: int) -> dict:
        '''
        Helper function that returns a dict object holding values associated with a record's RID for use
        in the Table page_directory. Values not relavent to a particular record should keep the None value.

        :param tid: int             Integer value of the Tail Identification
        :param tail_page: int       Integer value associated with the record's Tail_page index within the Base_page
        :param page_index: int      Integer value associated with the record's Page index within the Tail_page
        '''

        relative_rid = self.page_ranges[page_range_index].num_tail_records
        tail_page_index = math.floor(relative_rid / ENTRIES_PER_PAGE) 
        physical_page_index = relative_rid % ENTRIES_PER_PAGE

        # Check if current PageRange needs another TailPage allocated
        if tail_page_index > self.page_ranges[page_range_index].num_tail_pages - 1:
            self.page_ranges[page_range_index].num_tail_pages += 1
            self._allocate_new_tail_page(self.num_page_ranges, self.page_ranges[page_range_index].num_tail_pages)   
        
        rid_dict = {
            'page_range': page_range_index,
            'tail_page': tail_page_index,
            'page_index': physical_page_index,
            'is_base_record': False
        }

        return rid_dict


    def __get_last_base_page_record_location(self) -> dict:
        '''
        Helper function that returns a dict of the memory location for a given RID
        '''
        
        page_range_index = math.floor(self.num_base_records / ENTRIES_PER_PAGE_RANGE)
        index = self.num_base_records % ENTRIES_PER_PAGE_RANGE
        base_page_index = math.floor(index / ENTRIES_PER_PAGE)
        physical_page_index = index % ENTRIES_PER_PAGE

        return { 'page_range': page_range_index, 'base_page': base_page_index, 'page_index': physical_page_index }


    def set_column_name(self, name: str, column_key: int) -> None:
        '''
        Function that maps a name to a column key in the Table column_names dict

        :param name: str            Name to map to a column key
        :param column_key: int      Integer associated with a given data column 
        '''
        try:
            self.column_names[column_key] = name
            return
        except Exception as e:
            raise ValueError(f'ERROR: Unable to assign column name. {e}')
    

    def is_page_full(self, page: Page) -> bool:
        '''
        Given a Page object this function will look at the total elements a page can hold: PAGE_SIZE/PAGE_RECORD_SIZE
        in config.py, then return True if the record count for the page is equal to that value and False otherwise.
        :param page: Page       Page object to check
        :return: bool           Returns True if page is full and False otherwise
        '''

        total_elements_possible = (PAGE_SIZE / PAGE_RECORD_SIZE)  # How many total records the page can hold
        if page.num_records == total_elements_possible:           # If the record count is equal to the total possible                                                                 
            return True                                           # the page is full
        return False


    def create_new_page_range(self) -> int:
        '''
        This function creates a new PageRange for the Table and returns its key index for the Table.page_ranges list
        '''
        
        # length of a 0 - indexed list will return the appropriate index that the pr will reside at in Table.page_ranges
        pr_index = len(self.page_ranges)
        new_page_range = PageRange(num_columns=self.num_columns, parent_key=self.key, pr_key= pr_index)
        self.page_ranges.append(new_page_range)

        return pr_index


    def write_new_record(self, record: Record, rid: int) -> bool:
        '''
        This function takes a newly created rid and a Record and finds the appropriate base page to insert it to and updates
        the rid value in the page_directory appropriately
        '''

        record_info = self.page_directory.get(rid)
        pr = record_info.get('page_range')
        bp = record_info.get('base_page')
        pi = record_info.get('page_index')
        is_base_record = record_info.get('is_base_record')

        # Check if record is in bufferpool
        if not self.bufferpool.is_record_in_pool(self.name, record_info=record_info):
            did_load = self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp, is_base_record=is_base_record)
            if not did_load:
                # TODO throw an exception
                print("COULD NOT LOAD")

        # Get Frame index        
        frame_info = (self.name, pr, bp, is_base_record)
        frame_index = self.bufferpool.frame_directory[frame_info]

        for i in range(len(record.all_columns)):
            value = record.all_columns[i]
            self.bufferpool.frames[frame_index].all_columns[i].write(value, pi)

        # Set the dirty bit and increment the access count
        self.bufferpool.frames[frame_index].set_dirty_bit()
        self.bufferpool.frames[frame_index].access_count += 1

        # Stop working with BasePage Frame
        self.bufferpool.frames[frame_index].unpin_frame()
        
        return True


    def update_record(self, updated_record: Record, rid: int) -> bool:
        '''
        This function takes a Record and a RID and finds the appropriate place to write the record and writes it
        '''

        # print('--- UPDATING ---')
        rid_info = self.page_directory.get(rid)
        pr = rid_info.get('page_range')
        bp = rid_info.get('base_page')
        pp_index = rid_info.get('page_index')
        is_base_record = rid_info.get("is_base_record")

        frame_info = (self.name, pr, bp, is_base_record)
        if not self.bufferpool.is_record_in_pool(self.name, record_info=rid_info):
            base_page_frame_index = self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp, is_base_record=is_base_record)
        if self.bufferpool.is_record_in_pool(self.name, record_info=rid_info):
            base_page_frame_index = self.bufferpool.frame_directory[frame_info]

        old_indirection_rid = self.bufferpool.frames[base_page_frame_index].all_columns[INDIRECTION].read(pp_index)

        new_update_rid = self.new_tail_rid(page_range_index=pr)
        new_rid_dict = self.page_directory.get(new_update_rid)

        new_pr = new_rid_dict.get('page_range')
        new_tp = new_rid_dict.get('tail_page')
        new_pp_index = new_rid_dict.get('page_index')
        is_base_record = new_rid_dict.get("is_base_record")
        frame_info = (self.name, new_pr, new_tp, is_base_record)

        if not self.bufferpool.is_record_in_pool(self.name, record_info=new_rid_dict):
            tail_page_frame_index = self.bufferpool.load_page(self.name, self.num_columns, page_range_index=new_pr, base_page_index=new_tp, is_base_record=is_base_record)

        if self.bufferpool.is_record_in_pool(self.name, record_info=new_rid_dict):
            tail_page_frame_index = self.bufferpool.frame_directory.get(frame_info)

        updated_record.all_columns[INDIRECTION] = old_indirection_rid
        updated_record.all_columns[RID_COLUMN] = new_update_rid

        # print(f'new_tp = {new_tp} new_pp_index = {new_pp_index}')
    
        for i in range(len(updated_record.all_columns)):
            # print(f'@ i = {i}; all_columns[{i}] = {updated_record.all_columns[i]}')
            value = updated_record.all_columns[i]
            self.bufferpool.frames[tail_page_frame_index].all_columns[i].write(value, new_pp_index)
            # print(f'read = {self.book[pr].pages[bp].tail_page_list[new_tp].columns_list[i].read(new_pp_index)}')
        
        updated_schema = updated_record.all_columns[SCHEMA_ENCODING_COLUMN]
        # print(f'updated_schema = {updated_schema}')
        wrote_ind = self.bufferpool.frames[base_page_frame_index].all_columns[INDIRECTION].write(value=new_update_rid, row=pp_index)
        # print(f'wrote_ind = {wrote_ind}')
        # print(f'read new_tid = {self.book[pr].pages[bp].columns_list[INDIRECTION].read(pp_index)}')
        wrote_schema = self.bufferpool.frames[base_page_frame_index].all_columns[SCHEMA_ENCODING_COLUMN].write(value=updated_schema, row=pp_index)
        # print(f'wrote_schema = {wrote_schema}')
        # print(f'read updated_schema = {self.book[pr].pages[bp].columns_list[SCHEMA_ENCODING_COLUMN].read(pp_index)}')

        # print('----- EXITING UPDATE ------')
        return True


    def read_record(self, rid) -> Record:
        '''
        :param rid: int             RID of the record being read
        :return Record: Record      Returns the MRU Record associated with the ris

        '''

        record_info = self.page_directory.get(rid)
        #check if updated value is false
        pr = record_info.get("page_range")
        bp = record_info.get("base_page")
        pp_index = record_info.get("page_index")
        is_base_record = record_info.get("is_base_record")
        all_entries = []

        # Check if the BasePage is in the Bufferpool
        frame_info = (self.name, pr, bp, is_base_record)
        if not self.bufferpool.is_record_in_pool(self.name, record_info=record_info):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp, is_base_record=is_base_record)
        
        # Get Frame index
        frame_index = self.bufferpool.frame_directory.get(frame_info)

        # Start working with BasePage Frame
        self.bufferpool.frames[frame_index].pin_frame()
        indirection_rid = self.bufferpool.frames[frame_index].all_columns[INDIRECTION].read(pp_index)

        for col in range(self.num_columns + META_COLUMN_COUNT):
            entry = self.bufferpool.frames[frame_index].all_columns[col].read(pp_index)
            all_entries.append(entry)

        key = all_entries[KEY_COLUMN]
        schema_encode = all_entries[SCHEMA_ENCODING_COLUMN]
        user_cols = all_entries[KEY_COLUMN: ]
        self.bufferpool.frames[frame_index].unpin_frame()
        # Done working with BasePage Frame

        if not schema_encode:
            return Record(key= key, rid = rid, schema_encoding = schema_encode, column_values = user_cols)
        else:
            # record has been updated before
            ind_dict = self.page_directory.get(indirection_rid)
            pr = ind_dict.get("page_range")
            tp = ind_dict.get('tail_page')
            tp_index = ind_dict.get('page_index')
            is_base_record = ind_dict.get("is_base_record")
            column_update_indices = []

            # Check if the TailPage is in the Bufferpool
            frame_info = (self.name, pr, tp, is_base_record)
            if not self.bufferpool.is_record_in_pool(self.name, record_info=ind_dict):
                frame_index = self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pg, base_page_index=bp, is_base_record=is_base_record)
            if self.bufferpool.is_record_in_pool(self.name, record_info=ind_dict):
                frame_index = self.bufferpool.frame_directory.get(frame_info)
            
            for i in range(KEY_COLUMN, self.num_columns + META_COLUMN_COUNT):
                if get_bit(schema_encode, i - META_COLUMN_COUNT):
                    column_update_indices.append(i)
            
            # Start working with TailPage Frame
            self.bufferpool.frames[frame_index].pin_frame()
            for index in column_update_indices:
                user_cols[index - META_COLUMN_COUNT] = self.bufferpool.frames[frame_index].all_columns[index].read(tp_index)
            self.bufferpool.frames[frame_index].unpin_frame()
            # Done working with TailPage Frame

        return Record(key= key, rid = rid, schema_encoding = schema_encode, column_values = user_cols)


    def record_does_exist(self, key):
        '''
        Function returns RID of the an associated key if it exists and None otherwise
        '''
        # get record to find the rid assocated with the key
        if key in self.index_on_primary_key:
            rid = self.index_on_primary_key[key]
            if not self.page_directory[rid]["deleted"]:
                return rid
        
        return False

