from collections import deque
from lstore.transaction import Transaction
from lstore.config import *

import time
import threading

class Batcher:
    """
    Holds Transactions ready for consumption by PlanningWorkers
    Queue fills as Xacts come in and get then get moved to a batch until it fills
    then batch gets flagged for processing
    """

    def __init__(self):
        self.xact_queue = deque()
        self.kill_thread = False
        self.xact_batch = []
        self.batch_ready = False
        self.xact_count = 0
        self.xacts_queued = 0
        self.xacts_completed = 0
        self.transaction = []
        self.xact_meta_data = {
            # xact_id : [len of queries list, [], False]
        }
        self.high_priority_group = Group()
        self.low_priority_group = Group()
        self.high_planner = PlanningWorker(self.high_priority_group, self)
        # self.low_planner = PlanningWorker(self.low_priority_group, self)
        self.high_executors = self.initialize_execution_threads()
        self.intern = InternWorker(self)
        self.execution_mutex = threading.Lock()

    def initialize_execution_threads(self):
        executor_list = []
        for i in range(PRIORITY_QUEUE_COUNT):
            temp_executor = ExecutionWorker(self, i)
            executor_list.append(temp_executor)

        return executor_list

    def batch_xact(self):
        """
        fills a batch with transactions from the xact_queue
        """
        # print('BATCHING transactions')
        for i in range(BATCH_SIZE + 1):

            if len(self.xact_batch) < BATCH_SIZE and len(self.xact_queue) > 0:
                # print("BATCH < BATCH_SIZE")
                xact = self.xact_queue.popleft()
                self.xact_batch.append(xact)

            if len(self.xact_batch) == BATCH_SIZE or len(self.xact_queue) == 0:
                # print("BATCH equals BATCH_SIZE or QUEUE is EMPTY")
                self.xact_batch.sort(key=lambda xacts: xacts.timestamp)
                self.batch_ready = True

    def enqueue_xact(self, transaction: Transaction):
        self.xact_queue.append(transaction)
        self.xacts_queued += 1

    def kill_threads(self):
        self.kill_thread = True

    def check_for_completed_xacts(self):
         for xact in self.transaction:
             if self.xact_meta_data[xact.id][0] == len(self.xact_meta_data[xact.id][1]):
                 self.xact_meta_data[xact.id][2] = True
                 ret_list = self.xact_meta_data[xact.id][1]
                 xact.set_return_values(ret_list)
                 print(f'TRANSACTION {xact.id + 1} return = {xact.get_return_values()}')
                 self.transaction.remove(xact)
                 self.xacts_completed += 1


class Group:
    """
    Holds queues of Transactions
    """
    def __init__(self):
        self.queues = [deque() for i in range(PRIORITY_QUEUE_COUNT)]


class PlanningWorker:
    """
    PlanningWorkers are responsible for moving transactions to the PriorityGroups
    """

    def __init__(self, priority_group: Group, batcher: Batcher):
        self.group = priority_group
        self.batcher = batcher
        self.planner_thread = threading.Thread(target=self.do_work, args=(lambda : self.batcher.kill_thread,))
        self.planner_thread.daemon = False
        self.planner_thread.start()

    def do_work(self, stop):
        # print('PLANNER STARTING')

        while True:

            if stop():
                break

            time.sleep(.001)

            if self.batcher.batch_ready:
                # print(f'PLANNING - current batch: {self.batcher.xact_batch}')
                # moved sort to batch ready check
                for xact in self.batcher.xact_batch:

                    xact.id = self.batcher.xact_count
                    self.batcher.transaction.append(xact)
                    self.batcher.xact_meta_data[xact.id] = [len(xact.queries), [], False]
                    self.batcher.xact_count += 1

                    for query in xact.queries:
                        # print(f'IN PLANNING WORKER DO WORK: {query.query_name}')
                        query.set_xact_id(xact.id)
                        index = query.key % PRIORITY_QUEUE_COUNT
                        self.group.queues[index].append(query)

                self.batcher.xact_batch =[]

            if len(self.batcher.xact_batch) == 0:
                self.batcher.batch_ready = False


class ExecutionWorker:
    """
    ExecutionWorkers are responsible for executing transactions in the PriorityGroups
    """
    def __init__(self, batcher: Batcher, queue_index: int):
        self.batcher = batcher
        self.assigned_index = queue_index
        self.exec_thread = threading.Thread(target=self.do_execution, args=(lambda : self.batcher.kill_thread,))
        self.exec_thread.daemon = False
        self.exec_thread.start()

    def do_execution(self, stop):
        # print(f'EXECUTOR {self.assigned_index} STARTING')

        while True:

            if stop():
                break

            time.sleep(.001)

            if len(self.batcher.high_priority_group.queues[self.assigned_index]) > 0:
                # print(f'EXECUTING {self.assigned_index}')

                q_op = self.batcher.high_priority_group.queues[self.assigned_index].popleft()
                # print(f'RUNNING {q_op.query_name} BY WORKER {self.assigned_index}')
                ret = q_op.run()
                self.batcher.xact_meta_data[q_op.xact_id][1].append(ret)


class InternWorker:
    """
    Handles our shit
    """
    def __init__(self, batcher: Batcher):
        self.batcher = batcher
        self.intern_thread = threading.Thread(target=self.batcher_maintenance,
                                              args=(lambda : self.batcher.kill_thread,))
        self.intern_thread.daemon = False
        self.intern_thread.start()

    def batcher_maintenance(self, stop):
        # print("STARTING INTERN")

        while True:

            if stop():
                break

            time.sleep(.01)

            if not self.batcher.batch_ready:
                self.batcher.batch_xact()

            self.batcher.check_for_completed_xacts()
