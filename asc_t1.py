from threading import *
from asc_t1_defs import *
from barrier import *

global barrier, N_Threads, IDLE, BUSY
N_Threads = 0
barrier = ReBarrier(N_Threads + 1)
IDLE = 0
BUSY = 1

class Ram(GenericRAM):
	
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
	def request(self, addr, cache):
		self.curr_req.append((addr, cache))
	
	
	#Responds to every CACHE for their previous requests
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			cache = req[1]
			cache.get_answer_from_Ram(addr, value)
	
	# Prepares the lists for a new time step
	def prepare_lists(self):
		self.old_req = self.curr_req
		self.curr_req = []
	
	
	def run(self):
		self.system_manager.register_ram(self)
		self.respond_requests()
		self.prepare_lists()
		barrier.sync()
		


class Cache(GenericCache):
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
	def get_answer_from_Ram(self, addr, value):
		curr_answer.append([addr, value])	
	
	# Accepts requests from REGISTERS and it adds them to a queue
	def request(self, addr, register):
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
				self.ram.request(addr, self)
				self.curr_req.append([addr, register])
			# If the value is in the CACHE send it to the REGISTER
			else:
				register.get_answer_from_Cache(addr, value)
	
	
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


class RegisterSet(GenericRegisterSet):
	def __init__(self, num_register_cells, cache, system_manager):
		Thread.__init__(self)
		self.num_register_cells = num_register_cells
		self.cache = cache
		self.system_manager = system_manager
		self.register_set = num_register_cells * [None]
		
		self.curr_req = []
		self.old_req  = []
		
		self.curr_answer = []
		self.old_answer  = []
		
	# Tries to get the value from the REGISTER at "addr" address
	# If the "addr" address is not mapped in the REGISTER
	# the function returns "None"
	def get_cell_value(self, addr):
		for register_cell in self.register_set:
			if register_cell[0] == addr:
				return register_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the REGISTER. If there is no mapping for this adress, 
	# it is added to the REGISTER
	def set_cell_value(self, addr, value):
		for register_cell in self.register_set:
			if register_cell[0] == addr:
				register_cell[1] = value
				return
		self.register_set.append([addr, value])
	
	# Accepts requests from the processor it is connected to
	def request(self, addr, processor):
		curr_req.append([addr, processor])

	def get_answer_from_Cache(self, addr, value):
		curr_answer.append([addr, value])
	
	def process_cache_answers(self):
		for answer in self.old_answer:
			self.set_cell_value(answer[0], answer[1])
			
	
	# Responds to the Processor for its request
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			processor = req[1]
			
			# If the address/value is not in the REGISTER
			# request the value from the CACHE and maintain
			# de request in the curr_req so that it will be
			# processed at the next time step
			if (value == None):
				self.cache.request(addr, self)
				self.curr_req.append([addr, processor])
			# If the value is in the REGISTER send it to the PROCESSOR
			else:
				processor.get_answer_from_Register(addr, value)
	
	# Prepares the lists for a new time step	
	def prepare_lists(self):
		self.old_answer = self.curr_answer
		self.curr_answer = []
		self.old_req = self.curr_req
		self.curr_req = []
	
	def run(self):
		self.system_manager.register_register_set(self)
		self.respond_requests()
		self.process_cache_answers()
		self.prepare_lists()
		barrier.sync()


class Processor(GenericProcessor):
	global IDLE, BUSY
	def __init__(self, register_set, system_manager):
		Thread.__init__(self)
		self.register_set = register_set
		self.system_manager = system_manager
		self.state = IDLE
		
		self.curr_proc = []
		self.old_proc = []
		
		self.register_answers = []
		
	def get_process_number(self):
		return len(curr_proc)
		
	# This method is called by the ProcessScheduler
	# and it adds a new process in the queue
	def add_processes(self, process):
		curr_proc.append(process)
		
	
	def get_answer_from_Register(self, addr, value):
		register_answers.append([addr, value])
	
	def is_in_answers(self, addr):
		for answer in register_answers:
			if answer[0] == addr:
				return True
		return False
	
	# Returns the maximum number of operations
	# a process has done 
	def get_max_operations(self):
		max_op = 0
		for proc in self.old_proc:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op > max_op:
				max_op = curr_op
		return max_op
	
	# Returns a process from the process list to be run next
	# It is chosen by the max number of operations it already has done
	def get_process_to_run(self):
		max_op = self.get_max_operations()
		
		for proc in self.old_proc:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op == max_op:
				return proc
	
	# Implements the behavour of the PROCESSOR
	def run_process(self):
		self.process = self.get_process_to_run()
		if self.process == None:
			return
		self.num_operations = self.process.get_number_of_operations()
		if self.state == IDLE:
			for i in range(num_operations):
				self.operation = process.get_operation(i)
				
				self.operand = operation[0]
				self.addr1   = operation[1]
				self.addr2   = operation[2]
				
				if not self.is_in_answers(addr1):
					self.register_set.request(addr1, self)
				if not self.is_in_answers(addr2):
					self.register_set.request(addr2, self)
				
				self.state = BUSY
		
		elif self.state == BUSY:
			self.get_answer_from_Register()
			if len(self.register_answers) == 2:
				if operand == "+":
					x = 0
					for answer in register_answers:
						x += answer[1]
				elif operand == "*":
					x = 1
					for answer in register_answers:
						x *= answer[1]
	
	def run(self):
		self.system_manager.register_processor(self)
		self.run_process()
		barrier.sync()


class ProcessScheduler(GenericProcessScheduler):
	def __init__(self, processor_list, system_manager):
		Thread.__init__(self)
		self.processor_list = processor_list
		self.system_manager = system_manager
		
		self.old_proc  = []
		self.curr_proc = []

	def submit_process(self, process):
		self.curr_proc.append(process)

	def get_processor(self):
		min_proc = sys.maxint
		for process in processor_list:
			if process.get_process_number() < min_proc:
				min_proc = process.get_process_number()
				saved_process = process
		return saved_process

	def schedule_processes(self):
		for process in self.old_proc:
			processor = self.get_processor()
			processor.add_processes(process)

	# Prepares the lists for a new time step	
	def prepare_lists(self):
		self.old_proc = self.curr_proc
		self.curr_proc = []

	def run(self):
		self.system_manager.register_scheduler(self)
		self.schedule_processes()
		barrier.sync()


def todo(function):
	print "~~~~~TODO: " + function + " ~~~~~"

def init():
	pass


	
def get_RAM(num_ram_cells, num_ram_requests_per_time_step, system_manager):
	global N_Threads
	N_Threads += 1
	return Ram(num_ram_cells, num_ram_requests_per_time_step, system_manager)

def get_cache(num_cache_cells, ram, system_manager):
	global N_Threads
	N_Threads += 1
	return Cache(num_cache_cells, ram, system_manager)

def get_register_set(num_register_cells, cache, system_manager):
	global N_Threads
	N_Threads += 1
	return RegisterSet(num_register_cells, cache, system_manager)
	
def get_processor(register_set, system_manager):
	global N_Threads
	N_Threads += 1
	return Processor(register_set, system_manager)

def get_process_scheduler(processor_list, system_manager):
	global N_Threads
	N_Threads += 1
	return ProcessScheduler(processor_list, system_manager)

def wait_for_next_time_step(object, done):
	
	if done == 0:
		barrier.sync()
		object.increase_time_step()

	if done == 1:
		exit()

