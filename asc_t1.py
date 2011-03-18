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
		
		self.curr_req = []
		self.old_req = []
	
	
	# Sets RAM cell at addr address to value
	def set_cell_value(self, addr, value):
		self.ram[addr] = value
	
	
	# Returns the RAM value at addr address
	def get_cell_value(self, addr):
		return self.ram[addr]
		
	
	# Accepts requests from the CACHE
	def get_requests(self, addr, cache):
		self.curr_req.append((addr, cache))
	
	
	#Responds to every CACHE for their previous requests
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			cache = req[1]
			cache.get_answer(addr, value)
	
	# Prepares the lists for a new time step
	def prepare_lists(self):
		self.old_req = self.curr_req
		self.curr_req = []
	
	
	def run(self):
		self.system_manager.register_ram(self)
		self.respond_requests()
		self.prepare_lists()
		barrier.sync()
		


class MyCache(GenericCache):
	def __init__(self, num_cache_cells, ram, system_manager):
		Thread.__init__(self)
		self.num_cache_cells = num_cache_cells
		self.ram = ram
		self.system_manager = system_manager
		self.cache = [None] * num_cache_cells
		
		self.curr_answer = []
		self.old_answer = []
		
		self.curr_req = []
		self.old_req = []
	
	# Tries to get the value from the CACHE at "addr" address
	# If the "addr" address is not mapped in the cache
	# the function returns "None"
	def get_cell_value(self, addr):
		for cache_cell in self.cache:
			if cache_cell[0] == addr:
				return cache_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the CACHE. If there is no mapping for this adress, 
	# it is added to the CACHE
	def set_cell_value(self, addr, value):
		for cache_cell in self.cache:
			if cache_cell[0] == addr:
				cache_cell[1] = value
				return
		self.cache.append([addr, value])
	
	# This method will be called from the RAM
	# It receives answers to previous requests from the RAM
	def get_answer(self, addr, value):
		curr_answer.append([addr, value])	
	
	# Accepts requests from REGISTERS and it adds them to a queue
	def get_requests(self, addr, register):
		self.curr_req.append([addr, register])
	
	# Responds to each REGISTER for its request
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			register = req[1]
			
			# If the address/value is not in the CACHE
			# request the value from the RAM and maintain
			# de request in the curr_req so that it will be
			# processed at the next time step
			if (value == None):
				self.ram.get_requests(addr, self)
				self.curr_req.append([addr, register])
			# If the value is in the CACHE send it to the REGISTER
			else:
				register.get_answer(addr, value)
	
	
	# Inserts the values it got from the RAM into the CACHE
	def process_ram_answers(self):
		for answer in self.old_answer:
			self.set_cell_value(answer[0], answer[1])
	
	
	# Prepares the lists for a new time step	
	def prepare_lists(self):
		self.old_answer = self.curr_answer
		self.curr_answer = []
		self.old_req = self.curr_req
		self.curr_req = []
	
	def run(self):
		self.system_manager.register_cache(self)
		self.respond_requests()
		self.process_ram_answers()
		self.prepare_lists()
			
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

