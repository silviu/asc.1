from threading import *

class ReBarrier:
	def __init__(self, nr_threads):
		self.b1 = Barrier(nr_threads)
		self.b2 = Barrier(nr_threads)
		
	def sync(self):
		self.b1.sync()
		self.b2.sync()

class Barrier:
	def __init__(self, nr_threads):
		self.barrier    = Semaphore(value=0)
		self.regcritica = Semaphore(value=1)
		self.nr_threads = nr_threads
		self.n = nr_threads
 
	def sync(self):
		self.regcritica.acquire()
		self.n -= 1
		if  self.n == 0:
			for i in range(self.nr_threads):
				self.barrier.release()
			self.n = self.nr_threads
		self.regcritica.release()
		self.barrier.acquire()

class Threads(Thread):
	def __init__(self, barrier, idd):
		Thread.__init__(self)
		self.barrier = barrier
		self.idd = idd
		self.n = 0
	
	def run(self):
		while(1):
			self.n += 1
			print "Thread " + str(self.idd) + " : " + str(self.n)
			self.barrier.sync()
def main():
	num_threads = 100
	threads = num_threads * [None]
	barrier = ReBarrier(num_threads)
	
	for i in range(num_threads):
		threads[i] = Threads(barrier, i)

	for i in threads:
		i.start()
		
	for i in threads:
		i.join()

if __name__=="__main__":
	main()
