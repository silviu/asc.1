#!/usr/bin/python
from threading import *

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
