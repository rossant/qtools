"""Classes to easily implement Qt-friendly computational tasks running in
external threads or processes, with a simple API.
"""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------
import time
import inspect
from Queue import Queue
from threading import Thread
from multiprocessing import Process, Queue
# Need to handle threads in a particular way with Qt.
try:
    from qtpy.QtCore import QThread
    def _start_qthread(obj, method_name):
        """Start a QThread."""
        class MyQThread(QThread):
            def run(self):
                getattr(obj, method_name)()
            def join(self):
                self.wait()
        qthread = MyQThread()
        qthread.start(QThread.LowPriority)
        return qthread
# Or use standard threads if Qt is not available.
except ImportError:
    def _start_qthread(obj, method_name):
        """Start a Thread normally."""
        fun = getattr(obj, method_name)
        _thread = Thread(target=fun)
        _thread.start()
        return _thread


#------------------------------------------------------------------------------
# Global variables
#------------------------------------------------------------------------------
FINISHED = '__END__'

__all__ = ['TasksInQThread', 'TasksInThread', 'TasksInProcess',
           'inthread', 'inqthread']



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
        

def worker_loop(task_obj, qin, qout, impatient=False):
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
        method, args, kwargs = r
        if hasattr(task_obj, method):
            # evaluate the method of the task object, and get the result
            result = getattr(task_obj, method)(*args, **kwargs)
            # send back the task arguments, and the result
            kwargs_back = kwargs.copy()
            kwargs_back.update(_result=result)
            qout.put((method, args, kwargs_back))
    
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
        self._qin = Queue()
        self._qout = Queue()
        self.results = []
        # If impatient, the queue will always process only the last tasks
        # and not the intermediary ones.
        self.impatient = initkwargs.pop('impatient', None)
        # arguments of the task class constructor
        self.initargs, self.initkwargs = initargs, initkwargs
        # create the underlying task object
        self.task_class = cls
        self.instanciate_task()
        self.start()
        
        
    # Methods to override
    # -------------------
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
        return self.results[index][2]['_result']
    
    
    # Internal methods
    # ----------------
    def _start(self):
        """Worker main function."""
        worker_loop(self.task_obj, self._qin, self._qout, self.impatient)

    def _start_thread(self, fun, daemon=True):
        _thread = Thread(target=fun)
        _thread.daemon = daemon
        _thread.start()
        return _thread
        
    def _retrieve(self):
        """Master main function."""
        master_loop(self.task_class, self._qin, self._qout, self.results)
        
    def _put(self, fun, *arg, **kwargs):
        """Put a function to process on the queue."""
        self._qin.put((fun, arg, kwargs))
        
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
    def instanciate_task(self):
        self.task_obj = self.task_class(*self.initargs, **self.initkwargs)
        
    def start(self):
        self.start_worker()
        self.start_master()
    
    def start_worker(self):
        """Start the worker thread or process."""
        self._thread_worker = self._start_thread(self._start)
        
    def start_master(self):
        """Start the master thread, used to retrieve the results."""
        self._thread_master = self._start_thread(self._retrieve)
        
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
# Tasks in Thread for Qt
#------------------------------------------------------------------------------
class TasksInQThread(TasksInThread):
    """Job Queue supporting Qt signals and slots."""
    def start_worker(self):
        self._thread_worker = _start_qthread(self, '_start')

    def start_master(self):
        self._thread_master = _start_qthread(self, '_retrieve')
        

def inqthread(cls):
    class MyTasksInThread(TasksInQThread):
        def __init__(self, *initargs, **initkwargs):
            super(MyTasksInThread, self).__init__(cls, *initargs, **initkwargs)
    return MyTasksInThread


#------------------------------------------------------------------------------
# Tasks in Process
#------------------------------------------------------------------------------
class TasksInProcess(TasksBase):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def instanciate_task(self):
        self.task_obj = ToInstanciate(self.task_class, *self.initargs, **self.initkwargs)
    
    def start(self):
        self.start_worker()
        self.start_master()
    
    def start_worker(self):
        """Start the worker thread or process."""
        self._process_worker = Process(target=worker_loop, args=(self.task_obj, 
            self._qin, self._qout, self.impatient))
        self._process_worker.start()
        
    def start_master(self):
        """Start the master thread, used to retrieve the results."""
        self._thread_master = self._start_thread(self._retrieve)
        
    def join(self):
        """Stop the worker and master as soon as all tasks have finished."""
        self._qin.put(FINISHED)
        self._process_worker.join()
        # self._qout.put(FINISHED)
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
            return self._put('__getattr__', name)[2]['_result']
        # raise AttributeError("'{0:s}' is not an attribute of '{1:s}'".format(
            # name, self))
