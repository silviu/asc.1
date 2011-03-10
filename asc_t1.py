from asc_t1_defs import *

class MyRam(GenericRAM):
	def __init__(self):
		Thread.__init__(self)

	def set_cell_value(self, addr, value):
		todo("MyRam:set_cell_value()")

	def run(self):
		todo("MyRam:run()")


class MyCache(GenericCache):
	def __init__(self):
		Thread.__init__(self)

	def run(self):
		todo("MyCache:run()")

class MyRegisterSet(GenericRegisterSet):
	def __init__(self):
		Thread.__init__(self)

	def run(self):
		todo("MyRegisterSet:run()")


class MyProcessor(GenericProcessor):
	def __init__(self):
		Thread.__init__(self)

	def run(self):
		todo("MyProcessor:run()")

class MyProcessScheduler(GenericProcessScheduler):
    def __init__(self):
        Thread.__init__(self)

    def submit_process(self, process):
        todo("MyProcessScheduler:submit_process()")

    def run(self):
        todo("MyProcessScheduler:run()")
        


def todo(function):
	print "~~~~~TODO: " + function + " ~~~~~"

def init():
    todo("init()")

def get_RAM(num_ram_cells, num_ram_requests_per_time_step, system_manager):
	return MyRam()

def get_cache(num_cache_cells, ram, system_manager):
	return MyCache()

def get_register_set(num_register_cells, cache, system_manager):
    return MyRegisterSet()
    
def get_processor(register_set, system_manager):
   return MyProcessor()

def get_process_scheduler(processor_list, system_manager):
    return MyProcessScheduler()
