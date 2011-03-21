#!/usr/bin/python

import random
import time
from threading import *
from asc_t1_defs import *
from asc_t1 import *


__TOTAL_POINTS = 0
StdOutLock = Lock()
DEBUG_MODE = 1
PRINT_STATISTICS = 0

class SystemManager(Thread):
    def __init__(self, TMAX, num_caches, num_register_sets, num_processors, num_ram_cells, num_cache_cells, num_register_cells, num_ram_reqs_per_time_step, processor_register_dic, register_cache_dic, process_list, time_limit, max_max_processing_delay_for_bonus, bonus1, max_avg_processing_delay_for_bonus, bonus2, max_cost_for_bonus, bonus3):
        Thread.__init__(self)
        self.__TMAX = TMAX
        self.__num_caches = num_caches
        self.__num_register_sets = num_register_sets
        self.__num_processors = num_processors
        self.__num_ram_cells = num_ram_cells
        self.__num_cache_cells = num_cache_cells
        self.__num_register_cells = num_register_cells
        self.__num_ram_reqs_per_time_step = num_ram_reqs_per_time_step
        self.__processor_register_dic = processor_register_dic
        self.__register_cache_dic = register_cache_dic
        self.__max_max_processing_delay_for_bonus = max_max_processing_delay_for_bonus
        self.__max_avg_processing_delay_for_bonus = max_avg_processing_delay_for_bonus
        self.__max_cost_for_bonus = max_cost_for_bonus
        self.__bonus1 = bonus1
        self.__bonus2 = bonus2
        self.__bonus3 = bonus3

        self.__process_list = []
        self.__total_number_of_instructions = 0

        for pp in process_list:
            time, process = pp
            self.__process_list.append((time, 0, process))
            self.__total_number_of_instructions += process.get_number_of_operations()

        self.__time_limit = time_limit

        self.__big_lock = Lock()
        
        self.__ram_thread = None
        self.__ram_object = None
        self.__ram_status = []
        
        self.__cache_dic = {}
        self.__cache_status_dic = {}
        
        self.__register_dic = {}
        self.__register_status_dic = {}
        
        self.__processor_dic = {}
        self.__processor_status_dic = {}
        self.__processor_addr_dic = {}
        self.__processor_process_set = {}
        self.__processor_last_time_step = {}
        
        self.__scheduler_thread = None
        self.__scheduler_object = None
        self.__scheduler_status = []
    
        self.__wait_sem = Semaphore(0)

        self.__error = 0
        
        self.__req_dic = {}

        self.__points = 0

        self.__num_ram_requests_current_time_step = 0
        self.__num_ram_requests = 0
        self.__num_cache_requests = 0
        self.__num_register_requests = 0
        
        self.__process_finish_time = {}
        self.__number_of_executed_instructions = 0

    def get_points(self):
        return self.__points

    def register_ram(self, ram_object):
        self.__big_lock.acquire()

        ct = current_thread()
        if ((ct == self.__ram_thread) or (ct in self.__cache_dic.keys()) or (ct in self.__register_dic.keys()) or (ct in self.__processor_dic.keys()) or (ct == self.__scheduler_thread)):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-urile inregistrate nu sunt distincte"
            StdOutLock.release()

        if (self.__ram_thread != None):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Inregistrare RAM inca o data"
            StdOutLock.release()
            
        self.__ram_thread = current_thread()
        self.__ram_object = ram_object
        
        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Inregistrare RAM: thread=", self.__ram_thread, "obiect=", self.__ram_object
            StdOutLock.release()
        
        i = 0
        while (i < self.__num_ram_cells):
            value = random.randint(1, 1000)
            self.__ram_status.append(value)
            self.__ram_object.set_cell_value(i, value)
            i += 1

        self.__big_lock.release()
        self.__wait_sem.release()
    
    def register_cache(self, cache_object):
        self.__big_lock.acquire()
        ct = current_thread()
        if ((ct == self.__ram_thread) or (ct in self.__cache_dic.keys()) or (ct in self.__register_dic.keys()) or (ct in self.__processor_dic.keys()) or (ct == self.__scheduler_thread)):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-urile inregistrate nu sunt distincte"
            StdOutLock.release()
        else:
            self.__cache_dic[current_thread()] = cache_object
            if (len(self.__cache_dic.keys()) > self.__num_caches):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: S-au inregistrat prea multe cache-uri"
                StdOutLock.release()

            if (DEBUG_MODE == 1):
                StdOutLock.acquire()
                print "[SystemManager] Inregistrare Cache: thread=", current_thread(), "obiect=", cache_object
                StdOutLock.release()

            l = []
            for i in range(self.__num_cache_cells):
                l.append((-1, -1))
            
            self.__cache_status_dic[current_thread()] = l

        self.__big_lock.release()
        self.__wait_sem.release()

    def register_register_set(self, register_set_object):
        self.__big_lock.acquire()
        ct = current_thread()
        if ((ct == self.__ram_thread) or (ct in self.__cache_dic.keys()) or (ct in self.__register_dic.keys()) or (ct in self.__processor_dic.keys()) or (ct == self.__scheduler_thread)):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-urile inregistrate nu sunt distincte"
            StdOutLock.release()
        else:
            self.__register_dic[current_thread()] = register_set_object
            if (len(self.__register_dic.keys()) > self.__num_register_sets):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: S-au inregistrat prea multe seturi de registrii"
                StdOutLock.release()

            if (DEBUG_MODE == 1):
                StdOutLock.acquire()
                print "[SystemManager] Inregistrare RegisterSet: thread=", current_thread(), "obiect=", register_set_object
                StdOutLock.release()

            l = []
            for i in range(self.__num_register_cells):
                l.append((-1, -1))
            
            self.__register_status_dic[current_thread()] = l

        self.__big_lock.release()
        self.__wait_sem.release()

    def register_processor(self, processor_object):
        self.__big_lock.acquire()
        ct = current_thread()
        if ((ct == self.__ram_thread) or (ct in self.__cache_dic.keys()) or (ct in self.__register_dic.keys()) or (ct in self.__processor_dic.keys()) or (ct == self.__scheduler_thread)):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-urile inregistrate nu sunt distincte"
            StdOutLock.release()
        else:
            self.__processor_dic[current_thread()] = processor_object
            if (len(self.__processor_dic.keys()) > self.__num_processors):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: S-au inregistrat prea multe procesoare"
                StdOutLock.release()

            if (DEBUG_MODE == 1):
                StdOutLock.acquire()
                print "[SystemManager] Inregistrare Processor: thread=", current_thread(), "obiect=", processor_object
                StdOutLock.release()

            self.__processor_status_dic[current_thread()] = None
            self.__processor_last_time_step[current_thread()] = 0
            self.__processor_addr_dic[processor_object] = []
            self.__processor_process_set[current_thread()] = []

        self.__big_lock.release()
        self.__wait_sem.release()

    def register_scheduler(self, scheduler_object):
        self.__big_lock.acquire()
        
        ct = current_thread()
        if ((ct == self.__ram_thread) or (ct in self.__cache_dic.keys()) or (ct in self.__register_dic.keys()) or (ct in self.__processor_dic.keys()) or (ct == self.__scheduler_thread)):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-urile inregistrate nu sunt distincte"
            StdOutLock.release()

        if (self.__scheduler_thread != None):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Inregistrare scheduler inca o data"
            StdOutLock.release()
        
        self.__scheduler_thread = current_thread()
        self.__scheduler_object = scheduler_object

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Inregistrare Scheduler: thread=", self.__scheduler_thread, "obiect=", self.__scheduler_object
            StdOutLock.release()

        self.__big_lock.release()
        self.__wait_sem.release()
    
    def __wait_for_registrations(self):
        sum = 1 + self.__num_caches + self.__num_register_sets + self.__num_processors + 1
        while (sum > 0):
            self.__wait_sem.acquire()
            sum -= 1

    def __add_request(self, from_, to_, rid, addr):
        self.__big_lock.acquire()
        key = (from_, to_, rid)
        if (key in self.__req_dic.keys()):
            self.__error = 1

            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Exista doua cereri cu acelasi id intre aceeasi sursa si destinatie: sursa=", from_, "destinatie=", to_, "id cerere=", rid
            StdOutLock.release()
        else:
            self.__req_dic[key] = (addr, self.__t)
        self.__big_lock.release()
    
    def __check_request(self, from_, to_, rid, addr):
        self.__big_lock.acquire()
        key = (from_, to_, rid)
        if (not (key in self.__req_dic.keys())):
            self.__error = 1

            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Se trimite un raspuns la o cerere care nu exista: sursa cerere=", from_, "destinatie cerere=", to_, "id cerere=", rid
            StdOutLock.release()
        else:
            dic_addr, time = self.__req_dic[key]
            if (addr != dic_addr):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Se trimite un raspuns pentru o adresa diferita de cea ceruta: sursa cerere=", from_, "destinatie cerere=", to_, "id cerere=", rid
                StdOutLock.release()
                
            if (time < 0):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Se trimite un al doilea raspuns pentru aceeasi cerere"
                StdOutLock.release()
            elif (time >= self.__t):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Se trimite un raspuns pentru o cerere mai devreme decat este permis TIME= " + str(time) + " SELF__T= " + str(self.__t)
                StdOutLock.release()
              
            self.__req_dic[key] = (dic_addr, -(self.__t))
        self.__big_lock.release()

    def ram_notify_submit_answer(self, cache, rid, addr):
        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] RAM-ul trimite raspuns cu adresa addr=", addr, " la cererea rid=", rid, " catre cache=", cache
            StdOutLock.release()

        self.__big_lock.acquire()
        if ((current_thread() != self.__ram_thread) or not(cache in self.__cache_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Thread-ul RAM este incorect sau obiectul cache este neinregistrat"
            StdOutLock.release()

        self.__num_ram_requests_current_time_step += 1
        if (self.__num_ram_requests_current_time_step > self.__num_ram_reqs_per_time_step):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: RAM-ul a procesat prea multe cereri intr-un pas de timp:", self.__num_ram_requests_current_time_step, "(valoarea maxima permisa=", self.__num_ram_reqs_per_time_step, ")"
            StdOutLock.release()

        self.__big_lock.release()

        from_ = cache
        to_ = self.__ram_object
        self.__check_request(from_, to_, rid, addr)
       
    def cache_notify_submit_request(self, rid, addr):
        self.__big_lock.acquire()
        self.__num_ram_requests += 1
        cache = self.__cache_dic[current_thread()]

        if (not(cache in self.__cache_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul cache este neinregistrat"
            StdOutLock.release()
        self.__big_lock.release()        
 
        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Cache=", cache, "trimite cerere pentru adresa addr=", addr, "rid=", rid, " catre RAM"
            StdOutLock.release()

        if (addr < 0 or addr > self.__num_ram_cells):
            self.__big_lock.acquire()
            self.__error = 1
            self.__big_lock.release()

            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Adresa invalida in cadrul unei cereri: addr=", addr
            StdOutLock.release()

        from_ = cache
        to_ = self.__ram_object
        self.__add_request(from_, to_, rid, addr)
    
    def cache_notify_submit_answer(self, register_set, rid, addr):
        self.__big_lock.acquire()
        cache = self.__cache_dic[current_thread()]

        if (not(cache in self.__cache_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul cache este neinregistrat"
            StdOutLock.release()

        if (not(register_set in self.__register_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul register_set este neinregistrat"
            StdOutLock.release()

        if (self.__register_cache_dic[register_set] != cache):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Cache-ul trimite un raspuns la un set de registrii neconectat la el"
            StdOutLock.release()
        
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Cache=", cache, "trimite raspuns cu adresa addr=", addr, "la cererea rid=", rid, " catre setul de registri", register_set
            StdOutLock.release()

        from_ = register_set
        to_ = cache
        self.__check_request(from_, to_, rid, addr)

        self.__big_lock.acquire()
        cache_list = self.__cache_status_dic[current_thread()]
        found = 0
        for pp in cache_list:
            caddr, ctime = pp
            if (caddr == addr):
                found = 1
                break
            
        if (found == 0):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Cache-ul=", cache, "nu detine valoarea adresei addr=", addr
            StdOutLock.release()
        self.__big_lock.release()
    
    def cache_notify_store_value(self, position, addr):
        self.__big_lock.acquire()
        cache = self.__cache_dic[current_thread()]

        # Verifica daca s-a primit un raspuns de la RAM cu adresa respectiva la pasul curent de timp.
        from_ = cache
        to_ = self.__ram_object
        found = 0
        for key in self.__req_dic.keys():
            f, t, rid = key
            if (f == from_ and t == to_):
                dic_addr, time = self.__req_dic[key]
                if ((dic_addr == addr) and (time < 0) and ((-time) <= (self.__t - 1))):
                    self.__req_dic[key] = (dic_addr, -(self.__TMAX + 10))
                    found = 1
                    break
        
        if (found == 0):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Nu s-a primit niciun raspuns cu adresa addr=", addr, "pentru a putea salva aceasta adresa in cache"
            StdOutLock.release()
        
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Cache=", cache, "salveaza adresa addr=", addr, "la pozitia=", position
            StdOutLock.release()

        self.__big_lock.acquire()
        self.__cache_status_dic[current_thread()][position] = (addr, self.__t)
        self.__big_lock.release()

    def register_set_notify_submit_request(self, cache, rid, addr):
        self.__big_lock.acquire()
        self.__num_cache_requests += 1
        register_set = self.__register_dic[current_thread()]

        if (not(cache in self.__cache_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul cache este neinregistrat"
            StdOutLock.release()

        if (not(register_set in self.__register_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul register_set este neinregistrat"
            StdOutLock.release()

        if (self.__register_cache_dic[register_set] != cache):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Setul de registrii trimite o cerere la un cache la care nu e conectat"
            StdOutLock.release()

        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Setul de registri=", register_set, "trimite cerere pentru adresa addr=", addr, "rid=", rid, " catre cache-ul", cache
            StdOutLock.release()

        if (addr < 0 or addr > self.__num_ram_cells):
            self.__big_lock.acquire()
            self.__error = 1
            self.__big_lock.release()

            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Adresa invalida in cadrul unei cereri: addr=", addr
            StdOutLock.release()

        from_ = register_set
        to_ = cache
        self.__add_request(from_, to_, rid, addr)
    
    def register_set_notify_submit_answer(self, processor, rid, addr):
        self.__big_lock.acquire()
        register_set = self.__register_dic[current_thread()]

        if (not(processor in self.__processor_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul processor este neinregistrat"
            StdOutLock.release()

        if (not(register_set in self.__register_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul register_set este neinregistrat"
            StdOutLock.release()

        if (self.__processor_register_dic[processor] != register_set):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Setul de registrii trimite un raspuns la un procesor neconectat la el"
            StdOutLock.release()

        self.__processor_addr_dic[processor].append(addr)
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Setul de registri=", register_set, "trimite raspuns cu adresa addr=", addr, "la cererea rid=", rid, " catre procesorul=", processor
            StdOutLock.release()

        from_ = processor
        to_ = register_set
        self.__check_request(from_, to_, rid, addr)

        self.__big_lock.acquire()
        register_list = self.__register_status_dic[current_thread()]
        found = 0
        for pp in register_list:
            raddr, rtime = pp
            if (raddr == addr):
                found = 1
                break
            
        if (found == 0):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Setul de registrii=", register_set, "nu detine valoarea adresei addr=", addr
            StdOutLock.release()
        self.__big_lock.release()

    def register_set_notify_store_value(self, position, addr):
        self.__big_lock.acquire()
        register_set = self.__register_dic[current_thread()]
        from_ = register_set
        to_ = self.__register_cache_dic[register_set]
        found = 0
        for key in self.__req_dic.keys():
            f, t, rid = key
            if (f == from_ and t == to_):
                dic_addr, time = self.__req_dic[key]
                if ((dic_addr == addr) and (time < 0) and ((-time) <= (self.__t - 1))):
                    self.__req_dic[key] = (dic_addr, -(self.__TMAX + 10))
                    found = 1
                    break
        
        if (found == 0):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Nu s-a primit niciun raspuns cu adresa addr=", addr, "pentru a putea salva aceasta adresa in setul de registrii"
            StdOutLock.release()
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Setul de registri=", register_set, "salveaza adresa addr=", addr, "la pozitia=", position
            StdOutLock.release()

        self.__big_lock.acquire()
        self.__register_status_dic[current_thread()][position] = (addr, self.__t)
        self.__big_lock.release()
        
    def processor_notify_submit_request(self, register_set, rid, addr):
        self.__big_lock.acquire()
        self.__num_register_requests += 1
        processor = self.__processor_dic[current_thread()]

        if (not(processor in self.__processor_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul processor este neinregistrat"
            StdOutLock.release()

        if (not(register_set in self.__register_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul register_set este neinregistrat"
            StdOutLock.release()

        if (self.__processor_register_dic[processor] != register_set):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Procesorul trimite o cerere la un set de registrii la care nu e conectat"
            StdOutLock.release()
            
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Procesorul=", processor, "trimite cerere pentru adresa addr=", addr, "rid=", rid, " catre setul de registri", register_set
            StdOutLock.release()

        from_ = processor
        to_ = register_set
        self.__add_request(from_, to_, rid, addr)

    def processor_notify_start_executing_next_operation(self, process):
        self.__big_lock.acquire()
        processor = self.__processor_dic[current_thread()]

        if (not(processor in self.__processor_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul processor este neinregistrat"
            StdOutLock.release()

        if (self.__processor_status_dic[current_thread()] != None):
            self.__error = 1
            StdOutLock.acquire()            
            print "[SystemManager] EROARE FATALA: Un procesor doreste sa execute o instructiune desi are o alta instructiune in curs de procesare"
            StdOutLock.release()
        
        if (not (process in self.__processor_process_set[processor])):
            self.__error = 1
            StdOutLock.acquire()            
            print "[SystemManager] EROARE FATALA: Un procesor doreste sa execute o instructiune a unui proces care nu a fost asignat lui"
            StdOutLock.release()

        if (self.__processor_last_time_step[current_thread()] >= self.__t):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Procesorul=", processor, "a efectuat mai multe actiuni (start) la acelasi pas de timp"
            StdOutLock.release()
            
        self.__processor_last_time_step[current_thread()] = self.__t
        
        next_op = self.__get_next_operation(process)
        if (next_op < 0 or next_op >= process.get_number_of_operations()):
            self.__error = 1
            StdOutLock.acquire()            
            print "[SystemManager] EROARE FATALA: Instructiunea executata de procesorul=", processor, "din procesul=", process, "este invalida"
            StdOutLock.release()
        self.__big_lock.release()        

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Procesorul=", processor, "incepe executia instructiunii urmatoare=", next_op, "a procesului=", process
            StdOutLock.release()

        self.__big_lock.acquire()
        self.__processor_status_dic[current_thread()] = process
        self.__big_lock.release()

    def __update_operation(self, process):
        to_remove = None
        
        for pp in self.__process_list:
            time, nops, proc = pp
            if (proc == process):
                to_remove = pp
                break
            
        if (to_remove != None):
            time, nops, proc = to_remove
            self.__process_list.remove(to_remove)
            self.__process_list.append((time, nops + 1, proc))
            
            if (nops + 1 == proc.get_number_of_operations()):
                self.__process_finish_time[proc] = self.__t
        else:
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Procesul", process, "nu este valid"
            StdOutLock.release()

    def __get_next_operation(self, process):
        for pp in self.__process_list:
            time, nops, proc = pp
            if (proc == process):
                return nops
        
        # If we got here, then it's bad.
        return -1

    def processor_notify_finish_executing_operation(self, ans):
        self.__big_lock.acquire()
        processor = self.__processor_dic[current_thread()]
        if (not(processor in self.__processor_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul processor este neinregistrat"
            StdOutLock.release()
        
        process = self.__processor_status_dic[current_thread()]
        if (process == None):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Un procesor doreste sa incheie executia unei instructiuni, desi el nu a inceput sa execute nicio instructiune"
            StdOutLock.release()

        if (self.__processor_last_time_step[current_thread()] >= self.__t):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Procesorul=", processor, "a efectuat mai multe actiuni (finish ) la acelasi pas de timp"
            StdOutLock.release()
            
        self.__processor_last_time_step[current_thread()] = self.__t
        
        next_op = self.__get_next_operation(process)
        if (next_op < 0 or next_op >= process.get_number_of_operations()):
            self.__error = 1
            StdOutLock.acquire()            
            print "[SystemManager] EROARE FATALA: Instructiunea executata de procesorul=", processor, "din procesul=", process, "este invalida"
            StdOutLock.release()            

        op = process.get_operation(next_op)
        if (op[0] == "+"):
            expected_ans = 0
        else:
            expected_ans = 1
            
        i = 1
        while (i < len(op)):
            if (not (op[i] in self.__processor_addr_dic[processor])):
                self.__error = 1
                StdOutLock.acquire()            
                print "[SystemManager] EROARE FATALA: Procesorul=", processor, "incearca sa finalizeze executia unei instructiuni fara a fi primit toate valorile necesare"
                StdOutLock.release()            
            
            if (op[0] == "+"):
                expected_ans += self.__ram_status[op[i]]
            else:
                expected_ans *= self.__ram_status[op[i]]
            i += 1

        self.__processor_addr_dic[processor] = []

        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Procesorul=", processor, "a finalizat executia instructiunii urmatoare=", next_op, "a procesului=", process, "(rezultat obtinut=", ans, "rezultat asteptat=", expected_ans, ")"
            StdOutLock.release()
        
        if (ans != expected_ans):
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Rezulatul unei operatii finalizate este incorect (rezultat corect=", expected_ans, "rezultat obtinut=", ans, ")"
            StdOutLock.release()

        self.__number_of_executed_instructions += 1
        process = self.__processor_status_dic[current_thread()]
        self.__update_operation(process)
        self.__processor_status_dic[current_thread()] = None
        self.__big_lock.release()
    
    def scheduler_notify_submit_process(self, processor, process):
        if (DEBUG_MODE == 1):
            StdOutLock.acquire()
            print "[SystemManager] Scheduler-ul da procesul=", process, " procesorului=", processor, "pentru executie"
            StdOutLock.release()

        self.__big_lock.acquire()
        if (not(processor in self.__processor_dic.values())):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul processor este neinregistrat"
            StdOutLock.release()

        found = 0
        for pp in self.__process_list:
            time, nops, proc = pp
            if (proc == process):
                if (time >= self.__t):
                    self.__error = 1
                    StdOutLock.acquire()
                    print "[SystemManager] EROARE FATALA: Procesul este trimis de scheduler unui procesor mai devreme decat este permis. TIME = " + str(time) + " SELT___T: " + str(self.__t)
                    StdOutLock.release()                    
                found = 1
                break
            
        if (found == 0):
            self.__error = 1
            StdOutLock.acquire()
            print "[SystemManager] EROARE FATALA: Obiectul process nu este valid"
            StdOutLock.release()
                    
        self.__processor_process_set[processor].append(process)
        self.__big_lock.release()
    
    def increase_time_step(self):
        self.__wait_sem.acquire()
        
        self.__big_lock.acquire()
        self.__t += 1

        if (PRINT_STATISTICS == 1):
            print "[SystemManager] Numar total de instructiuni a caror executie a fost finalizata:", self.__number_of_executed_instructions, "/", self.__total_number_of_instructions
            print "[SystemManager] Numar total de procese finalizate:", len(self.__process_finish_time.keys()), "/", len(self.__process_list)
        
        if (self.__t <= self.__TMAX):
            StdOutLock.acquire()
            if (PRINT_STATISTICS == 1):
                print "[SystemManager] Incepe pasul de timp", self.__t
            StdOutLock.release()

        self.__num_ram_requests_current_time_step = 0
        self.__big_lock.release()
    
    def __final_check(self):
        global __RAM_REQUEST_COEFF

        self.__big_lock.acquire()
        for pp in self.__process_list:
            time_, nops, process = pp
            if (nops != process.get_number_of_operations()):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Nu s-au executat toate instructiunile procesului=", process, "(doar", nops, "/", process.get_number_of_operations(), ")" 
                StdOutLock.release()
        
        Tavg = 0.0
        Tmax = 0
        
        for proc in self.__process_finish_time.keys():
            finish_time = self.__process_finish_time[proc]

            start_time = None
            for pp in self.__process_list:
                time_, nops, process = pp
                if (process == proc):
                    start_time = time_
                    
            delay = finish_time - start_time - 2 * proc.get_number_of_operations()
            Tavg += delay
            if (delay > Tmax):
                Tmax = delay
        
        if (len(self.__process_finish_time.keys()) > 0):
            Tavg /= len(self.__process_finish_time.keys())
        
        if (self.__error == 0):
            print "[SystemManager] Testul a fost finalizat cu succes"
            self.__points = 25

            print "[SystemManager] Delay-ul maxim per proces:", Tmax, "(valoare maxima pentru bonus:", self.__max_max_processing_delay_for_bonus, ")"
            if (Tmax <= self.__max_max_processing_delay_for_bonus):
                self.__points += self.__bonus1

            print "[SystemManager] Delay-ul mediu per proces:", Tavg, "(valoare maxima pentru bonus:", self.__max_avg_processing_delay_for_bonus, ")"
            if (Tavg <= self.__max_avg_processing_delay_for_bonus):
                self.__points += self.__bonus2
            
            print "[SystemManager] Numar de cereri la RAM:", self.__num_ram_requests
            print "[SystemManager] Numar de cereri la cache-uri:", self.__num_cache_requests
            print "[SystemManager] Numar de cereri la seturile de registrii:", self.__num_register_requests

            Cost = self.__num_ram_requests * 100 + self.__num_cache_requests * 20 + self.__num_register_requests * 1
            print "[SystemManager] Costul cererilor efectuate:", Cost, "(valoare maxima pentru bonus:", self.__max_cost_for_bonus, ")"
            if (Cost <= self.__max_cost_for_bonus):
                self.__points += self.__bonus3
        
            print "[SystemManager] PUNCTAJ PE TEST:", self.__points
        
        self.__big_lock.release()
    
    def run(self):
        tstart = time.time()
        
        if (PRINT_STATISTICS == 1):
            StdOutLock.acquire()
            print "[SystemManager] Incepe pasul de timp 1"
            StdOutLock.release()

        self.__wait_for_registrations()

        self.__big_lock.acquire()
        self.__t = 1
        while (self.__t <= self.__TMAX):
            if (time.time() - tstart >= self.__time_limit):
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Limita de timp de", self.__time_limit, "secunde (timp de rulare pe testul curent) a fost depasita"
                StdOutLock.release()
                self.__big_lock.release()
                return
                
            self.__big_lock.release()

            # Submit processes.
            for elem in self.__process_list:
                time_, nops, process = elem
                if (time_ == self.__t):
                    if (DEBUG_MODE == 1):
                        StdOutLock.acquire()
                        print "[SystemManager] Trimit procesul=", process, "catre scheduler pentru a fi planificat pentru executie"
                        StdOutLock.release()
                    self.__scheduler_object.submit_process(process)

            old_time_step = self.__t
            new_time_step = self.__t + 1

            if (old_time_step == self.__TMAX):
                done = 1
            else:
                done = 0

            self.__wait_sem.release()
            wait_for_next_time_step(self, done)
            
            if (self.__t != new_time_step):
                self.__big_lock.acquire()
                self.__error = 1
                StdOutLock.acquire()
                print "[SystemManager] EROARE FATALA: Pasul de timp nu a fost incrementat corespunzator (valoare curent=", self.__t, ", valoare asteptata=", new_time_step, ")"
                StdOutLock.release()
                self.__big_lock.release()
            self.__big_lock.acquire()
        self.__big_lock.release()
                
        self.__final_check();

def test1():
    global __TOTAL_POINTS

    NUM_RAM_CELLS = 4
    NUM_RAM_REQS_PER_TIME_STEP = 3
    NUM_CACHE_CELLS = 3
    NUM_REGISTER_CELLS = 2
    NUM_PROCESSORS = 1
    NUM_CACHES = 1
    TMAX = 40
    TIME_LIMIT = 30.0 # sec
    
    lop1 = [["+", 0, 3], ["+", 1, 2]]
    lop2 = [["*", 0, 1], ["*", 2, 3]]
    p1 = Process(lop1)
    p2 = Process(lop2)
    process_list = [(2, p2), (3, p1)]

    init();

    register_cache_dic = {}
    processor_register_dic = {}    
    system_manager = SystemManager(TMAX, NUM_CACHES, NUM_PROCESSORS, NUM_PROCESSORS, NUM_RAM_CELLS, NUM_CACHE_CELLS, NUM_REGISTER_CELLS, NUM_RAM_REQS_PER_TIME_STEP, processor_register_dic, register_cache_dic, process_list, TIME_LIMIT, -1, 0, -1, 0, -1, 0)

    ram = get_RAM(NUM_RAM_CELLS, NUM_RAM_REQS_PER_TIME_STEP, system_manager)
    cache = get_cache(NUM_CACHE_CELLS, ram, system_manager)
    register_set = get_register_set(NUM_REGISTER_CELLS, cache, system_manager)
    processor = get_processor(register_set, system_manager)
    processor_list = [processor]
    scheduler = get_process_scheduler(processor_list, system_manager)

    register_cache_dic[register_set] = cache    
    processor_register_dic[processor] = register_set

    system_manager.start()
    ram.start()
    cache.start()
    register_set.start()
    processor.start()
    scheduler.start()

    system_manager.join()
    ram.join()
    cache.join()
    register_set.join()
    processor.join()
    scheduler.join()

    __TOTAL_POINTS += system_manager.get_points()

def test2():
    global __TOTAL_POINTS

    NUM_RAM_CELLS = 100
    NUM_RAM_REQS_PER_TIME_STEP = 10
    NUM_CACHE_CELLS = 20
    NUM_REGISTER_CELLS = 4
    NUM_PROCESSORS = 8
    NUM_CACHES = 8
    TMAX = 250
    TIME_LIMIT = 30.0 # sec
    
    NUM_PROCESSES = 56
    NUM_OPS_PER_PROCESS = 5
    NUM_ADDR_PER_OP = 3

    random.seed(19032011)

    process_list = []
    ram_addr = 0
    for i in range(NUM_PROCESSES):
        lop = []
        for j in range(NUM_OPS_PER_PROCESS):
            op = []
            if (random.randint(0, 1) == 0):
                op.append("+")
            else:
                op.append("*")
            for k in range(NUM_ADDR_PER_OP):
                ram_addr = ((i + 1) * (j + 1) * (k + 1)) % NUM_RAM_CELLS
                addr = ram_addr
                op.append(addr)
            lop.append(op)
        p = Process(lop)
        process_list.append((1, p))
    
    init();

    register_cache_dic = {}
    processor_register_dic = {}    
    system_manager = SystemManager(TMAX, NUM_CACHES, NUM_PROCESSORS, NUM_PROCESSORS, NUM_RAM_CELLS, NUM_CACHE_CELLS, NUM_REGISTER_CELLS, NUM_RAM_REQS_PER_TIME_STEP, processor_register_dic, register_cache_dic, process_list, TIME_LIMIT, 229, 3, 124.0, 3, 50224, 4)

    ram = get_RAM(NUM_RAM_CELLS, NUM_RAM_REQS_PER_TIME_STEP, system_manager)

    cache_list = []
    register_list = []
    processor_list = []
    for i in range(NUM_CACHES):
        cache = get_cache(NUM_CACHE_CELLS, ram, system_manager)
        cache_list.append(cache)
        
        register_set = get_register_set(NUM_REGISTER_CELLS, cache, system_manager)
        register_list.append(register_set)
        register_cache_dic[register_set] = cache    

        processor = get_processor(register_set, system_manager)
        processor_list.append(processor)
        processor_register_dic[processor] = register_set

    scheduler = get_process_scheduler(processor_list, system_manager)

    system_manager.start()
    ram.start()

    for cache in cache_list:
        cache.start()

    for register_set in register_list:
        register_set.start()

    for processor in processor_list:
        processor.start()

    scheduler.start()

    system_manager.join()
    ram.join()

    for cache in cache_list:
        cache.join()

    for register_set in register_list:
        register_set.join()

    for processor in processor_list:
        processor.join()

    scheduler.join()

    __TOTAL_POINTS += system_manager.get_points()

def test3():
    global __TOTAL_POINTS

    NUM_RAM_CELLS = 600
    NUM_RAM_REQS_PER_TIME_STEP = 10
    NUM_CACHE_CELLS = 60
    NUM_REGISTER_CELLS = 7
    NUM_PROCESSORS = 20
    NUM_CACHES = 8
    TMAX = 1000
    TIME_LIMIT = 240.0 # sec
    
    NUM_PROCESSES = 200
    NUM_OPS_PER_PROCESS = 10
    NUM_ADDR_PER_OP = 6

    random.seed(19032011)

    process_list = []
    for i in range(NUM_PROCESSES):
        lop = []
        for j in range(NUM_OPS_PER_PROCESS):
            op = []
            if (random.randint(0, 1) == 0):
                op.append("+")
            else:
                op.append("*")
            for k in range(NUM_ADDR_PER_OP):
                addr = (i + j + k + random.randint(0, 10)) % NUM_RAM_CELLS
                op.append(addr)
            lop.append(op)
        p = Process(lop)
        process_list.append((1, p))
    
    register_cache_dic = {}
    processor_register_dic = {}    
    system_manager = SystemManager(TMAX, NUM_CACHES, NUM_PROCESSORS, NUM_PROCESSORS, NUM_RAM_CELLS, NUM_CACHE_CELLS, NUM_REGISTER_CELLS, NUM_RAM_REQS_PER_TIME_STEP, processor_register_dic, register_cache_dic, process_list, TIME_LIMIT, 540, 3, 293.0, 3, 163500, 4)

    processor_cache_index = []
    for i in range(NUM_PROCESSORS):
        processor_cache_index.append(i % NUM_CACHES)

    init()

    ram = get_RAM(NUM_RAM_CELLS, NUM_RAM_REQS_PER_TIME_STEP, system_manager)

    cache_list = []
    register_list = []
    processor_list = []
    for i in range(NUM_CACHES):
        cache = get_cache(NUM_CACHE_CELLS, ram, system_manager)
        cache_list.append(cache)

    for i in range(NUM_PROCESSORS):
        cache = cache_list[processor_cache_index[i]]
        register_set = get_register_set(NUM_REGISTER_CELLS, cache, system_manager)
        register_list.append(register_set)
        register_cache_dic[register_set] = cache    

        processor = get_processor(register_set, system_manager)
        processor_list.append(processor)
        processor_register_dic[processor] = register_set

    scheduler = get_process_scheduler(processor_list, system_manager)

    system_manager.start()
    ram.start()

    for cache in cache_list:
        cache.start()

    for register_set in register_list:
        register_set.start()

    for processor in processor_list:
        processor.start()

    scheduler.start()

    system_manager.join()
    ram.join()

    for cache in cache_list:
        cache.join()

    for register_set in register_list:
        register_set.join()

    for processor in processor_list:
        processor.join()

    scheduler.join()

    __TOTAL_POINTS += system_manager.get_points()

if __name__=="__main__":

	print "### TESTUL 1 ###"
	test1()
	print "PUNCTAJ DUPA PRIMUL TEST:", __TOTAL_POINTS
	print "### TESTUL 2 ###"
	test2()
	print "PUNCTAJ TOTAL DUPA PRIMELE DOUA TESTE:", __TOTAL_POINTS
	print "### TESTUL 3 ###"
	test3()
	#print "PUNCTAJ TOTAL DUPA PRIMELE TREI TESTE:", __TOTAL_POINTS

   # print "CU ACORDUL ASISTENTULUI, PUNCTAJUL MAXIM PE CARE IL POTI OBTINE PE TEMA ESTE:", __TOTAL_POINTS + 25
