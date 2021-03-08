from lstore.page import *
from lstore.index import Index
from lstore.config import *
from lstore.record import *
from lstore.helpers import *
from lstore.bufferpool import *
from lstore.que_cc import *
import math
import os
import pickle
import threading

'''
              *** Table Diagram ***

    -----------------------------------------
    |       Table: Holds PageRange(s)       |
    |   ------   ------   ------   ------   |
    |   | PR |   | PR |   | PR |   | PR |   |
    |   ------   ------   ------   ---|--   |
    |                  ...            |     |
    ----------------------------------|------
                                      |---------|  
                                                |
    -----------------------------------------   |
    |     PageRange: Holds BasePage(s)      |   |
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
    |                  ...            |     |------|
    ----------------------------------|------      |
                                      |--------|   |     
                                               |   |                                        
    ----------------------------------------   |   |                               
    |       BasePage: Holds Page(s)        |<--|   |
    |   -----   -----   -----   -----      |       |
    |   | P |   | P |   | P |   | P |      |       |
    |   |   |   |   |   |   |   |   |  ... |       |
    |   |   |   |   |   |   |   |   |      |       |
    |   -----   -----   --|--   -----      |       |              Each PageRange has a
    ----------------------|-----------------       |         list of TailPage(s) for updates
                          |                        |    ----------------------------------------
                          |                        |--->|       TailPage: Holds Page(s)        |
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


class PageRange:
    """
    :param num_columns: int        Number of data columns in the PageRange
    :param parent_key: int         Integer key of the parent Table
    :param pr_key: int             Integer key of the PageRange as it is mapped in the parent Table list
    """
    def __init__(self, num_columns: int, parent_key: int, pr_key: int):
        self.table_key = parent_key
        self.num_columns = num_columns
        self.key = pr_key
        self.num_tail_pages = 0
        self.num_tail_records = 0
    
        
class Table:
    """
    :param name: string             Name of the Table
    :param num_columns: int         Number of data columns in the Table
    :param key: int                 Integer key of the Table as it is mapped in the parent Database
    :param path: str                File path of the Table
    :param bufferpool: Bufferpool   Active Bufferpool for the Database
    """
    def __init__(self, name: str, num_columns: int, key: int, path: str = None, bufferpool: Bufferpool = None,
                 batcher: Batcher = None, is_new=True):
        self.name = name
        self.db_batcher = batcher
        self.bufferpool = bufferpool
        self.table_path = path
        self.key = key
        self.num_columns = num_columns
        self.page_directory = {}
        self.index = Index(self)
        self.num_page_ranges = 0
        self.page_range_data = {}
        self.page_ranges = [PageRange(num_columns=num_columns, parent_key=key, pr_key=0)]
        self.num_records = 0
        self.num_base_records = 0
        self.num_tail_records = 0
        self.record_lock = threading.Lock()
        self.column_names = { 
            0: 'Indirection',
            1: 'RID', 
            2: 'Base_RID',
            3: 'Timestamp',
            4: 'Schema'
        }

        if is_new:
            self._allocate_page_range_to_disk()

    def _allocate_page_range_to_disk(self):
        """
        Function that allocates a new PageRange to disk
        """
        page_range_path_name = f"{self.table_path}/page_range_{self.num_page_ranges}"
        if os.path.isdir(page_range_path_name):
            raise Exception("Page range was not incremented")
        else:

            os.mkdir(page_range_path_name)

            for i in range(BASE_PAGE_COUNT):

                base_page_file_name = f"{page_range_path_name}/base_page_{i}.bin"
                base_page_file = open(base_page_file_name, "wb")
                
                physical_page = bytearray(PAGE_SIZE)
                for j in range(self.num_columns+META_COLUMN_COUNT):
                    base_page_file.write(physical_page)
                
                # print(f"The size using getSize of {base_page_file_name} is {getSize(base_page_file)}\n")
                base_page_file.close()
            
            tail_page_directory_path_name = f"{page_range_path_name}/tail_pages"
            os.mkdir(tail_page_directory_path_name)

            self.page_range_data[self.num_page_ranges] = {
                "tail_page_count": 0,
                "num_tail_records": 0,
                "num_updates": 0,
                "path_to_tail_pages": f"{self.table_path}/page_range_{self.num_page_ranges}/tail_pages"
            }

            tail_page_count = self.page_range_data[self.num_page_ranges].get("tail_page_count")
            self._allocate_new_tail_page(self.num_page_ranges, tail_page_count)
            
            self.num_page_ranges += 1

    def _allocate_new_tail_page(self, page_range_index: int, tail_page_index: int):
        """
        Function that allocates a new TailPage to disk and updates the parent PageRange
        """
        # Create new tail page
        # # print(f'Allocating new tail page')
        new_tail_file_name = f"{self.table_path}/page_range_{page_range_index}" \
                             f"/tail_pages/tail_page_{tail_page_index}.bin"

        new_tail_file = open(new_tail_file_name, "wb")

        physical_page = bytearray(PAGE_SIZE)
        for i in range(self.num_columns + META_COLUMN_COUNT):
            new_tail_file.write(physical_page)

        new_tail_file.close()
        self.page_ranges[page_range_index].num_tail_pages += 1
        self.page_range_data[page_range_index]["tail_page_count"] += 1

    def merge_check(self, rid: int):
        """
        This function provides an interface to check and run a merge
        """
        rid_info = self.page_directory.get(rid)
        pr = rid_info.get('page_range')
        if self.page_range_data[pr].get('num_updates') % MERGE_COUNT_TRIGGER == 0:
            merge_thread = threading.Thread(target=self.__merge)
            merge_thread.daemon = True
            merge_thread.start()

    def __merge(self):
        """
        Function loads a PageRange into memory and tries to consolidate TailPage information into BasePages
        """

        # For each PageRange We will need to do the whole merge process
        self.record_lock.acquire()

        # Check for dirty frames in the bufferpool and write to disk before merge
        for i in range(len(self.bufferpool.frames)):
            frame = self.bufferpool.frames[i]
            if frame.dirty_bit:
                write_to_disk(frame.path_to_page_on_disk, frame.all_columns)
                frame.unset_dirty_bit()

        for pr_index in range(self.num_page_ranges):
            merge_buffer = Bufferpool(self.bufferpool.path_to_root)
            merge_buffer.merge_buffer = True
            num_tail_pages = self.page_ranges[pr_index].num_tail_pages

            updated_records = {}
            updated_base_pages = {}

            # Load each BasePage for the PageRange in the buffer
            for bp_index in range(BASE_PAGE_COUNT):
                merge_buffer.load_page(table_name=self.name, num_columns=self.num_columns, page_range_index=pr_index,
                                       base_page_index=bp_index, is_base_record=True)
            # Load each TailPage for the PageRange in the buffer
            for tp_index in range(num_tail_pages):
                merge_buffer.load_page(table_name=self.name, num_columns=self.num_columns, page_range_index=pr_index,
                                       base_page_index=tp_index, is_base_record=False)

            tp_start_frame_index = BASE_PAGE_COUNT
            tp_end_frame_index = merge_buffer.frame_count - 1

            # Traverse TailPages and records in reverse order, if a BasePage hasn't been updated yet, update it
            # use the BASE_RID to update the BasePage record and keep a log of which BasePages were updated
            for frame in range(tp_end_frame_index, tp_start_frame_index - 1, -1):
                for record_index in range(ENTRIES_PER_PAGE-1, -1, -1):
                    # Check Base RID of each record and see if it has been updated yet
                    base_rid = merge_buffer.frames[frame].all_columns[BASE_RID_COLUMN].read(record_index)
                    if base_rid not in updated_records:
                        # Found Latest Update
                        tail_rid = merge_buffer.frames[frame].all_columns[RID_COLUMN].read(record_index)
                        self.__merge_update(buffer=merge_buffer, base_rid=base_rid, tail_record_index=record_index,
                                            tail_frame=frame, tail_rid=tail_rid)
                        updated_records[base_rid] = True
                        bp_info = self.page_directory.get(base_rid)
                        bp = bp_info.get('base_page')
                        updated_base_pages[bp] = True

            # Write updated BasePages to disk
            for bp_frame in updated_base_pages:
                merge_buffer.frames[bp_frame].set_dirty_bit()
                merge_buffer.commit_page(bp_frame)

            # Reload updated BasePages into bufferpool
            for bp in updated_base_pages:
                sample_rid = bp * ENTRIES_PER_PAGE
                sample_record_info = self.page_directory.get(sample_rid)
                if self.bufferpool.is_record_in_pool(self.name, sample_record_info):
                    frame_index = self.bufferpool.get_page_frame(self.name, sample_record_info)
                    self.bufferpool.reload_page(frame_index, self.num_columns)

            # Delete merge_buffer
            del merge_buffer

        self.record_lock.release()

    def __merge_update(self, buffer: Bufferpool, base_rid: int, tail_record_index: int, tail_frame: int, tail_rid: int):
        """
        This helper function performs the BasePage update for the merge process
        """
        base_record_info = self.page_directory.get(base_rid)
        bp_index = base_record_info.get('base_page')
        pp_index = base_record_info.get('page_index')

        schema = buffer.frames[bp_index].all_columns[SCHEMA_ENCODING_COLUMN].read(pp_index)
        column_update_indices = []

        # Determine which columns need to be updated based on the schema column
        for i in range(KEY_COLUMN, self.num_columns + META_COLUMN_COUNT):
            if get_bit(schema, i - META_COLUMN_COUNT):
                column_update_indices.append(i)

        # Update the appropriate BasePage columns
        for index in column_update_indices:
            data = buffer.frames[tail_frame].all_columns[index].read(tail_record_index)
            buffer.frames[bp_index].all_columns[index].write(data, pp_index)

        self.page_directory[base_rid]['tps'] = tail_rid

    def save_table_data(self):
        """
        Function that stores a Table's data members to a dict and stores that in the Table page_directory
        """
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
        }
        self.page_directory["table_data"] = table_data

    def populate_data_members(self, table_data):
        """
        Function that populates a Table's data members from given table_data

        """
        self.name = table_data["name"]
        self.key = table_data["key"]
        self.table_path = table_data["table_path"]
        self.num_columns = table_data["num_columns"]
        self.num_records = table_data["num_records"]
        self.num_base_records = table_data["num_base_records"]
        self.num_tail_records = table_data["num_tail_records"]
        self.column_names = table_data["column_names"]
        self.num_page_ranges = table_data["num_page_ranges"]
        self.page_range_data = table_data["page_range_data"]

    def close_table_page_directory(self):
        """
        Function that writes the Table's page_directory to disk
        """
        self.save_table_data()
        # TODO make sure this opens and writes, else should return false
        page_directory_file = open(f"{self.table_path}/page_directory.pkl", "wb")
        pickle.dump(self.page_directory, page_directory_file)
        page_directory_file.close()

        return True

    def new_base_rid(self) -> int:
        """
        Function that creates a new RID, increments the amount of records in the table,
        then creates a RID dict that is mapped in the Table page_directory.
        """
        self.record_lock.acquire()
        rid = self.num_records
        self.num_records += 1
        self.page_directory[rid] = self.__new_base_rid_dict()
        self.num_base_records += 1
        self.record_lock.release()
        return rid

    def __new_base_rid_dict(self) -> dict:
        """
        Helper function that returns a dict object holding values associated with a record's RID for use
        in the Table page_directory.
        """
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
            'tps': 0,
            'deleted': False,
            'is_base_record': True
        }
        
        return record_info

    def new_tail_rid(self, page_range_index: int) -> int:
        """
        Function that creates a new TID, increments the amount of records in the Base_page,
        then creates a TID dict that is mapped in the BP tail_page_directory.
        """


        rid = self.num_records
        self.num_records += 1
        self.page_directory[rid] = self.__new_tail_rid_dict(page_range_index=page_range_index)


        return rid

    def __new_tail_rid_dict(self, page_range_index: int) -> dict:
        """
        Helper function that returns a dict object holding values associated with a record's RID for use
        in the Table page_directory.

        :param page_range_index: int     Integer Key of the TailPage's parent PageRange
        """

        relative_rid = self.page_ranges[page_range_index].num_tail_records
        tail_page_index = math.floor(relative_rid / ENTRIES_PER_PAGE) 
        physical_page_index = relative_rid % ENTRIES_PER_PAGE
        
        # Check if current PageRange needs another TailPage allocated
        if tail_page_index > self.page_range_data[page_range_index]["tail_page_count"] - 1:
            self._allocate_new_tail_page(page_range_index, self.page_range_data[page_range_index]["tail_page_count"])
        
        # TODO Do you need this Jim? NO WE DON'T HALEY
        self.page_ranges[page_range_index].num_tail_records += 1
        self.page_range_data[page_range_index]["num_tail_records"] += 1
        self.num_tail_records += 1
        
        rid_dict = {
            'page_range': page_range_index,
            'tail_page': tail_page_index,
            'page_index': physical_page_index,
            'is_base_record': False
        }
        # print(f'__new_tail_rid = {rid_dict}')
        return rid_dict

    def create_new_page_range(self) -> int:
        """
        This function creates a new PageRange for the Table and returns its key index for the Table.page_ranges list
        """
        
        # length of a 0 - indexed list will return the appropriate index that the pr will reside at in Table.page_ranges
        pr_index = len(self.page_ranges)
        new_page_range = PageRange(num_columns=self.num_columns, parent_key=self.key, pr_key=pr_index)
        self.page_ranges.append(new_page_range)

        return pr_index

    def write_new_record(self, record: Record, rid: int) -> bool:
        """
        This function takes a newly created rid and a Record and finds the appropriate base page to insert it to and
        updates the rid value in the page_directory appropriately
        """
        self.record_lock.acquire()
        record_info = self.page_directory.get(rid)
        pr = record_info.get('page_range')
        bp = record_info.get('base_page')
        pi = record_info.get('page_index')
        is_base_record = record_info.get('is_base_record')
        
        # Get Frame index        
        frame_info = (self.name, pr, bp, is_base_record)

        # Check if record is in bufferpool
        if not self.bufferpool.is_record_in_pool(self.name, record_info=record_info):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp,
                                      is_base_record=is_base_record)

        frame_index = self.bufferpool.frame_directory[frame_info]

        # Write values to page
        for i in range(len(record.all_columns)):
            value = record.all_columns[i]
            self.bufferpool.frames[frame_index].all_columns[i].write(value, pi)

        # Set the dirty bit and increment the access count
        self.bufferpool.frames[frame_index].set_dirty_bit()
        self.bufferpool.frames[frame_index].access_count += 1

        # Stop working with BasePage Frame
        self.bufferpool.frames[frame_index].unpin_frame()
        self.record_lock.release()
        return True

    def update_record(self, updated_record: Record, rid: int) -> bool:
        """
        This function takes a Record and a RID and finds the appropriate place to write the record and writes it
        """

        self.record_lock.acquire()
        rid_info = self.page_directory.get(rid)
        pr = rid_info.get('page_range')
        bp = rid_info.get('base_page')
        pp_index = rid_info.get('page_index')
        is_base_record = rid_info.get("is_base_record")

        frame_info = (self.name, pr, bp, is_base_record)

        # Start working with BasePage
        if not self.bufferpool.is_record_in_pool(self.name, record_info=rid_info):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp,
                                      is_base_record=is_base_record)

        base_page_frame_index = self.bufferpool.frame_directory[frame_info]

        old_indirection_rid = self.bufferpool.frames[base_page_frame_index].all_columns[INDIRECTION].read(pp_index)

        self.bufferpool.frames[base_page_frame_index].unpin_frame()
        # Done working with BasePage

        new_update_rid = self.new_tail_rid(page_range_index=pr)
        new_rid_dict = self.page_directory.get(new_update_rid)

        new_pr = new_rid_dict.get('page_range')
        new_tp = new_rid_dict.get('tail_page')
        new_pp_index = new_rid_dict.get('page_index')

        tail_frame_info = (self.name, new_pr, new_tp, False)

        # Start working with TailPage
        if not self.bufferpool.is_record_in_pool(self.name, record_info=new_rid_dict):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=new_pr, base_page_index=new_tp,
                                      is_base_record=False)

        tail_page_frame_index = self.bufferpool.frame_directory.get(tail_frame_info)

        updated_record.all_columns[INDIRECTION] = old_indirection_rid
        updated_record.all_columns[RID_COLUMN] = new_update_rid

        for i in range(len(updated_record.all_columns)):
            value = updated_record.all_columns[i]
            self.bufferpool.frames[tail_page_frame_index].all_columns[i].write(value, new_pp_index)

        self.bufferpool.frames[tail_page_frame_index].set_dirty_bit()
        self.bufferpool.frames[tail_page_frame_index].unpin_frame()
        # Stop working with TailPage
        
        updated_schema = updated_record.all_columns[SCHEMA_ENCODING_COLUMN]

        # Update BasePage
        # Start working with BasePage
        if not self.bufferpool.is_record_in_pool(self.name, record_info=rid_info):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp,
                                      is_base_record=is_base_record)

        frame_info = (self.name, pr, bp, is_base_record)
        base_page_frame_index = self.bufferpool.frame_directory[frame_info]

        self.bufferpool.frames[base_page_frame_index].all_columns[INDIRECTION].write(value=new_update_rid, row=pp_index)
        self.bufferpool.frames[base_page_frame_index].all_columns[SCHEMA_ENCODING_COLUMN].write(value=updated_schema,
                                                                                                row=pp_index)
        # Stop working with BasePage
        self.bufferpool.frames[base_page_frame_index].set_dirty_bit()
        self.bufferpool.frames[base_page_frame_index].unpin_frame()

        self.page_range_data[pr]['num_updates'] += 1

        self.record_lock.release()

        return True

    def read_record(self, rid) -> Record:
        """
        Reads and returns the Record of a given RID
        :param rid: int             RID of the record being read
        :return Record: Record      Returns the MRU Record associated with the RID
        """

        self.record_lock.acquire()
        record_info = self.page_directory.get(rid)
        # Check if updated value is false
        pr = record_info.get("page_range")
        bp = record_info.get("base_page")
        pp_index = record_info.get("page_index")
        is_base_record = record_info.get("is_base_record")
        tps = record_info.get('tps')
        all_entries = []

        # Start working with BasePage Frame
        frame_info = (self.name, pr, bp, is_base_record)
        if not self.bufferpool.is_record_in_pool(self.name, record_info=record_info):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=bp,
                                      is_base_record=is_base_record)

        # Get Frame index
        frame_index = self.bufferpool.frame_directory.get(frame_info)
        indirection_rid = self.bufferpool.frames[frame_index].all_columns[INDIRECTION].read(pp_index)

        for col in range(self.num_columns + META_COLUMN_COUNT):
            entry = self.bufferpool.frames[frame_index].all_columns[col].read(pp_index)
            all_entries.append(entry)

        key = all_entries[KEY_COLUMN]
        schema_encode = all_entries[SCHEMA_ENCODING_COLUMN]
        user_cols = all_entries[KEY_COLUMN:]
        self.bufferpool.frames[frame_index].unpin_frame()
        # Done working with BasePage Frame

        if not schema_encode:
            self.record_lock.release()
            return Record(key=key, rid=rid, base_rid=rid, schema_encoding=schema_encode, column_values=user_cols)

        if tps == indirection_rid:
            self.record_lock.release()
            return Record(key=key, rid=rid, base_rid=rid, schema_encoding=schema_encode, column_values=user_cols)

        # record has been updated before
        ind_dict = self.page_directory.get(indirection_rid)
        pr = ind_dict.get("page_range")
        tp = ind_dict.get('tail_page')
        tp_index = ind_dict.get('page_index')
        is_base_record = ind_dict.get("is_base_record")
        column_update_indices = []

        # Start working with TailPage Frame
        frame_info = (self.name, pr, tp, is_base_record)

        if not self.bufferpool.is_record_in_pool(self.name, record_info=ind_dict):
            self.bufferpool.load_page(self.name, self.num_columns, page_range_index=pr, base_page_index=tp,
                                      is_base_record=is_base_record)

        frame_index = self.bufferpool.frame_directory.get(frame_info)

        for i in range(KEY_COLUMN, self.num_columns + META_COLUMN_COUNT):
            if get_bit(schema_encode, i - META_COLUMN_COUNT):
                column_update_indices.append(i)

        for index in column_update_indices:
            user_cols[index - META_COLUMN_COUNT] = \
                self.bufferpool.frames[frame_index].all_columns[index].read(tp_index)

        self.bufferpool.frames[frame_index].unpin_frame()
        # Done working with TailPage Frame

        self.record_lock.release()
        return Record(key=key, rid=indirection_rid, base_rid=rid, schema_encoding=schema_encode,
                      column_values=user_cols)

    def record_does_exist(self, key):
        """
        Function returns RID of the an associated key if it exists and None otherwise
        """
        # get record to find the rid associated with the key
        column_index = self.index.get_index_for_column(0)
        rids = column_index.get(key)
        if rids is None or len(rids) != 1:
            return None
        else:
            if not self.page_directory[rids[0]]["deleted"]:
                return rids[0]
            else:
                return None

    def records_with_rid(self, column, key):
        """
        Returns list of rids with given key in given column
        if there are no rows with given key in given column, return an empty list
        """
        column_index = self.index.get_index_for_column(column)
        # if there is an index, use the index
        if column_index is not None:
            # print(f'records key = {key}')
            # print(f'column_index = {column_index.index}')
            return column_index.get(key)
        # otherwise, do linear scan to find rids with given column value
        else:
            rids_with_value = []
            # use bufferpool to do linear scan
            # write values into rids_with_value
            for key in self.page_directory:
                rid_info = self.page_directory.get(key)
                if rid_info.get('is_base_record') and not rid_info.get('deleted'):
                    record = self.read_record(key)
                    if record.user_data[column] == key:
                        rids_with_value.append(record.get_rid())
            return rids_with_value

