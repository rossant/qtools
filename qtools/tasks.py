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
from qtpy import QtCore


#------------------------------------------------------------------------------
# Global variables
#------------------------------------------------------------------------------
FINISHED = '__END__'

__all__ = ['TasksInQThread', 'TasksInThread', 'TasksInProcess']



#------------------------------------------------------------------------------
# Tasks In Thread
#------------------------------------------------------------------------------
class TasksInThread(object):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def __init__(self, cls, *initargs, **initkwargs):
        self._qin = Queue()
        self._qout = Queue()
        # self._queue = Queue()
        # self._results = []
        # If impatient, the queue will always process only the last tasks
        # and not the intermediary ones.
        self.impatient = initkwargs.pop('impatient', None)
        # arguments of the task class constructor
        self.initargs, self.initkwargs = initargs, initkwargs
        # create the underlying task object
        self.task_class = cls
        self.task_obj = cls(*self.initargs, **self.initkwargs)
        # start the worker thread
        self.start()
        
    def start(self):
        """Start the worker thread."""
        self._thread_in = Thread(target=self._start)
        self._thread_in.daemon = True
        self._thread_in.start()
        # start the client thread that processes the results sent back
        # from the worker thread
        self._thread_out = Thread(target=self._retrieve)
        self._thread_out.daemon = True
        self._thread_out.start()
        
    def join(self):
        """Order to stop the queue as soon as all tasks have finished."""
        self._qin.put(None)
        self._thread_in.join()
        self._thread_out.join()
    
    def _start(self):
        """Worker thread main function."""
        # while True:
            # r = self._qin.get()
            # # only process the last item
            # if self.impatient and not self._qin.empty():
                # continue
            # if r is None:
                # # tell the client thread to shut down as all tasks have finished
                # self._qout.put(FINISHED)
                # break
            # fun, args, kwargs = r
            # getattr(self.task_obj, fun)(*args, **kwargs)
            # obj = taskcls(*initargs, **initkwargs)
        while True:
            r = self._qin.get()
            if self.impatient and not self._qin.empty():
                continue
            if r is None:
                # tell the client thread to shut down as all tasks have finished
                self._qout.put(FINISHED)
                break
            method, args, kwargs = r
            if hasattr(self.task_obj, method):
                # evaluate the method of the task object, and get the result
                result = getattr(self.task_obj, method)(*args, **kwargs)
                # send back the task arguments, and the result
                kwargs_back = kwargs.copy()
                kwargs_back.update(_result=result)
                self._qout.put((method, args, kwargs_back))

    def _put(self, fun, *arg, **kwargs):
        """Put a function to process on the queue."""
        # print fun
        self._qin.put((fun, arg, kwargs))
        # print "hey"
        
    def _retrieve(self):
        # call done_callback for each finished result
        while True:
            r = self._qout.get()
            if r == FINISHED:
                break
            # the method that has been called on the worked, with an additional
            # parameter _result in kwargs, containing the result of the task
            method, args, kwargs = r
            done_name = method + '_done'
            getattr(self.task_class, done_name)(*args, **kwargs)
        
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
    def start(self):
        jobself = self
        
        class TasksInThread(QtCore.QThread):
            def run(self):
                jobself._start()
                
            def join(self):
                self.wait()
                
        self._thread = TasksInThread()
        self._thread.start(QtCore.QThread.LowPriority)


def inqthread(cls):
    class MyTasksInThread(TasksInQThread):
        def __init__(self, *initargs, **initkwargs):
            super(MyTasksInThread, self).__init__(cls, *initargs, **initkwargs)
    return MyTasksInThread


#------------------------------------------------------------------------------
# Tasks in Process
#------------------------------------------------------------------------------
def _run(taskcls, initargs, initkwargs, qin, qout):
    obj = taskcls(*initargs, **initkwargs)
    while True:
        p = qin.get()
        if p is None:
            # tell the client thread to shut down as all tasks have finished
            qout.put(FINISHED)
            break
        method, args, kwargs = p
        if hasattr(obj, method):
            # evaluate the method of the task object, and get the result
            result = getattr(obj, method)(*args, **kwargs)
            # send back the task arguments, and the result
            kwargs_back = kwargs.copy()
            kwargs_back.update(_result=result)
            qout.put((method, args, kwargs_back))


class TasksInProcess(object):
    """Implements a queue containing jobs (Python methods of a base class
    specified in `cls`)."""
    def __init__(self, cls, *initargs, **initkwargs):
        # self._results = []
        # If impatient, the queue will always process only the last tasks
        # and not the intermediary ones.
        self.impatient = initkwargs.pop('impatient', None)
        # arguments of the task class constructor
        self.initargs, self.initkwargs = initargs, initkwargs
        # create the underlying task object
        self.task_class = cls
        # start the worker thread
        self.start()
        
    def start(self):
        """Start the worker thread."""
        self._qin = Queue()
        self._qout = Queue()
        self._process = Process(target=_run, args=(self.task_class, 
            self.initargs, self.initkwargs, self._qin, self._qout,))
        self._process.start()
        # start the client thread that processes the results sent back
        # from the worker process
        self._thread = Thread(target=self._retrieve)
        self._thread.daemon = True
        self._thread.start()
        
    def join(self):
        """Order to stop the queue as soon as all tasks have finished."""
        self._qin.put(None)
        self._process.join()
        self._thread.join()

    def _put(self, fun, *args, **kwargs):
        """Put a function to process on the queue."""
        self._qin.put((fun, args, kwargs))
        
    def _retrieve(self):
        # call done_callback for each finished result
        while True:
            r = self._qout.get()
            if r == FINISHED:
                break
            # the method that has been called on the worked, with an additional
            # parameter _result in kwargs, containing the result of the task
            method, args, kwargs = r
            done_name = method + '_done'
            getattr(self.task_class, done_name)(*args, **kwargs)
        
    def __getattr__(self, name):
        if hasattr(self.task_class, name):
            return lambda *args, **kwargs: self._put(name, *args, **kwargs)


