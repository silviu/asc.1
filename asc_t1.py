#!/usr/bin/python
from threading import *
from asc_t1_defs import *
from synced_list import *
import echo
import sys

global barrier, N_Threads, IDLE, BUSY
N_Threads = 0

IDLE = 0
BUSY = 1
EXIT_TIME = False

class ReBarrier:
	def __init__(self):
		self.b1 = Barrier()
		self.b2 = Barrier()
		
	def sync(self):
		self.b1.sync()
		self.b2.sync()
	
	def end_requests(self, whom):
		#print "~~PAS 1~~ Thread " + str(whom) + " finished waiting for requests"
		self.sync()
	
	def end_process_requests(self, whom):
		#print "~~PAS 2~~ Thread " + str(whom) + " finished processing requests"
		self.sync()
	
	def end_reply_requests(self, whom):
		#print "~~PAS 3~~ Thread " + str(whom) + " finished replying to requests"
		self.sync()
	
	def end_process_answers(self, whom):
		#print "~~PAS 4~~ Thread " + str(whom) + " finished processing answers"
		self.sync()

class Barrier:
	def __init__(self):
		global N_Threads
		self.barrier    = Semaphore(value=0)
		self.regcritica = Semaphore(value=1)
		self.n = 0
 
	def sync(self):
		global N_Threads
		self.regcritica.acquire()
		self.n += 1
		if  self.n == N_Threads:
			for i in range(N_Threads):
				self.barrier.release()
			self.n = 0
		self.regcritica.release()
		self.barrier.acquire()


barrier = ReBarrier()

class Ram(GenericRAM):
	
	def __init__(self, num_ram_cells, num_ram_requests_per_time_step, system_manager):
		Thread.__init__(self)
		self.num_ram_cells = num_ram_cells
		self.num_ram_requests_per_time_step = num_ram_requests_per_time_step
		self.system_manager = system_manager
		self.ram = [None] * num_ram_cells
		self.rid = 0
		
		self.curr_req = Synced_list()
		self.old_req = []
	
	
	# Sets RAM cell at addr address to value
	#@echo.echo
	def set_cell_value(self, addr, value):
		self.ram[addr] = value
	
	
	# Returns the RAM value at addr address
	##@echo.echo
	def get_cell_value(self, addr):
		return self.ram[addr]
		
	
	# Accepts requests from the CACHE
	##@echo.echo
	def request(self, addr, cache):
		self.curr_req.append((addr, cache))
		dbg("~~~~~~CACHE " + str(cache) + " is requesting from RAM addr= " + str(addr))
	
	
	#Responds to every CACHE for their previous requests
	##@echo.echo
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			cache = req[1]
			cache.get_answer_from_Ram(addr, value)
			self.rid += 1
			self.system_manager.ram_notify_submit_answer(cache, self.rid, addr)
			dbg("~~~~~~RAM " + str(self) + " is responding to CACHE for addr= " + str(addr) + " value= " + str(value))
	
	# Prepares the lists for a new time step
	##@echo.echo
	def prepare_list(self):
		self.old_req = self.curr_req.list
		self.curr_req.list = []
	
	##@echo.echo
	def run(self):
		self.system_manager.register_ram(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return

			barrier.end_requests(self)
			
			self.prepare_list()
			barrier.end_process_requests(self)
			
			if len(self.old_req) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)
			

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
		self.old_answer = []
		
		self.curr_req = Synced_list()
		self.old_req = []
	
	# Tries to get the value from the CACHE at "addr" address
	# If the "addr" address is not mapped in the cache
	# the function returns "None"
	#@echo.echo
	def get_cell_value(self, addr):
		for cache_cell in self.cache:
			if cache_cell[0] == addr:
				return cache_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the CACHE. If there is no mapping for this adress, 
	# it is added to the CACHE
	#@echo.echo
	def set_cell_value(self, addr, value):
		for i, cache_cell in enumerate(self.cache):
			if cache_cell[0] == addr:
				cache_cell[1] = value
				return i
		self.cache.append([addr, value])
		return len(self.cache)
	
	# This method will be called from the RAM
	# It receives answers to previous requests from the RAM
	#@echo.echo
	def get_answer_from_Ram(self, addr, value):
		curr_answer.append([addr, value])
		dbg("~~~~~~CACHE " + str(self) + " is getting answer from RAM for addr= " + str(addr) + " value= " + str(value))
	
	# Accepts requests from REGISTERS and it adds them to a queue
	#@echo.echo
	def request(self, addr, register):
		self.curr_req.append([addr, register])
		dbg("~~~~~~REGISTER " + str(register) + " is requesting from CACHE for addr= " + str(addr))
	
	def send_ram_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			register = req[1]

			# If the address/value is not in the CACHE
			# request the value from the RAM and maintain
			# de request in the curr_req so that it will be
			# processed at the next time step
			if value == None:
				self.ram.request(addr, self)
				self.ram_rid += 1
				self.system_manager.cache_notify_submit_request(self.ram_rid, addr)
				self.curr_req.append([addr, register])
		
	
	# Responds to each REGISTER for its request
	#@echo.echo
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = get_cell_value(req[0])
			register = req[1]
			
			# If the value is still not in the CACHE
			# check if it in the answers list
			if value == None:
				for answer in self.old_answer:
					if answer[0] == addr:
						value = answer[1]
						position = self.set_cell_value(addr, value)
						self.system_manager.cache_notify_store_value(position, addr)
						break
			# If the value is not in the CACHE nor in the answers list
			if value == None:
				continue
			
			dbg("~~~~~~CACHE " + str(self) + " is responding to REGISTER for addr= " + str(addr) + " value= " + str(value))
			register.get_answer_from_Cache(addr, value)
			self.old_req.remove([addr, value])
			self.reg_rid += 1
			self.system_manager.cache_notify_submit_answer(register.register_set, self.reg_rid, addr)
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_list(self):
		self.old_req.extend(self.curr_req.list)
		self.curr_req.list = []
	
	def prepare_answer_list(self):
		self.old_answer = self.curr_answer.list
		self.curr_answer.list = []

	#@echo.echo
	def run(self):
		self.system_manager.register_cache(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			if len(self.old_req) > 0:
				self.send_ram_requests()
			barrier.end_requests(self)
					
			self.prepare_request_list()
			barrier.end_process_requests(self)
			

			if len(self.old_req) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)
			
				
			self.prepare_answer_list()
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
		self.old_req  = []
		
		self.curr_answer = Synced_list()
		self.old_answer  = []
		
	# Tries to get the value from the REGISTER at "addr" address
	# If the "addr" address is not mapped in the REGISTER
	# the function returns "None"
	#@echo.echo
	def get_cell_value(self, addr):
		for register_cell in self.register_set:
			if register_cell[0] == addr:
				return register_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the REGISTER. If there is no mapping for this adress, 
	# it is added to the REGISTER
	#@echo.echo
	def set_cell_value(self, addr, value):
		for i, register_cell in enumerate(self.register_set):
			if register_cell[0] == addr:
				register_cell[1] = value
				return i
		self.register_set.append([addr, value])
		return register_set.get_len()
	
	# Accepts requests from the processor it is connected to
	#@echo.echo
	def request(self, addr, processor):
		self.curr_req.append([addr, processor])
		dbg("~~~~~~PROCESSOR " + str(processor) + " is requesting REGISTER for addr= " + str(addr))

	#@echo.echo
	def get_answer_from_Cache(self, addr, value):
		self.curr_answer.append([addr, value])
		dbg("~~~~~~REGISTER " + str(self) + " is receives answer from CACHE for addr= " + str(addr) + " value= " + str(value))
	
	#@echo.echo
	def process_cache_answers(self):
		for answer in self.old_answer:
			dbg("~~~~~~REGISTER " + str(self) + " is processing answer from CACHE for addr= " + str(answer[0]) + " value= " + str(answr[1]))
			position = self.set_cell_value(answer[0], answer[1])
			self.system_manager.register_set_notify_store_value(position, answer[0])
			
	
	def send_cache_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			processor = req[1]
			
			# If the address/value is not in the REGISTER
			# request the value from the CACHE

			if value == None:
				self.cache.request(addr, self)################################################################################
				self.rid += 1
				self.system_manager.register_set_notify_submit_request(self.cache, self.rid, addr)
			# If the value is in the REGISTER send it to the PROCE

	# Responds to the Processor for its request
	#@echo.echo
	def respond_requests(self):
		for req in self.old_req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			processor = req[1]
			
			# If the address/value is not in the REGISTER yet
			# it may be in the answer list from cache
			if value == None:
				for answer in self.old_answer:
					if answer[0] == addr:
						value = answer[1]
						self.set_cell_value([addr, value])
						break
			
			# If addr is not in REGISTER and not in the answers list
			# send the next value and wait for this one for more
			if value == None:
				continue
				
			dbg("~~~~~~REGISTER " + str(self) + " is responding to PROCESSOR for addr= " + str(addr) + " value= " + str(value))
			processor.get_answer_from_Register(addr, value)
			self.old_proc.remove([addr, value])
			self.rid += 1
			self.system_manager.register_set_notify_submit_answer(processor, self.rid, addr)	

	
	# Prepares the lists for a new time step	
	#@echo.echo
	def prepare_request_list(self):
		# some cache requests may take more time
		# so it is best to extend the list and remove
		# items when we respond to the PROCESSOR
		self.old_req.extend(self.curr_req.list)
		self.curr_req.list = []
	
	def prepare_answer_lists(self):
		self.old_answer = self.curr_answer.list
		self.curr_answer.list = []
	
	
	#@echo.echo
	def run(self):
		self.system_manager.register_register_set(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting or sending requests
			self.send_cache_requests()
			barrier.end_requests(self)
			
			# Interchange shared request list with my local list 
			self.prepare_request_list()
			barrier.end_process_requests(self)
			
			# Replying to requests
			if len(self.old_req) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)

			# Processing answers
			if len(self.old_req) > 0:
				self.process_cache_answers()
				
			self.prepare_answer_lists()
			barrier.end_process_answers(self)
			
				

class Processor(GenericProcessor):
	global IDLE, BUSY
	def __init__(self, register_set, system_manager):
		Thread.__init__(self)
		self.register_set = register_set
		self.system_manager = system_manager
		self.state = IDLE
		self.rid = 0
		self.process = None
		self.operation_index = 0
		self.operations_left = 0
		self.sent_register_requests = 0
		self.operand = None
		
		self.curr_proc = Synced_list()
		self.old_proc = []
		
		self.register_answers = Synced_list()
		
	#@echo.echo
	def get_process_number(self):
		return self.curr_proc.get_len()
		
	# This method is called by the ProcessScheduler
	# and it adds a new process in the queue
	#@echo.echo
	def add_processes(self, process, scheduler):
		self.curr_proc.append(process)
		self.scheduler = scheduler
		dbg("~~~~~~PROCESSOR " + str(self) + " received a process from the SCHEDULER; process =" + str(process))
		
	#@echo.echo
	def get_answer_from_Register(self, addr, value):
		register_answers.append([addr, value])
		dbg("~~~~~~PROCESSOR" + str(self) + " received an answer from REGISTER for addr= " + str(addr) + " value= " + str(value))
	
	#@echo.echo
	def is_in_answers(self, addr):
		for answer in self.register_answers.list:
			if answer[0] == addr:
				return True
		return False
	
	# Returns the maximum number of operations
	# a process has done 
	#@echo.echo
	def get_max_operations(self):
		max_op = 0
		for proc in self.old_proc:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op > max_op:
				max_op = curr_op
		return max_op
	
	# Returns a process from the process list to be run next
	# It is chosen by the max number of operations it already has done
	#@echo.echo
	def get_process_to_run(self):
		max_op = self.get_max_operations()
		
		for proc in self.old_proc:
			curr_op = proc.get_number_of_executed_operations()
			if curr_op == max_op:
				return proc

	
	def send_register_requests(self):
		if self.state == IDLE:
			if not self.is_in_answers(self.addr1):
				self.register_set.request(self.addr1, self)
				self.rid += 1
				self.sent_register_requests += 1
				self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr1)
			
			if not self.is_in_answers(self.addr2):
				self.register_set.request(self.addr2, self)
				self.rid += 1
				self.sent_register_requests += 1
				self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr2)
				
	
	def get_next_operation(self):
		if self.process == None:
			return None
			
		# If there are no more operations left to run return None
		if self.operation_index > self.process.get_number_of_operations():
			return None
		
		# Get next operation
		self.operation = self.process.get_operation(self.operation_index)
		self.operation_index += 1
		
		# Initialize Register requests counter that is used to decide
		# when to start running the operation 
		# (sent_register_requests == number of replies from the Register)
		self.sent_register_requests = 0
		
		# operand = "+" or "*"
		# addr1 and addr2 are the RAM adresses where the values
		# to be added or multiplied
		# TODO in viitor pot primi si "+ 2 3 4 5 3 9". va fi nevoie de o lista
		self.operand = self.operation[0]
		self.addr1   = self.operation[1]
		self.addr2   = self.operation[2]
	
	
	def remove_element(self, elem):
		for proc in self.old_proc:
			if proc == elem:
				self.old_proc.remove(proc)
				return
			
	# Implements the behavour of the PROCESSOR
	#@echo.echo
	def run_process(self):	
		if self.state == IDLE:
			print "\n\n !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!``````BUSYYY````````!!!!!!!!!!!!!!!!!!!\n\n"
			
			# Get number of operations left
			if not self.process == None:
				self.operations_left = self.process.get_number_of_operations() - self.process.get_number_of_executed_operations()
			
			# If current process finished all its operations
			# remove it from the processes list
			if self.operations_left == 0:
				self.remove_element(self.process)
				self.process = None
				self.operation_index = 0
			
			# If running the first time of if the processor finished all
			# operations for this process get another process from the queue
			if self.process == None:
				self.process = self.get_process_to_run()
				self.get_next_operation()
				self.state = BUSY

			# If the current process has multiple operations
			else:
				self.get_next_operation()
				self.state = BUSY
				
		if self.state == BUSY:
			if self.process == None:
				self.state = IDLE
				return
			
			print "\n\n !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!``````BUSYYY````````!!!!!!!!!!!!!!!!!!!\n\n"
			self.system_manager.processor_notify_start_executing_next_operation(self.process) 
			if self.sent_register_requests == self.register_answers.get_len():
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
	
	
	# Calculates the sum of all operations in all processes
	# of the current PROCESSOR
	def get_sum_operations(self):
		suma = 0
		for baba in self.old_proc:
			suma += baba.get_number_of_operations()
		return suma
	
	# Sends the sum of all operations in all processes
	# of the current PROCESSOR to the SCHEDULER
	def reply_to_scheduler(self):
		suma = self.get_sum_operations()
		self.scheduler.get_processor_info_from_Processor([self, suma])
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_lists(self):
		self.old_proc.extend(self.curr_proc.list)
		self.curr_proc.list = []

	#@echo.echo
	def run(self):
		self.system_manager.register_processor(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# If the processor has not just started, therefore 
			# it has something to request
			if len(self.old_proc) > 0:
				self.send_register_requests()
			barrier.end_requests(self)
			

			self.prepare_request_lists()
			barrier.end_process_requests(self)
			
			# If there are any processes on this processor
			# send info of them to the scheduler
			if len(self.old_proc) > 0:
				self.reply_to_scheduler()
			barrier.end_reply_requests(self)
			
			# First time it enters for both are 0
			if len(self.old_proc) > 0:
				self.run_process()
			barrier.end_process_answers(self)
			

class ProcessScheduler(GenericProcessScheduler):
	def __init__(self, processor_list, system_manager):
		Thread.__init__(self)
		self.processor_list = processor_list
		self.system_manager = system_manager
		
		self.old_proc_info = []
		self.curr_proc_info = Synced_list()
		
		self.old_proc  = []
		self.curr_proc = Synced_list()
	
	#@echo.echo
	def submit_process(self, process):
		self.curr_proc.append(process)
		dbg("~~~~~~SCHEDULER " + str(self) + " received a process from SYSTEM_MANAGER; process= " + str(process))

	#@echo.echo
	def get_processor(self):
		min_proc = sys.maxint
		for processor in self.processor_list:
			if processor.get_process_number() < min_proc:
				min_proc = processor.get_process_number()
				saved_processor = processor
		return saved_processor
	
	def get_processor_info_from_Processor(self, info):
		self.curr_proc_info.append(info)
		dbg("~~~~~~SCHEDULER " + str(self) + " received processor info from PROCESSOR = " + str(info[0]) + " info= " + str(info[1]))
	
	#@echo.echo
	def schedule_processes(self):
		for process in self.old_proc:
			processor = self.get_processor()
			processor.add_processes(process, self)  # TRIMITERE CERERE
			self.system_manager.scheduler_notify_submit_process(processor, process)

	# Prepares the lists for a new time step
	#@echo.echo	
	def prepare_request_lists(self):
		self.old_proc = self.curr_proc.list
		self.curr_proc.list = []
	
	def prepare_answer_lists(self):
		self.old_proc = self.curr_proc.list
		self.curr_proc.list = []
	
	#@echo.echo
	def run(self):
		self.system_manager.register_scheduler(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			

			if len(self.old_proc) > 0:
				self.schedule_processes()
			barrier.end_requests(self)
			

			self.prepare_request_lists()
			barrier.end_process_requests(self)
			

			barrier.end_reply_requests(self)
			
			self.prepare_answer_lists()
			barrier.end_process_answers(self)
			

def init():
	pass

def dbg(msg):
	print "\n" + msg

	
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

