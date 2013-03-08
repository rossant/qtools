"""Test the tasks module.
"""
import time
from nose.tools import raises
import qtools


#------------------------------------------------------------------------------
# Test tasks.
#------------------------------------------------------------------------------
class TestTasks(object):
    # Constructor
    # -----------
    def __init__(self, kwarg0=None):
        self.kwarg0 = kwarg0
    
    # Square task
    # -----------
    def square(self, x):
        time.sleep(.1)
        return x * x
        
    @staticmethod
    def square_done(x, _result=None):
        pass

    
    # Operation task
    # --------------
    def operation(self, x, y, coeff=1):
        time.sleep(.1)
        return coeff * (x + y)
        
    @staticmethod
    def operation_done(x, y, coeff=1, _result=None):
        pass
    
    
    # Callback-free task
    # ------------------
    def nocallback(self, x):
        return x

    
    # Method raising an exception
    # ---------------------------
    def exception(self):
        raise TypeError("This is an exception.")
    
    
# Task with decorator and state
# -----------------------------
@qtools.inthread
class TestTasksWithState(object):
    def __init__(self, x):
        self.x = x
        
    def square(self):
        self.y = self.x ** 2


#------------------------------------------------------------------------------
# Run task in external threads.
#------------------------------------------------------------------------------
def test_tasksinthread_square():
    tasks = qtools.TasksInThread(TestTasks)
    tasks.square(3)
    tasks.join()
    assert tasks.get_result() == 9
    
def test_tasksinthread_operation():
    tasks = qtools.TasksInThread(TestTasks)
    tasks.operation(3, 4, coeff=2)
    tasks.join()
    assert tasks.get_result() == 14

def test_tasksinthread_nocallback():
    """Test a task without callback."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.nocallback(3)
    tasks.join()
    assert tasks.get_result() == 3

@raises(TypeError)
def test_taskinthread_exception():
    tasks = qtools.TasksInThread(TestTasks)
    # an exception happens in the thread, there's just a warning message 
    # displayed, the worker thread does not die
    tasks.exception()
    tasks.join()
    # now this raises an exception on the client
    tasks.get_result()


#------------------------------------------------------------------------------
# Run task with decorator in external threads.
#------------------------------------------------------------------------------
def test_tasksinthread_decorator_square():
    tasks = TestTasksWithState(3)
    tasks.square()
    tasks.join()
    assert tasks.y == 9


#------------------------------------------------------------------------------
# Run tasks in external processes.
#------------------------------------------------------------------------------
def test_tasksinprocess_square():
    tasks = qtools.TasksInProcess(TestTasks)
    tasks.square(3)
    tasks.join()
    
def test_tasksinprocess_operation():
    tasks = qtools.TasksInThread(TestTasks)
    tasks.operation(3, 4, coeff=2)
    tasks.join()
    
def test_tasksinprocess_constructor():
    tasks = qtools.inprocess(TestTasks)(7)
    tasks.operation(3, 4, coeff=2)
    tasks.join()
    
def test_tasksinprocess_state():
    tasks = qtools.inprocess(TestTasks)(7)
    tasks.operation(3, 4, coeff=2)
    x = tasks.kwarg0
    assert x == 7
    tasks.join()
    

