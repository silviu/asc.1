from threading import *

class Synced_list():
	
	def __init__(self, length):
		self.lock = RLock()
		self.list = length * [None]
	
	def append(self, elem):
		self.lock.acquire()
		self.list.append(elem)
		self.lock.release()
	
	def get_len(self):
		return len(self.list)
