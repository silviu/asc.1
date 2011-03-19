#!/usr/bin/python
from threading import *
from asc_t1_defs import *
from barrier import *
from synced_list import *
import echo
import sys

global barrier, N_Threads, IDLE, BUSY
N_Threads = 0
barrier = ReBarrier(N_Threads + 1)
IDLE = 0
BUSY = 1
EXIT_TIME = False

class Ram(GenericRAM):
	
	def __init__(self, num_ram_cells, num_ram_requests_per_time_step, system_manager):
		Thread.__init__(self)
		self.num_ram_cells = num_ram_cells
		self.num_ram_requests_per_time_step = num_ram_requests_per_time_step
		self.system_manager = system_manager
		self.ram = [None] * num_ram_cells
		self.rid = 0
		
		self.curr_req = Synced_list()
		self.old_req = Synced_list()
	
	
	# Sets RAM cell at addr address to value
	@echo.echo
	def set_cell_value(self, addr, value):
		self.ram[addr] = value
	
	
	# Returns the RAM value at addr address
	@echo.echo
	def get_cell_value(self, addr):
		return self.ram[addr]
		
	
	# Accepts requests from the CACHE
	@echo.echo
	def request(self, addr, cache):
		self.curr_req.append((addr, cache))
	
	
	#Responds to every CACHE for their previous requests
	@echo.echo
	def respond_requests(self):
		for req in self.old_req.list:
			addr  = req[0]
			value = get_cell_value(req[0])
			cache = req[1]
			cache.get_answer_from_Ram(addr, value)
			self.rid += 1
			self.system_manager.ram_notify_submit_answer(cache, self.rid, addr)
	
	# Prepares the lists for a new time step
	@echo.echo
	def prepare_lists(self):
		self.old_req.list = self.curr_req.list
		self.curr_req.list = []
	
	@echo.echo
	def run(self):
		self.system_manager.register_ram(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			# Accepting requests
			barrier.end_requests(self)
			
			# Processing requests
			barrier.end_process_requests(self)
			
			# Replying to requests
			barrier.end_reply_requests(self)
			if self.old_req.get_len() > 0:
				self.respond_requests()
				self.prepare_lists()
			
			# Processing answers
			barrier.end_process_answers(self)
			


class Cache(GenericCache):
	def __init__(self, num_cache_cells, ram, system_manager):
		Thread.__init__(self)
		self.num_cache_cells = num_cache_cells
		self.ram = ram
		self.system_manager = system_manager
		self.cache = num_cache_cells * [None]
		self.ram_rid = 0
		self.reg_rid = 0
		
		self.curr_answer = Synced_list()
		self.old_answer = Synced_list()
		
		self.curr_req = Synced_list()
		self.old_req = Synced_list()
	
	# Tries to get the value from the CACHE at "addr" address
	# If the "addr" address is not mapped in the cache
	# the function returns "None"
	@echo.echo
	def get_cell_value(self, addr):
		for cache_cell in self.cache:
			if cache_cell[0] == addr:
				return cache_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the CACHE. If there is no mapping for this adress, 
	# it is added to the CACHE
	@echo.echo
	def set_cell_value(self, addr, value):
		for i, cache_cell in enumerate(self.cache):
			if cache_cell[0] == addr:
				cache_cell[1] = value
				return i
		self.cache.append([addr, value])
		return len(self.cache)
	
	# This method will be called from the RAM
	# It receives answers to previous requests from the RAM
	@echo.echo
	def get_answer_from_Ram(self, addr, value):
		curr_answer.append([addr, value])	
	
	# Accepts requests from REGISTERS and it adds them to a queue
	@echo.echo
	def request(self, addr, register):
		self.curr_req.append([addr, register])
	
	# Responds to each REGISTER for its request
	@echo.echo
	def respond_requests(self):
		for req in self.old_req.list:
			addr  = req[0]
			value = get_cell_value(req[0])
			register = req[1]
			
			# If the address/value is not in the CACHE
			# request the value from the RAM and maintain
			# de request in the curr_req so that it will be
			# processed at the next time step
			if (value == None):
				self.ram.request(addr, self)
				self.ram_rid += 1
				self.system_manager.cache_notify_submit_request(self.ram_rid, addr)
				self.curr_req.append([addr, register])
			# If the value is in the CACHE send it to the REGISTER
			else:
				register.get_answer_from_Cache(addr, value)
				self.reg_rid += 1
				self.system_manager.cache_notify_submit_answer(register.register_set, self.reg_rid, addr)
	
	
	# Inserts the values it got from the RAM into the CACHE
	@echo.echo
	def process_ram_answers(self):
		for answer in self.old_answer.list:
			position = self.set_cell_value(answer[0], answer[1])
			self.system_manager.cache_notify_store_value(position, answer[0])
	
	
	# Prepares the lists for a new time step
	@echo.echo
	def prepare_lists(self):
		self.old_answer.list = self.curr_answer.list
		self.curr_answer.list = []
		self.old_req.list = self.curr_req.list
		self.curr_req.list = []

	@echo.echo
	def run(self):
		self.system_manager.register_cache(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting requests
			barrier.end_requests(self)
			
			# Processing requests
			barrier.end_process_requests(self)
			
			# Replying to requests
			if self.old_req.get_len() > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)
			
				
			# Processing answers
			if self.old_answer.get_len() > 0:
				self.process_ram_answers()
				self.prepare_lists()
			barrier.end_process_answers(self)
			
			

class RegisterSet(GenericRegisterSet):
	def __init__(self, num_register_cells, cache, system_manager):
		Thread.__init__(self)
		self.num_register_cells = num_register_cells
		self.cache = cache
		self.system_manager = system_manager
		self.register_set = num_register_cells * [None]
		self.rid = 0
		
		self.curr_req = Synced_list()
		self.old_req  = Synced_list()
		
		self.curr_answer = Synced_list()
		self.old_answer  = Synced_list()
		
	# Tries to get the value from the REGISTER at "addr" address
	# If the "addr" address is not mapped in the REGISTER
	# the function returns "None"
	@echo.echo
	def get_cell_value(self, addr):
		for register_cell in self.register_set:
			if register_cell[0] == addr:
				return register_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the REGISTER. If there is no mapping for this adress, 
	# it is added to the REGISTER
	@echo.echo
	def set_cell_value(self, addr, value):
		for i, register_cell in enumerate(self.register_set):
			if register_cell[0] == addr:
				register_cell[1] = value
				return i
		self.register_set.append([addr, value])
		return register_set.get_len()
	
	# Accepts requests from the processor it is connected to
	@echo.echo
	def request(self, addr, processor):
		self.curr_req.append([addr, processor])

	@echo.echo
	def get_answer_from_Cache(self, addr, value):
		self.curr_answer.append([addr, value])
	
	@echo.echo
	def process_cache_answers(self):
		for answer in self.old_answer.list:
			position = self.set_cell_value(answer[0], answer[1])
			self.system_manager.register_set_notify_store_value(position, answer[0])
			
	
	# Responds to the Processor for its request
	@echo.echo
	def respond_requests(self):
		for req in self.old_req.list:
			addr  = req[0]
			value = get_cell_value(req[0])
			processor = req[1]
			
			# If the address/value is not in the REGISTER
			# request the value from the CACHE and maintain
			# de request in the curr_req so that it will be
			# processed at the next time step
			if (value == None):
				self.cache.request(addr, self)
				self.rid += 1
				self.system_manager.register_set_notify_submit_request(self.cache, self.rid, addr)
				self.curr_req.append([addr, processor])
			# If the value is in the REGISTER send it to the PROCESSOR
			else:
				processor.get_answer_from_Register(addr, value)
				self.rid += 1
				self.system_manager.register_set_notify_submit_answer(processor, self.rid, addr)
	
	# Prepares the lists for a new time step	
	@echo.echo
	def prepare_lists(self):
		self.old_answer.list = self.curr_answer.list
		self.curr_answer.list = []
		self.old_req.list = self.curr_req.list
		self.curr_req.list = []
		
	@echo.echo
	def run(self):
		self.system_manager.register_register_set(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting requests
			barrier.end_requests(self)
			
			# Processing requests
			barrier.end_process_requests(self)
			
			# Replying to requests
			if self.old_req.get_len() > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)

			# Processing answers
			if self.old_answer.get_len() > 0:
				self.process_cache_answers()
				self.prepare_lists()
			barrier.end_process_answers(self)
			
				

class Processor(GenericProcessor):
	global IDLE, BUSY
	def __init__(self, register_set, system_manager):
		Thread.__init__(self)
		self.register_set = register_set
		self.system_manager = system_manager
		self.state = IDLE
		self.rid = 0
		
		self.curr_proc = Synced_list()
		self.old_proc = Synced_list()
		
		self.register_answers = Synced_list()
		
	@echo.echo
	def get_process_number(self):
		return self.curr_proc.get_len()
		
	# This method is called by the ProcessScheduler
	# and it adds a new process in the queue
	@echo.echo
	def add_processes(self, process):
		self.curr_proc.append(process)
		
	@echo.echo
	def get_answer_from_Register(self, addr, value):
		register_answers.append([addr, value])
	
	@echo.echo
	def is_in_answers(self, addr):
		for answer in self.register_answers.list:
			if answer[0] == addr:
				return True
		return False
	
	# Returns the maximum number of operations
	# a process has done 
	@echo.echo
	def get_max_operations(self):
		max_op = 0
		for proc in self.old_proc.list:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op > max_op:
				max_op = curr_op
		return max_op
	
	# Returns a process from the process list to be run next
	# It is chosen by the max number of operations it already has done
	@echo.echo
	def get_process_to_run(self):
		max_op = self.get_max_operations()
		
		for proc in self.old_proc.list:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op == max_op:
				return proc
	
	# Implements the behavour of the PROCESSOR
	@echo.echo
	def run_process(self):
		self.process = self.get_process_to_run()
		if self.process == None:
			return
		self.num_operations = self.process.get_number_of_operations()
		if self.state == IDLE:
			print "\n\n !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!``````IDLEEEE````````!!!!!!!!!!!!!!!!!!!\n\n"
			for i in range(self.num_operations):
				self.operation = self.process.get_operation(i)
				
				self.operand = self.operation[0]
				self.addr1   = self.operation[1]
				self.addr2   = self.operation[2]
				
				if not self.is_in_answers(self.addr1):
					self.register_set.request(self.addr1, self)
					self.rid += 1
					self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr1)
				if not self.is_in_answers(self.addr2):
					self.register_set.request(self.addr2, self)
					self.rid += 1
					self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr2)
				
				self.state = BUSY
		
		elif self.state == BUSY:
			print "\n\n !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!``````BUSYYY````````!!!!!!!!!!!!!!!!!!!\n\n"
			if self.register_answers.get_len() == 2:
				self.system_manager.processor_notify_start_executing_next_operation(self.process) 
				if self.operand == "+":
					x = 0
					for answer in self.register_answers.list:
						x += answer[1]
				elif self.operand == "*":
					x = 1
					for answer in self.register_answers.list:
						x *= answer[1]
				self.process.inc_number_of_executed_operations()
				self.system_manager.processor_notify_finish_executing_operation(x)
				self.state = IDLE
	
	# Prepares the lists for a new time step
	@echo.echo
	def prepare_lists(self):
		self.old_proc.list = self.curr_proc.list
		self.curr_proc.list = []

	@echo.echo
	def run(self):
		self.system_manager.register_processor(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting requests
			if self.old_proc.get_len() > 0:
				self.run_process()
			barrier.end_requests(self)
			
			# Processing requests
			self.prepare_lists()
			barrier.end_process_requests(self)
			
			# Replying to requests
			barrier.end_reply_requests(self)
			
			# Process answers
			barrier.end_process_answers(self)
			

class ProcessScheduler(GenericProcessScheduler):
	def __init__(self, processor_list, system_manager):
		Thread.__init__(self)
		self.processor_list = processor_list
		self.system_manager = system_manager
		
		self.old_proc  = []
		self.curr_proc = Synced_list()
	
	@echo.echo
	def submit_process(self, process):
		self.curr_proc.append(process)

	@echo.echo
	def get_processor(self):
		min_proc = sys.maxint
		for process in self.processor_list:
			if process.get_process_number() < min_proc:
				min_proc = process.get_process_number()
				saved_process = process
		return saved_process
	
	@echo.echo
	def schedule_processes(self):
		for process in self.old_proc:
			processor = self.get_processor()
			processor.add_processes(process)
			self.system_manager.scheduler_notify_submit_process(processor, process)

	# Prepares the lists for a new time step
	@echo.echo	
	def prepare_lists(self):
		self.old_proc = self.curr_proc.list
		self.curr_proc.list = []
	
	@echo.echo
	def run(self):
		self.system_manager.register_scheduler(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting requests
			if len(self.old_proc) > 0:
				self.schedule_processes()
			barrier.end_requests(self)
			
			# Processing requests
			self.prepare_lists()
			barrier.end_process_requests(self)
			
			# Replying to requests
			barrier.end_reply_requests(self)
			
			# Process answers
			barrier.end_process_answers(self)
			

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
		barrier.end_requests(object)
		barrier.end_process_requests(object)
		barrier.end_reply_requests(object)
		barrier.end_process_answers(object)
		object.increase_time_step()


	if done == 1:
		global EXIT_TIME
		EXIT_TIME = True
		exit()

