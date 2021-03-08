from lstore.table import Table
from lstore.bufferpool import *
from lstore.que_cc import *
import time
import os
import shutil
import pickle


class Database:

    def __init__(self):
        # store tables in a dictionary
        self.table_directory = {}
        self.tables = {}
        self.bufferpool = None
        self.root_name = None
        self.batcher = None

    def open(self, path):
        """
        Open takes in a path to the root of the file system
        """
        self.bufferpool = Bufferpool(path)
        self.batcher = Batcher()

        # TODO spawn a main thread that doesn't close until db.close is called, so we can join out other threads

        # Check if root path already exists and set the root_name
        if os.path.isdir(path):
            self.root_name = path
            # load in the table directory
            for entry in os.scandir(path):
                table_directory_file_path = f"{path}/table_directory.pkl"
                if entry.path == table_directory_file_path: # grab the table directory
                    with open(table_directory_file_path, "rb") as pkl_file:
                        self.table_directory = pickle.load(pkl_file)

            self.populate_tables()

        else:  # Make a new root for this database
            os.mkdir(path)
            self.root_name = path

        # TODO : Read in indexes and page directories

    def populate_tables(self):
        """
        Function that populates table_data from table_directory loaded in from open() and sets it to
        tables[table_name]
        """
        for table_name in self.table_directory:
            path_to_table = self.table_directory[table_name].get("table_path_name")
            num_columns = self.table_directory[table_name].get("num_columns")
            table_key = self.table_directory[table_name].get("key")
            temp_table = Table(name=table_name, num_columns=num_columns, key=table_key, path=path_to_table,
                               bufferpool=self.bufferpool, batcher=self.batcher, is_new=False)
            path_to_page_directory = f"{path_to_table}/page_directory.pkl"
            with open(path_to_page_directory, "rb") as page_directory:
                temp_table.page_directory = pickle.load(page_directory)
            page_directory.close()
            
            table_data = temp_table.page_directory["table_data"]
            temp_table.populate_data_members(table_data)

            # read index from disk
            path_to_indices = f"{path_to_table}/indices.pkl"
            with open(path_to_indices, "rb") as stored_index:
                temp_table.index = pickle.load(stored_index)
            self.tables[table_name] = temp_table

    def close(self):
        """
        Close checks all the dirty bits and writes updates back to disk; saves page_directories and indexes as
        json files
        """
        # Save all the table data
        table_directory_file = open(f"{self.root_name}/table_directory.pkl", "wb")
        pickle.dump(self.table_directory, table_directory_file)
        table_directory_file.close()

        # Thread cleanup
        self.let_execution_threads_complete()
        self.batcher.kill_threads()
        print(f'THREADS KILLED')

        # go through every table and save the page directories
        for table_info in self.table_directory.values():
            table_name = table_info.get("name")
            table = self.tables[table_name]
            table.record_lock = None
            table.db_batcher = None
            table.bufferpool.data_lock = None
            did_close = table.close_table_page_directory()

            if not did_close:
                raise Exception(f"Could not close the page directory: {table_name}")

            # save indexes as pkl
            index_file = open(f"{table.table_path}/indices.pkl", "wb")

            pickle.dump(table.index, index_file)
            index_file.close()
        
        # Write all dirty values back to disk
        self.bufferpool.commit_all_frames()

        print(f'DB CLOSING')
        return True

    def create_table(self, name: str, num_columns: int, key: int) -> Table:
        """
        # create_table makes a new directory inside root called name and adds it to our table directory; makes a new table object
        :param name: string         # Table name
        :param num_columns: int     # Number of Columns: all columns are integer
        :param key: int             # Index of table key in columns
        """
        table_path_name = f"{self.root_name}/{name}"
        if os.path.isdir(table_path_name):
            raise Exception(f"Sorry the name {name} is already taken")
        else:
            os.mkdir(table_path_name)

        table = Table(name, num_columns, key, path=table_path_name, bufferpool=self.bufferpool, batcher=self.batcher)
        # create default index on primary key
        table.index.create_default_primary_index()
        self.tables[name] = table

        # Add table information to table directory
        self.table_directory[name] = {
            "name": name,
            "table_path_name": table_path_name,
            "num_columns": num_columns,
            "key": key
        }
        return table

    @staticmethod
    def delete_directory(path):
        """
        Function that deletes a given file directory
        """
        shutil.rmtree(path)

    def drop_table(self, name):
        """
        drop_table removes the table from self.tables and self.tables_directory; deletes the table's directory in disk
        and its contents
        """

        if name in self.table_directory:
            table_directory = self.table_directory[name]["table_path_name"]
            if os.path.isdir(table_directory):
                self.delete_directory(table_directory)
                del self.table_directory[name]
                del self.tables[name]
                return True

        return False

    def get_table(self, name):
        """
        Returns table with the passed name
        """
        print(f'tables = {self.tables}')
        return self.tables[name]

    def let_execution_threads_complete(self):
        # Thread cleanup
        while self.batcher.xacts_queued != self.batcher.xacts_completed:
            time.sleep(.5)
