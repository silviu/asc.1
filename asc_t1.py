#!/usr/bin/python
from threading import *
from asc_t1_defs import *
import sys
import time

barrier = None

N_Threads = 1

IDLE = 0
BUSY = 1
EXIT_TIME = False
SCHEDULER = None

class Synced_list():
	
	def __init__(self):
		self.lock = Lock()
		self.list = []
	
	def append(self, elem):
		self.lock.acquire()
		self.list.append(elem)
		self.lock.release()
	
	def get_len(self):
		return len(self.list)

class ReBarrier:
	def __init__(self):
		self.b1 = Barrier()
		self.b2 = Barrier()
		
	def sync(self):
		self.b1.sync()
		self.b2.sync()
	
	def end_requests(self, whom):
		##print "~~PAS 1~~ Thread " + str(whom) + " finished waiting for requests"
		self.sync()
	
	def end_process_requests(self, whom):
		##print "~~PAS 2~~ Thread " + str(whom) + " finished processing requests"
		self.sync()
	
	def end_reply_requests(self, whom):
		##print "~~PAS 3~~ Thread " + str(whom) + " finished replying to requests"
		self.sync()
	
	def end_process_answers(self, whom):
		##print "~~PAS 4~~ Thread " + str(whom) + " finished processing answers"
		self.sync()
	
	def flood_release(self):
		for i in range(4):	
			self.b1.flood_release()
			self.b2.flood_release()

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
	
	def flood_release(self):
		self.regcritica.acquire()
		for i in range(N_Threads-1):
			self.barrier.release()
		self.regcritica.release()

class Req_cache_to_ram:
	def __init__(self, addr, cache, rid):
		self.addr = addr
		self.cache = cache
		self.rid = rid
		
class Time_cell:
	def __init__(self, my_time, o):
		self.my_time = my_time
		self.o = o

class Ram(GenericRAM):
	
	def __init__(self, num_ram_cells, num_ram_requests_per_time_step, system_manager):
		Thread.__init__(self)
		self.num_ram_cells = num_ram_cells
		self.num_ram_requests_per_time_step = num_ram_requests_per_time_step
		self.system_manager = system_manager
		self.ram = [None] * num_ram_cells
		self.my_time = 0
		
		self.sync_req = Synced_list()
		self.req = []
		self.old_requests = []
	
	def remove_elem(self, elem_to_remove, the_list):
		if elem_to_remove in the_list:
			the_list.remove(elem_to_remove)
	
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
	def request(self, r_c_to_r):
		self.sync_req.append(r_c_to_r)
		dbg("CACHE        ] " + str(r_c_to_r.cache) + " is requesting from RAM addr= " + str(r_c_to_r.addr) + " RID = " + str(r_c_to_r.rid))
	
	
	
	#Responds to every CACHE for their previous requests
	##@echo.echo
	def respond_requests(self):
		requests_done = 0
		req_copy = self.old_requests
		requests_to_remove = []
		
		for tcr in req_copy:
			r = tcr.o
			if (requests_done-1 > self.num_ram_requests_per_time_step):
				break
			
			if (tcr.my_time == self.my_time):
				continue
			
			addr  = r.addr
			value = self.get_cell_value(r.addr)
			cache = r.cache
			rid = r.rid
			
			cache.get_answer_from_Ram(addr, value)
			self.system_manager.ram_notify_submit_answer(cache, rid, addr)
			requests_done += 1
			requests_to_remove.append(tcr)
			dbg("RAM          ] " + str(self) + " is responding to CACHE for addr= " + str(addr) + " value= " + str(value))
		
		for rem in requests_to_remove:
			self.remove_elem(rem, self.old_requests)
		
	
	# Prepares the lists for a new time step
	##@echo.echo
	def prepare_list(self):
		self.req = []
		for r in self.sync_req.list:
			self.req.append(Time_cell(self.my_time, r))
			self.sync_req.list = []
	
	##@echo.echo
	def run(self):
		self.system_manager.register_ram(self)
		global EXIT_TIME
		while(1):
			self.my_time += 1
			if EXIT_TIME:
				return

			barrier.end_requests(self)
			
			self.prepare_list()
			barrier.end_process_requests(self)
			
			if len(self.old_requests) > 0:
				self.respond_requests()
			barrier.end_reply_requests(self)
			
			# aici pun elemente in lista 3. lista din care trimit raspunsuri
			self.old_requests.extend(self.req)
			barrier.end_process_answers(self)
			


class Memory_cell:
	def __init__(self, address, value, timestamp):
		self.address = address
		self.value = value
		self.timestamp = timestamp


		
class Req_register_to_cache:
	def __init__(self, addr, register, rid):
		self.addr = addr
		self.register = register
		self.rid = rid

class Cache(GenericCache):
	def __init__(self, num_cache_cells, ram, system_manager):
		Thread.__init__(self)
		self.num_cache_cells = num_cache_cells
		self.ram = ram
		self.system_manager = system_manager
		self.cache = num_cache_cells * [Memory_cell(None, None, 0)]
		self.ram_rid = 0
		self.my_time = 0
		
		self.already_requested = []
		
		self.sync_answer = Synced_list()
		self.answer_list = []
		
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
			if cache_cell.address == None:
				continue
			if cache_cell.address == addr:
				return cache_cell.value
		return None
	
	
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the CACHE . If there is no mapping for this adress, 
	# it is added to the CACHE
	#@echo.echo
	def set_cell_value(self, addr, value):
		# look for first empty cell
		min_time = time.time()
		i = 0
		saved_position = 0
		
		for cache_cell in self.cache:
			if cache_cell.timestamp < min_time:
				min_time = cache_cell.timestamp
				if (i < self.num_cache_cells):
					saved_position = i
			i += 1
		# if there are no more empty cells
		# default on overwriting cell 0
		
		#print "SAVEDDDD POSITIOON: " + str(saved_position)
		self.cache[saved_position] = Memory_cell(addr, value, time.time())
		return saved_position
	
	
	
	# This method will be called from the RAM
	# It receives answers to previous requests from the RAM
	#@echo.echo
	def get_answer_from_Ram(self, addr, value):
		self.sync_answer.append([addr, value])
		dbg("CACHE        ] " + str(self) + " is getting answer from RAM for addr= " + str(addr) + " value= " + str(value))
	
	
	
	# Accepts requests from REGISTERS and it adds them to a queue
	#@echo.echo
	def request(self, r_r_to_c):
		self.sync_req.append(r_r_to_c)
		dbg("REGISTER     ] " + str(r_r_to_c.register) + " is requesting from CACHE for addr= " + str(r_r_to_c.addr))
	
	
	
	def send_ram_requests(self):
		for tcr in self.req:
			r = tcr.o
			addr  = r.addr
			value = self.get_cell_value(r.addr)
			register = r.register

			# If the address/value is not in the CACHE
			# request the value from the RAM and maintain
			# de request in the sync_req so that it will be
			# processed at the next time step
			if value == None:
				if self.if_already_requested([addr, register]):
					continue
				dbg("CACHE        ] " + str(self) + " is requesting from RAM for addr= " + str(addr))
				self.ram.request(Req_cache_to_ram(addr, self, self.ram_rid))
				self.already_requested.append([addr, register])
				self.system_manager.cache_notify_submit_request(self.ram_rid, addr)
				self.ram_rid += 1
	
	
	
	def remove_elem(self, elem_to_remove, the_list):
		if elem_to_remove in the_list:
			the_list.remove(elem_to_remove)
	
	
	# Responds to each REGISTER for its request
	#@echo.echo
	def respond_requests(self):
		req_copy = self.req
		requests_to_remove = []
		alreadys_to_remove = []
		
		for tcr in req_copy:
			r = tcr.o
			addr  = r.addr
			value = self.get_cell_value(r.addr)
			register = r.register
			reg_rid = r.rid
			
			if (tcr.my_time == self.my_time):
				continue
			
			# If the value is still not in the CACHE
			# check if it in the answers list
			if value == None:
				for answer in self.answer_list:
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
			self.system_manager.cache_notify_submit_answer(register, reg_rid, addr)
						
			requests_to_remove.append(tcr)
			alreadys_to_remove.append([addr, register])
			

		
		for rem in requests_to_remove:
			self.remove_elem(rem, self.req)
		
		for alr in alreadys_to_remove:
			self.remove_elem(alr, self.already_requested)
	
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_list(self):
		for r in self.sync_req.list:
			self.req.append(Time_cell(self.my_time, r))
		self.sync_req.list = []
	
	
	def prepare_answer_list(self):
		self.answer_list = self.sync_answer.list
		self.sync_answer.list = []


	#@echo.echo
	def run(self):
		self.system_manager.register_cache(self)
		global EXIT_TIME
		while(1):
			self.my_time += 1
			if EXIT_TIME:
				return
			
			if len(self.req) > 0:
				self.send_ram_requests()
			barrier.end_requests(self)
					
			self.prepare_request_list()
			barrier.end_process_requests(self)
			

			if len(self.req) > 0:
				##print "\n[CACHE INFO B ] REQUEST LIST = " + str(self.req) + "\n\t\t ANSWER LIST = " + str(self.answer_list)
				self.respond_requests()
				##print "\n[CACHE INFO A ] REQUEST LIST = " + str(self.req) + "\n\t\t ANSWER LIST = " + str(self.answer_list)
			barrier.end_reply_requests(self)
			
			
			self.prepare_answer_list()
			barrier.end_process_answers(self)
			
	
class Req_cpu_to_register:
	def __init__(self, addr, cpu, rid):
		self.addr = addr
		self.cpu = cpu
		self.rid = rid
		

class RegisterSet(GenericRegisterSet):
	def __init__(self, num_register_cells, cache, system_manager):
		Thread.__init__(self)
		self.num_register_cells = num_register_cells
		self.cache = cache
		self.system_manager = system_manager
		self.register_set = num_register_cells * [Memory_cell(None, None, 0)]
		self.cache_rid = 0
		self.my_time = 0
		
		self.already_requested = []
		
		self.sync_req = Synced_list()
		self.req  = []
		
		self.sync_answer = Synced_list()
		self.answer_list  = []
	
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
			if register_cell.address == None:
				continue
			if register_cell.address == addr:
				return register_cell.value
		return None
	
	# Tries to find the mapped address of the RAM address "addr" 
	# in the REGISTER. If there is no mapping for this adress, 
	# it is added to the REGISTER
	#@echo.echo
	def set_cell_value(self, addr, value):
		# Look for the first empty cell and and value there
		min_time = time.time()
		i = 0
		saved_position = 0
		
		for register_cell in self.register_set:
			if register_cell.timestamp < min_time:
				min_time = register_cell.timestamp
				if (i < self.num_register_cells):
					saved_position = i
			i += 1
		# if there are no more empty cells
		# default on overwriting cell 0
		
		self.register_set[saved_position] = Memory_cell(addr, value, time.time())
		return saved_position
	
	# Accepts requests from the processor it is connected to
	#@echo.echo
	def request(self, r_cpu_to_reg):
		self.sync_req.append(r_cpu_to_reg)
		dbg("PROCESSOR    ] " + str( r_cpu_to_reg.cpu) + " is requesting REGISTER for addr= " + str( r_cpu_to_reg.addr))

	#@echo.echo
	def get_answer_from_Cache(self, addr, value):
		self.sync_answer.append([addr, value])
		dbg("REGISTER     ]  " + str(self) + " received answer from CACHE for addr= " + str(addr) + " value= " + str(value))
	
	#@echo.echo
	def process_cache_answers(self):
		for answer in self.answer_list:
			dbg("REGISTER     ] " + str(self) + " is processing answer from CACHE for addr= " + str(answer[0]) + " value= " + str(answer[1]))
			position = self.set_cell_value(answer[0], answer[1])
			self.system_manager.register_set_notify_store_value(position, answer[0])
			
	
	def send_cache_requests(self):
		for tcr in self.req:
			r = tcr.o
			addr  = r.addr
			value = self.get_cell_value(r.addr)
			processor = r.cpu
			
			# If the address/value is not in the REGISTER     ]
			# request the value from the CACHE        ]

			if value == None:
				if self.if_already_requested([addr, processor]):
					continue
				
				self.cache.request(Req_register_to_cache(addr, self, self.cache_rid))
				self.system_manager.register_set_notify_submit_request(self.cache, self.cache_rid, addr)
				self.already_requested.append([addr, processor])
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
		requests_to_remove = []	
		alreadys_to_remove = []
		req_copy = self.req
		
		for tcr in req_copy:
			r = tcr.o
			
			addr  = r.addr
			value = self.get_cell_value(r.addr)
			processor = r.cpu
			processor_rid = r.rid
			
			if (tcr.my_time == self.my_time):
				continue
			
			# If the address/value is not in the REGISTER yet
			# it may be in the answer list from cache
			if value == None:
				for answer in self.answer_list:
					if answer[0] == addr:
						value = answer[1]
						position = self.set_cell_value(addr, value)
						self.system_manager.register_set_notify_store_value(position, addr)
						break
			
			# If addr is not in REGISTER     ] and not in the answers list
			# send the next value and wait for this one for more
			if value == None:
				continue
				
			dbg("REGISTER     ] " + str(self) + " is responding to PROCESSOR for addr= " + str(addr) + " value= " + str(value))
			processor.get_answer_from_Register(addr, value)
			self.system_manager.register_set_notify_submit_answer(processor, processor_rid, addr)
			
			requests_to_remove.append(tcr)
			alreadys_to_remove.append([addr, processor])
			##print "\n\n $$$$$$$$$$REGISTER_SET= " + str(self.register_set) 
		
		for rem in requests_to_remove:			
			self.remove_elem(rem, self.req)
			
		for alr in alreadys_to_remove:
			self.remove_elem(alr, self.already_requested)


	
	# Prepares the lists for a new time step	
	#@echo.echo
	def prepare_request_list(self):
		# some cache requests may take more time
		# so it is best to extend the list and remove
		# items when we respond to the PROCESSOR     ]
		for r in self.sync_req.list:
			self.req.append(Time_cell(self.my_time, r))
		self.sync_req.list = []
	
	def prepare_answer_lists(self):
		self.answer_list = self.sync_answer.list
		self.sync_answer.list = []
	
	
	#@echo.echo
	def run(self):
		self.system_manager.register_register_set(self)
		global EXIT_TIME
		while(1):
			self.my_time += 1
			
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
			# Processing answers
			if len(self.req) > 0:
				self.process_cache_answers()
			
			if len(self.req) > 0:
				##print "\n[REGISTER INFO B] REQUEST LIST = " + str(self.req) + "\n\t\t ANSWER LIST = " + str(self.answer_list)
				self.respond_requests()
				##print "\n[REGISTER INFO A] REQUEST LIST = " + str(self.req) + "\n\t\t ANSWER LIST = " + str(self.answer_list)
			
			barrier.end_reply_requests(self)

				
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
		self.my_time = 0
		
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
		return self.process_requests[0].o

	
	def send_register_requests(self):
		for address in self.addresses_to_look_for:
			if not self.is_in_answers(address):
				self.register_set.request(Req_cpu_to_register(address, self, self.rid))
				self.sent_register_requests += 1
				self.system_manager.processor_notify_submit_request(self.register_set, self.rid, address)
				self.rid += 1
			
	def get_next_operation(self):
		self.addresses_to_look_for = []
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
		for i in range(len(self.operation) - 1):
			self.addresses_to_look_for.append(self.operation[i + 1])
		
		if self.operand == "+":
			self.result  = 0
		else:
			self.result = 1
		self.system_manager.processor_notify_start_executing_next_operation(self.process)
	
	def remove_element(self, elem):
		for tprocess in self.process_requests:
			process = tprocess.o
			if process == elem:
				self.process_requests.remove(tprocess)
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
		for tprocess in self.process_requests:
			process = tprocess.o
			suma += process.get_number_of_operations()
		return suma
	
	# Sends the sum of all operations in all processes
	# of the current PROCESSOR     ] to the SCHEDULER    ]
	def reply_to_scheduler(self):
		suma = self.get_sum_operations()
		SCHEDULER.get_processor_info_from_Processor([self, suma])
	
	# Prepares the lists for a new time step
	#@echo.echo
	def prepare_request_lists(self):
		for r in self.sync_process.list:
			self.process_requests.append(Time_cell(self.my_time, r))
		self.sync_process.list = []
	
	def prepare_answer_list(self):
		self.register_answers.extend(self.sync_register_answers.list)
		self.sync_register_answers.list = []
	
	#@echo.echo
	def run(self):
		self.system_manager.register_processor(self)
		global EXIT_TIME
		while(1):
			self.my_time += 1
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
			
			self.reply_to_scheduler()
			barrier.end_reply_requests(self)
			

			if len(self.process_requests) > 0:
				self.run_process()
			self.prepare_answer_list()
			barrier.end_process_answers(self)
			

class ProcessScheduler(GenericProcessScheduler):
	def __init__(self, processor_list, system_manager):
		global SCHEDULER
		Thread.__init__(self)
		self.processor_list = processor_list
		self.system_manager = system_manager
		self.my_time = 0
		SCHEDULER = self
		
		self.process_info = []
		self.sync_process_info = Synced_list()
		
		self.process  = []
		self.sync_process = Synced_list()
	
	#@echo.echo
	def submit_process(self, process):
		self.sync_process.append(process)
		self.process_info.append([process, 0])
		dbg("SCHEDULER    ] " + str(self) + " received a process from SYSTEM_MANAGER; process= " + str(process))

	#@echo.echo
	#TODO se joaca cu lista procesorului. trebuie sincronizat
	def get_cpu(self, nr_operations):
		min_proc = sys.maxint
		saved_cpu = self.processor_list[0]
		saved_i = 0
		
		print "\nCPU INFOOOOOO " + str(self.process_info)
		for i in range(len(self.process_info)):
			pr = self.process_info[i]
			cpu = pr[0]
			suma = pr[1]
			if suma < min_proc:
				min_proc = suma
				saved_cpu = cpu
				saved_i = i
		self.process_info[saved_i][1] += nr_operations
		return saved_cpu
	
	def get_processor_info_from_Processor(self, info):
		self.sync_process_info.append(info)
		dbg("SCHEDULER    ] " + str(self) + " received processor info from PROCESSOR= " + str(info[0]) + " info= " + str(info[1]))
	
	#@echo.echo
	def schedule_processes(self):
		for tproc in self.process:
			proc = tproc.o
			nr_operations = proc.get_number_of_operations()
			cpu = self.get_cpu(nr_operations)
			cpu.add_processes(proc, self)  # TRIMITERE CERERE
			self.system_manager.scheduler_notify_submit_process(cpu, proc)
			self.process.remove(tproc)

	# Prepares the lists for a new time step
	#@echo.echo	
	def prepare_request_lists(self):
		for r in self.sync_process.list:
			self.process.append(Time_cell(self.my_time, r))
		self.sync_process.list = []
	
	def prepare_answer_lists(self):
		self.process_info = self.sync_process_info.list
		self.sync_process_info.list = []
	
	#@echo.echo
	def run(self):
		self.system_manager.register_scheduler(self)
		global EXIT_TIME
		while(1):
			self.my_time += 1
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
	global barrier, N_Threads, EXIT_TIME
	barrier = ReBarrier()
	N_Threads = 1
	EXIT_TIME = False
	

def dbg(msg):
	##print "[" + msg + "\n"
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
		barrier.flood_release()
		object.increase_time_step()

