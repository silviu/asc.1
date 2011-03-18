from threading import *
from asc_t1_defs import *
from barrier import *

global barrier, N_Threads
N_Threads = 0
barrier = ReBarrier(N_Threads + 1)

class MyRam(GenericRAM):
	
	def __init__(self, num_ram_cells, num_ram_requests_per_time_step, system_manager):
		Thread.__init__(self)
		self.num_ram_cells = num_ram_cells
		self.num_ram_requests_per_time_step = num_ram_requests_per_time_step
		self.system_manager = system_manager
		self.ram = [None] * num_ram_cells

	def set_cell_value(self, addr, value):
		self.ram[addr] = value

	def run(self):
		self.system_manager.register_ram(self)
		barrier.sync()
		


class MyCache(GenericCache):
	def __init__(self, num_cache_cells, ram, system_manager):
		Thread.__init__(self)
		self.num_cache_cells = num_cache_cells
		self.ram = ram
		self.system_manager = system_manager
		self.cache = [None] * num_cache_cells

	def run(self):
		self.system_manager.register_cache(self)
		barrier.sync()


class MyRegisterSet(GenericRegisterSet):
	def __init__(self, num_register_cells, cache, system_manager):
		Thread.__init__(self)
		self.num_register_cells = num_register_cells
		self.cache = cache
		self.system_manager = system_manager

	def run(self):
		self.system_manager.register_register_set(self)
		barrier.sync()

class MyProcessor(GenericProcessor):
	def __init__(self, register_set, system_manager):
		Thread.__init__(self)
		self.register_set = register_set
		self.system_manager = system_manager

	def run(self):
		self.system_manager.register_processor(self)
		barrier.sync()


class MyProcessScheduler(GenericProcessScheduler):
    def __init__(self, process_list, system_manager):
        Thread.__init__(self)
        self.process_list = process_list
        self. system_manager = system_manager

    def submit_process(self, process):
        todo("MyProcessScheduler:submit_process()")
        
        

    def run(self):
    	self.system_manager.register_scheduler(self)
    	barrier.sync()
        


def todo(function):
	print "~~~~~TODO: " + function + " ~~~~~"

def init():
	pass


	
def get_RAM(num_ram_cells, num_ram_requests_per_time_step, system_manager):
	global N_Threads
	N_Threads += 1
	return MyRam(num_ram_cells, num_ram_requests_per_time_step, system_manager)

def get_cache(num_cache_cells, ram, system_manager):
	global N_Threads
	N_Threads += 1
	return MyCache(num_cache_cells, ram, system_manager)

def get_register_set(num_register_cells, cache, system_manager):
	global N_Threads
	N_Threads += 1
	return MyRegisterSet(num_register_cells, cache, system_manager)
    
def get_processor(register_set, system_manager):
	global N_Threads
	N_Threads += 1
	return MyProcessor(register_set, system_manager)

def get_process_scheduler(process_list, system_manager):
	global N_Threads
	N_Threads += 1
	return MyProcessScheduler(process_list, system_manager)

def wait_for_next_time_step(object, done):
	
	if done == 0:
		barrier.sync()
		object.increase_time_step()

	if done == 1:
		exit()

