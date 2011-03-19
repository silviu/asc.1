from threading import *

class Process:
    def __init__(self, operation_list):
        self.__operation_list = operation_list
        self.executed_ops = 0
    
    def get_number_of_operations(self):
        return len(self.__operation_list)
    
    def get_operation(self, i):
        return self.__operation_list[i]

    def get_number_of_executed_operations(self):
        return self.executed_ops

    def inc_number_of_executed_operations(self):
        self.executed_ops += 1

def wait_for_next_time_step(object, done):
    pass

class GenericRAM(Thread):
    def __init__(self):
        Thread.__init__(self)

    def set_cell_value(self, addr, value):
        pass

    def run(self):
        pass

class GenericCache(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass
    
class GenericRegisterSet(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass

class GenericProcessor(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass
    
class GenericProcessScheduler(Thread):
    def __init__(self):
        Thread.__init__(self)

    def submit_process(self, process):
        pass

    def run(self):
        pass

def init():
    pass

def get_RAM(num_ram_cells, num_ram_requests_per_time_step, system_manager):
    pass

def get_cache(num_cache_cells, ram, system_manager):
    pass

def get_register_set(num_register_cells, cache, system_manager):
    pass

def get_processor(register_set, system_manager):
    pass

def get_process_scheduler(processor_list, system_manager):
    pass
def wait_for_next_time_step(object, done):
	pass
