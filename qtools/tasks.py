"""Classes to easily implement Qt-friendly computational tasks running in
external threads or processes, with a simple API.
"""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------
import time
import traceback
import inspect
import logging
from Queue import Queue as tQueue
from threading import Thread
from multiprocessing import Process, Queue as pQueue
# Need to handle threads in a particular way with Qt.
try:
    from qtpy.QtCore import QThread
    # def _start_thread(obj, method_name):
    def _start_thread(fun, *args, **kwargs):
        """Start a QThread."""
        class MyQThread(QThread):
            def run(self):
                # fun = getattr(obj, method_name)
                # getattr(obj, method_name)()
                fun(*args, **kwargs)
            def join(self):
                self.wait()
        qthread = MyQThread()
        qthread.start(QThread.LowPriority)
        return qthread
# Or use standard threads if Qt is not available.
except ImportError:
    # def _start_thread(obj, method_name):
    def _start_thread(fun, *args, **kwargs):
        """Start a Thread normally."""
        # fun = getattr(obj, method_name)
        _thread = Thread(target=fun, args=args, kwargs=kwargs)
        _thread.start()
        return _thread


#------------------------------------------------------------------------------
# Global variables
#------------------------------------------------------------------------------
FINISHED = '__END__'

__all__ = [
           'TasksBase',
           'TasksInThread',
           'TasksInProcess',
           'inthread',
           'inprocess',
           ]


#------------------------------------------------------------------------------
# Base Tasks class
#------------------------------------------------------------------------------
class ToInstanciate(object):
    def __init__(self, task_class, *initargs, **initkwargs):
        self.task_class = task_class
        self.initargs = initargs
        self.initkwargs = initkwargs
    
    def instanciate(self):
        return self.task_class(*self.initargs, **self.initkwargs)
        

def worker_loop(task_obj, qin, qout, qout_sync, impatient=False):
    """Worker loop that processes jobs send by the master."""
    # instanciate the task object if needed
    if isinstance(task_obj, ToInstanciate):
        task_obj = task_obj.instanciate()
    while True:
        # import threading
        # print threading.current_thread().ident, "waiting"
        r = qin.get()
        # print threading.current_thread().ident, "got", r
        if r == FINISHED:
            # tell the client thread to shut down as all tasks have finished
            qout.put(FINISHED)
            break
        if impatient and not qin.empty():
            continue
        method, args, kwargs, sync = r
        if hasattr(task_obj, method):# or method == '__getattr__':
            # evaluate the method of the task object, and get the result
            try:
                result = getattr(task_obj, method)(*args, **kwargs)
            except Exception as e:
                msg = traceback.format_exc()
                print("An exception occurred: {0:s}.".format(msg))
                result = e
            # send back the task arguments, and the result
            kwargs_back = kwargs.copy()
            kwargs_back.update(_result=result)
            # using different queues according to whether the caller used
            # a sync or async method
            if sync:
                q = qout_sync
            else:
                q = qout
            q.put((method, args, kwargs_back))
    
def master_loop(task_class, qin, qout, results=[]):
    """Master loop that retrieves jobs processed by the worker."""
    while True:
        r = qout.get()
        if r == FINISHED:
            break
        # the method that has been called on the worked, with an additional
        # parameter _result in kwargs, containing the result of the task
        method, args, kwargs = r
        results.append((method, args, kwargs))
        done_name = method + '_done'
        if hasattr(task_class, done_name):
            getattr(task_class, done_name)(*args, **kwargs)


class TasksBase(object):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def __init__(self, cls, *initargs, **initkwargs):
        self.results = []
        # If impatient, the queue will always process only the last tasks
        # and not the intermediary ones.
        self.impatient = initkwargs.pop('impatient', None)
        # arguments of the task class constructor
        self.initargs, self.initkwargs = initargs, initkwargs
        # create the underlying task object
        self.task_class = cls
        self.init_queues()
        self.instanciate_task()
        self.start()
        
        
    # Methods to override
    # -------------------
    def init_queues(self):
        """Initialize the two queues (two directions), named _qin and _qout.
        
        """
        pass
    
    def instanciate_task(self):
        """Instanciate the task self.task_obj.
        
        This object can be a ToInstanciate instance if the task needs
        to be instanciated in a separated thread or process.
        
        """
        pass
    
    def start(self):
        pass
    
    def start_worker(self):
        """Start the worker thread or process."""
        pass
        
    def start_master(self):
        """Start the master thread, used to retrieve the results."""
        pass
        
    def join(self):
        """Stop the worker and master as soon as all tasks have finished."""
        pass
    
    
    # Public methods
    # --------------
    def get_result(self, index=-1):
        result = self.results[index][2]['_result']
        if isinstance(result, Exception):
            raise result
        return result
    
    
    # Internal methods
    # ----------------
    def _start(self):
        """Worker main function."""
        worker_loop(self.task_obj, self._qin, self._qout, self._qout_sync,
            self.impatient)

    def _retrieve(self):
        """Master main function."""
        master_loop(self.task_class, self._qin, self._qout, self.results)
        
    def _put(self, fun, *arg, **kwargs):
        """Put a function to process on the queue."""
        # True if the call to the task method should wait and return the result
        sync = kwargs.pop('_sync', None)
        self._qin.put((fun, arg, kwargs, sync))
        if sync:
            return self._qout_sync.get()
        
    def __getattr__(self, name):
        if hasattr(self.task_obj, name):
            v = getattr(self.task_obj, name)
            # wrap the task object's method in the Job Queue so that it 
            # is pushed in the queue instead of executed immediately
            if inspect.ismethod(v):
                return lambda *args, **kwargs: self._put(name, *args, **kwargs)
            # if the attribute is a task object's property, just return it
            else:
                return v
        raise AttributeError("'{0:s}' is not an attribute of '{1:s}'".format(
            name, self))


#------------------------------------------------------------------------------
# Tasks In Thread
#------------------------------------------------------------------------------
class TasksInThread(TasksBase):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def init_queues(self):
        self._qin = tQueue()
        self._qout = tQueue()
        self._qout_sync = tQueue()
    
    def instanciate_task(self):
        self.task_obj = self.task_class(*self.initargs, **self.initkwargs)
        
    def start(self):
        self.start_worker()
        self.start_master()
    
    def start_worker(self):
        """Start the worker thread or process."""
        self._thread_worker = _start_thread(self._start)
        
    def start_master(self):
        """Start the master thread, used to retrieve the results."""
        self._thread_master = _start_thread(self._retrieve)
        
    def join(self):
        """Stop the worker and master as soon as all tasks have finished."""
        self._qin.put(FINISHED)
        self._thread_worker.join()
        # self._qout.put(FINISHED)
        self._thread_master.join()

def inthread(cls):
    class MyTasksInThread(TasksInThread):
        def __init__(self, *initargs, **initkwargs):
            super(MyTasksInThread, self).__init__(cls, *initargs, **initkwargs)
    return MyTasksInThread


#------------------------------------------------------------------------------
# Tasks in Process
#------------------------------------------------------------------------------
class TasksInProcess(TasksBase):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def init_queues(self):
        self._qin = pQueue()
        self._qout = pQueue()
        self._qout_sync = pQueue()
        
    def instanciate_task(self):
        self.task_obj = ToInstanciate(self.task_class, *self.initargs, **self.initkwargs)
    
    def start(self):
        self.start_worker()
        self.start_master()
    
    def start_worker(self):
        """Start the worker thread or process."""
        self._process_worker = Process(target=worker_loop, args=(self.task_obj, 
            self._qin, self._qout, self._qout_sync, self.impatient))
        self._process_worker.start()
        
    def start_master(self):
        """Start the master thread, used to retrieve the results."""
        self._thread_master = _start_thread(self._retrieve)
        
    def join(self):
        """Stop the worker and master as soon as all tasks have finished."""
        self._qin.put(FINISHED)
        self._thread_master.join()
        self._process_worker.terminate()
        self._process_worker.join()
    
    def terminate(self):
        self._process_worker.terminate()
        self._process_worker.join()
        self._qout.put(FINISHED)
        self._thread_master.join()
        
    
    def __getattr__(self, name):
        # execute a method on the task object remotely
        if hasattr(self.task_class, name):
            v = getattr(self.task_class, name)
            # wrap the task object's method in the Job Queue so that it 
            # is pushed in the queue instead of executed immediately
            if inspect.ismethod(v):
                return lambda *args, **kwargs: self._put(name, *args, **kwargs)
            # if the attribute is a task object's property, just return it
            else:
                return v
        # or, if the requested name is a task object attribute, try obtaining
        # remotely
        else:
            result = self._put('__getattribute__', name, _sync=True)
            return result[2]['_result']

def inprocess(cls):
    class MyTasksInProcess(TasksInProcess):
        def __init__(self, *initargs, **initkwargs):
            super(MyTasksInProcess, self).__init__(cls, *initargs, **initkwargs)
    return MyTasksInProcess
    
    