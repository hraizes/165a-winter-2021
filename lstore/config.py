# Global Setting for the Database
# PageSize, StartRID, etc..

# Table values
PAGE_SIZE = 4096
PAGE_RECORD_SIZE = 8
BASE_PAGE_COUNT = 16
META_COLUMN_COUNT = 5
ENTRIES_PER_PAGE = int(PAGE_SIZE / PAGE_RECORD_SIZE)
ENTRIES_PER_PAGE_RANGE = ENTRIES_PER_PAGE * BASE_PAGE_COUNT
SPECIAL_NULL_VALUE = pow(2, 64) - 1

# Column Indices
INDIRECTION = 0  # int
RID_COLUMN = 1  # int
BASE_RID_COLUMN = 2
TIMESTAMP_COLUMN = 3  # datetime
SCHEMA_ENCODING_COLUMN = 4  # string
KEY_COLUMN = META_COLUMN_COUNT

# Bufferpool
BUFFERPOOL_FRAME_COUNT = 75  # 1 frame == 1 base page

# Merge
MERGE_COUNT_TRIGGER = 2048

# QueCC
BATCH_SIZE = 4
