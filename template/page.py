from template.config import *

class Page:

    def __init__(self):
        self.num_records = 0
        self.data = bytearray(PAGE_SIZE)

    def has_capacity(self):
        pass

    def write(self, value):
        self.num_records += 1
        pass

