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
		
		self.sync_req = Synced_list()
		self.req = []
		self.old_requests = []
	
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
	def request(self, addr, cache, rid):
		self.sync_req.append([addr, cache, rid])
		dbg("CACHE        ] " + str(cache) + " is requesting from RAM addr= " + str(addr) + " RID = " + str(rid))
	
	
	#Responds to every CACHE for their previous requests
	##@echo.echo
	def respond_requests(self):
		for req in self.old_requests:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			cache = req[1]
			rid = req[2]
			
			cache.get_answer_from_Ram(addr, value)
			self.system_manager.ram_notify_submit_answer(cache, rid, addr)
			dbg("RAM          ] " + str(self) + " is responding to CACHE for addr= " + str(addr) + " value= " + str(value))
	
	# Prepares the lists for a new time step
	##@echo.echo
	def prepare_list(self):
		self.req = self.sync_req.list
		self.sync_req.list = []
	
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
			
			if len(self.old_requests) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)
			
			# aici pun elemente in lista 3. lista din care trimit raspunsuri
			self.old_requests = self.req
			barrier.end_process_answers(self)
			


class Cache(GenericCache):
	def __init__(self, num_cache_cells, ram, system_manager):
		Thread.__init__(self)
		self.num_cache_cells = num_cache_cells
		self.ram = ram
		self.system_manager = system_manager
		self.cache = num_cache_cells * [None]
		self.ram_rid = 0

		
		self.already_requested = []
		
		self.sync_answer = Synced_list()
		self.answer = []
		
		self.sync_req = Synced_list()
		self.req = []
	
	# Checks if a request from CACHE to RAM for address
	# has been already cast
	def if_already_requested(self, request_to_check):
		for request in self.already_requested:
			if request == request_to_check:
				return True
		return False
	
	# Tries to get the value from the CACHE at "addr" address
	# If the "addr" address is not mapped in the cache
	# the function returns "None"
	#@echo.echo
	def get_cell_value(self, addr):
		for cache_cell in self.cache:
			if cache_cell == None:
				continue
			if cache_cell[0] == addr:
				return cache_cell[1]
		return None
	
	
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the CACHE . If there is no mapping for this adress, 
	# it is added to the CACHE
	#@echo.echo
	def set_cell_value(self, addr, value):
		# look for first empty cell
		for i in range(self.num_cache_cells):
			if self.cache[i] == None:
				self.cache.insert(i, [addr, value])
				return i

		# if there are no more empty cells
		# default on overwriting cell 0
		self.cache.insert(0, [addr, value])
		return 0
	
	
	
	# This method will be called from the RAM
	# It receives answers to previous requests from the RAM
	#@echo.echo
	def get_answer_from_Ram(self, addr, value):
		self.sync_answer.append([addr, value])
		dbg("CACHE        ] " + str(self) + " is getting answer from RAM for addr= " + str(addr) + " value= " + str(value))
	
	
	
	# Accepts requests from REGISTERS and it adds them to a queue
	#@echo.echo
	def request(self, addr, register, reg_rid):
		self.sync_req.append([addr, register, reg_rid])
		dbg("REGISTER     ] " + str(register) + " is requesting from CACHE for addr= " + str(addr))
	
	
	
	def send_ram_requests(self):
		for req in self.req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			register = req[1]

			# If the address/value is not in the CACHE
			# request the value from the RAM and maintain
			# de request in the sync_req so that it will be
			# processed at the next time step
			if value == None:
				if self.if_already_requested([addr, self]):
					continue
				dbg("CACHE        ] " + str(self) + " is requesting from RAM for addr= " + str(addr))
				self.ram.request(addr, self, self.ram_rid)
				self.already_requested.append([addr, self])
				self.system_manager.cache_notify_submit_request(self.ram_rid, addr)
				self.ram_rid += 1
	
	
	
	def remove_elem(self, elem_to_remove, the_list):
		for elem in the_list:
			if elem == elem_to_remove:
				the_list.remove(elem)
				return
	
	
	
	# Responds to each REGISTER for its request
	#@echo.echo
	def respond_requests(self):
		for req in self.req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			register = req[1]
			reg_rid = req[2]
			
			# If the value is still not in the CACHE
			# check if it in the answers list
			if value == None:
				for answer in self.answer:
					if answer[0] == addr:
						value = answer[1]
						position = self.set_cell_value(addr, value)
						self.system_manager.cache_notify_store_value(position, addr)
						break
			# If the value is not in the CACHE nor in the answers list
			if value == None:
				continue
			
			dbg("CACHE        ] " + str(self) + " is responding to REGISTER for addr= " + str(addr) + " value= " + str(value))
			register.get_answer_from_Cache(addr, value)
			self.remove_elem([addr, value], self.req)
			self.remove_elem([addr, register], self.already_requested)
			
			self.system_manager.cache_notify_submit_answer(register, reg_rid, addr)
	
	
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_list(self):
		self.req.extend(self.sync_req.list)
		self.sync_req.list = []
	
	
	def prepare_answer_list(self):
		self.answer = self.sync_answer.list
		self.sync_answer.list = []


	#@echo.echo
	def run(self):
		self.system_manager.register_cache(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			if len(self.req) > 0:
				self.send_ram_requests()
			barrier.end_requests(self)
					
			self.prepare_request_list()
			barrier.end_process_requests(self)
			

			if len(self.req) > 0:
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
		self.cache_rid = 0
		
		self.already_requested = []
		
		self.sync_req = Synced_list()
		self.req  = []
		
		self.sync_answer = Synced_list()
		self.answer  = []
	
	# Checks if a request from REGISTER to CACHE for address
	# has been already cast
	def if_already_requested(self, request_to_check):
		for request in self.already_requested:
			if request == request_to_check:
				return True
		return False
	
	# Tries to get the value from the REGISTER at "addr" address
	# If the "addr" address is not mapped in the REGISTER
	# the function returns "None"
	#@echo.echo
	def get_cell_value(self, addr):
		for register_cell in self.register_set:
			if register_cell == None:
				continue
			if register_cell[0] == addr:
				return register_cell[1]
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the REGISTER. If there is no mapping for this adress, 
	# it is added to the REGISTER
	#@echo.echo
	def set_cell_value(self, addr, value):
		# Look for the first empty cell and and value there
		for i in range(self.num_register_cells):
			if self.register_set[i] == None:
				self.register_set.insert(i, [addr, value])
				return i
		
		# If there are no more empty cells default on overwriting 
		# the first cell
		self.register_set.insert(0, [addr, value])
		return 0
	
	# Accepts requests from the processor it is connected to
	#@echo.echo
	def request(self, addr, processor, processor_rid):
		self.sync_req.append([addr, processor, processor_rid])
		dbg("PROCESSOR    ] " + str(processor) + " is requesting REGISTER for addr= " + str(addr))

	#@echo.echo
	def get_answer_from_Cache(self, addr, value):
		self.sync_answer.append([addr, value])
		dbg("REGISTER     ]  " + str(self) + " received answer from CACHE for addr= " + str(addr) + " value= " + str(value))
	
	#@echo.echo
	def process_cache_answers(self):
		for answer in self.answer:
			dbg("REGISTER     ] " + str(self) + " is processing answer from CACHE for addr= " + str(answer[0]) + " value= " + str(answer[1]))
			position = self.set_cell_value(answer[0], answer[1])
			self.system_manager.register_set_notify_store_value(position, answer[0])
			
	
	def send_cache_requests(self):
		for req in self.req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			processor = req[1]
			
			# If the address/value is not in the REGISTER     ]
			# request the value from the CACHE        ]

			if value == None:
				if self.if_already_requested([addr, self]):
					continue
				
				self.cache.request(addr, self, self.cache_rid)
				self.already_requested.append([addr, self])
				self.system_manager.register_set_notify_submit_request(self.cache, self.cache_rid, addr)
				self.cache_rid += 1
			# If the value is in the REGISTER     ] send it to the PROCE
	
	def remove_elem(self, elem_to_remove, the_list):
		for elem in the_list:
			if elem == elem_to_remove:
				the_list.remove(elem)
				return
			
	# Responds to the Processor for its request
	#@echo.echo
	def respond_requests(self):
		for req in self.req:
			addr  = req[0]
			value = self.get_cell_value(req[0])
			processor = req[1]
			processor_rid = req[2]
			
			# If the address/value is not in the REGISTER yet
			# it may be in the answer list from cache
			if value == None:
				for answer in self.answer:
					if answer[0] == addr:
						value = answer[1]
						self.set_cell_value(addr, value)
						break
			
			# If addr is not in REGISTER     ] and not in the answers list
			# send the next value and wait for this one for more
			if value == None:
				continue
				
			dbg("REGISTER     ] " + str(self) + " is responding to PROCESSOR for addr= " + str(addr) + " value= " + str(value))
			processor.get_answer_from_Register(addr, value)

			self.remove_elem([addr, processor], self.req)
			self.remove_elem([addr, processor], self.already_requested)
			self.system_manager.register_set_notify_submit_answer(processor, processor_rid, addr)	

	
	# Prepares the lists for a new time step	
	#@echo.echo
	def prepare_request_list(self):
		# some cache requests may take more time
		# so it is best to extend the list and remove
		# items when we respond to the PROCESSOR     ]
		self.req.extend(self.sync_req.list)
		self.sync_req.list = []
	
	def prepare_answer_lists(self):
		self.answer = self.sync_answer.list
		self.sync_answer.list = []
	
	
	#@echo.echo
	def run(self):
		self.system_manager.register_register_set(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# Accepting or sending requests
			if len(self.req) > 0:
				self.send_cache_requests()
			barrier.end_requests(self)
			
			# Interchange shared request list with my local list 
			self.prepare_request_list()
			barrier.end_process_requests(self)
			
			# Replying to requests
			if len(self.req) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)

			# Processing answers
			if len(self.req) > 0:
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
		
		self.sync_process = Synced_list()
		self.process_requests = []
		
		
		self.register_answers = []
		self.sync_register_answers = Synced_list()
		
		
	#@echo.echo
	def get_process_number(self):
		return self.sync_process.get_len()
		
	# This method is called by the ProcessScheduler
	# and it adds a new process in the queue
	#@echo.echo
	def add_processes(self, process, scheduler):
		self.sync_process.append(process)
		self.scheduler = scheduler
		dbg("PROCESSOR     ] " + str(self) + " received a process from the SCHEDULER; process =" + str(process))
		
	#@echo.echo
	def get_answer_from_Register(self, addr, value):
		self.sync_register_answers.append([addr, value])
		dbg("PROCESSOR     ] " + str(self) + " received an answer from REGISTER for addr= " + str(addr) + " value= " + str(value))
	
	#@echo.echo
	def is_in_answers(self, addr):
		for answer in self.register_answers:
			if answer[0] == addr:
				return True
		return False
	
	# Returns the maximum number of operations
	# a process has done 
	#@echo.echo
	def get_max_operations(self):
		max_op = 0
		for proc in self.process_requests:
			sync_op = proc.get_number_of_executed_operations()
			if sync_op > max_op:
				max_op = sync_op
		return max_op
	
	# Returns a process from the process list to be run next
	# It is chosen by the max number of operations it already has done
	#@echo.echo
	def get_process_to_run(self):
		#max_op = self.get_max_operations()
		
		#for proc in self.process_requests:
		#	sync_op = proc.get_number_of_executed_operations()
		#	if sync_op == max_op:
		#		return proc
		return self.process_requests[0]

	
	def send_register_requests(self):
			if not self.is_in_answers(self.addr1):
				self.register_set.request(self.addr1, self, self.rid)
				self.sent_register_requests += 1
				self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr1)
				self.rid += 1
			
			if not self.is_in_answers(self.addr2):
				self.register_set.request(self.addr2, self, self.rid)
				self.sent_register_requests += 1
				self.system_manager.processor_notify_submit_request(self.register_set, self.rid, self.addr2)
				self.rid += 1
				
	
	def get_next_operation(self):
		if self.process == None:
			return
			
		# If there are no more operations left to run return None
		if self.operation_index > self.process.get_number_of_operations():
			return
		
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
		if self.operand == "+":
			self.result  = 0
		else:
			self.result = 1
		self.system_manager.processor_notify_start_executing_next_operation(self.process)
	
	def remove_element(self, elem):
		for process in self.process_requests:
			if process == elem:
				self.process_requests.remove(process)
				return
			
	# Implements the behavour of the PROCESSOR
	#@echo.echo
	def run_process(self):	
		if self.state == IDLE:
			
			# If running the first time of if the processor finished all
			# operations for this process get another process from the queue
			if self.process == None:
				self.process = self.get_process_to_run()
				self.get_next_operation()
				self.state = BUSY
			
			else:
				operations_left = self.process.get_number_of_operations() - self.process.get_number_of_executed_operations()
			
				# If current process finished all its operations
				# remove it from the processes list
				if operations_left == 0:
					self.remove_element(self.process)
					self.process = None
					self.operation_index = 0
				else:
					self.get_next_operation()
					self.state = BUSY
				
				
		elif self.state == BUSY:
			if self.process == None:
				self.state = IDLE
				return
			
			if self.sent_register_requests == 0:
				return
				
			if self.sent_register_requests == len(self.register_answers):
				if self.operand == "+":
					for answer in self.register_answers:
						self.result += answer[1]
				elif self.operand == "*":
					for answer in self.register_answers:
						self.result *= answer[1]
				
				self.system_manager.processor_notify_finish_executing_operation(self.result)
				self.process.inc_number_of_executed_operations()
				self.register_answers = []
				self.state = IDLE
	
	
	# Calculates the sum of all operations in all processes
	# of the current PROCESSOR     ]
	def get_sum_operations(self):
		suma = 0
		for process in self.process_requests:
			suma += process.get_number_of_operations()
		return suma
	
	# Sends the sum of all operations in all processes
	# of the current PROCESSOR     ] to the SCHEDULER    ]
	def reply_to_scheduler(self):
		suma = self.get_sum_operations()
		self.scheduler.get_processor_info_from_Processor([self, suma])
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_lists(self):
		self.process_requests.extend(self.sync_process.list)
		self.sync_process.list = []
	
	def prepare_answer_list(self):
		self.register_answers.extend(self.sync_register_answers.list)
		self.sync_register_answers.list = []
	
	#@echo.echo
	def run(self):
		self.system_manager.register_processor(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			
			# If the processor has not just started, therefore 
			# it has something to request
			if len(self.process_requests) > 0 and self.sent_register_requests == 0:
				self.send_register_requests()
			barrier.end_requests(self)
			

			self.prepare_request_lists()
			barrier.end_process_requests(self)
			
			# If there are any processes on this processor
			# send info of them to the scheduler
			if len(self.process_requests) > 0:
				self.reply_to_scheduler()
			barrier.end_reply_requests(self)
			
			# First time it enters for both are 0
			if len(self.process_requests) > 0:
				self.run_process()
				self.prepare_answer_list()
			barrier.end_process_answers(self)
			

class ProcessScheduler(GenericProcessScheduler):
	def __init__(self, processor_list, system_manager):
		Thread.__init__(self)
		self.processor_list = processor_list
		self.system_manager = system_manager
		
		self.process_info = []
		self.sync_process_info = Synced_list()
		
		self.process  = []
		self.sync_process = Synced_list()
	
	#@echo.echo
	def submit_process(self, process):
		self.sync_process.append(process)
		dbg("SCHEDULER    ] " + str(self) + " received a process from SYSTEM_MANAGER; process= " + str(process))

	#@echo.echo
	#TODO se joaca cu lista procesorului. trebuie sincronizat
	def get_cpu(self):
		#min_proc = sys.maxint
		#for processor in self.processor_list:
		#	if processor.get_process_number() < min_proc:
		#		min_proc = processor.get_process_number()
		#		saved_processor = processor
		return self.processor_list[0]
	
	def get_processor_info_from_Processor(self, info):
		self.sync_process_info.append(info)
		dbg("SCHEDULER    ] " + str(self) + " received processor info from PROCESSOR= " + str(info[0]) + " info= " + str(info[1]))
	
	#@echo.echo
	def schedule_processes(self):
		for process in self.process:
			cpu = self.get_cpu()
			cpu.add_processes(process, self)  # TRIMITERE CERERE
			self.system_manager.scheduler_notify_submit_process(cpu, process)

	# Prepares the lists for a new time step
	#@echo.echo	
	def prepare_request_lists(self):
		self.process = self.sync_process.list
		self.sync_process.list = []
	
	def prepare_answer_lists(self):
		self.process_info = self.sync_process_info.list
		self.sync_process_info.list = []
	
	#@echo.echo
	def run(self):
		self.system_manager.register_scheduler(self)
		global EXIT_TIME
		while(1):
			if EXIT_TIME:
				return
			

			if len(self.process) > 0:
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
	print "[" + msg + "\n"

	
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

