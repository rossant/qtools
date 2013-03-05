"""Test the tasks module.
"""
import time
import qtools


#------------------------------------------------------------------------------
# Test tasks.
#------------------------------------------------------------------------------
class TestTasks(object):
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
    def nocallback(self, x):
        return x
        

#------------------------------------------------------------------------------
# Run task in external threads.
#------------------------------------------------------------------------------
def test_tasksinthread_square():
    """Tests a simple task in an external thread."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.square(3)
    tasks.join()
    assert tasks.get_result() == 9
    
def test_tasksinthread_operation():
    """Tests a simple task in an external thread."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.operation(3, 4, coeff=2)
    tasks.join()
    assert tasks.get_result() == 14

def test_tasksinthread_nocallback():
    tasks = qtools.TasksInThread(TestTasks)
    tasks.nocallback(3)
    tasks.join()
    assert tasks.get_result() == 3
    

#------------------------------------------------------------------------------
# Run tasks in external processes.
#------------------------------------------------------------------------------
def test_tasksinprocess_square():
    """Tests a simple task in an external process."""
        
    tasks = qtools.TasksInProcess(TestTasks)
    tasks.square(3)
    tasks.join()
    
def test_tasksinprocess_operation():
    """Tests a simple task in an external thread."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.operation(3, 4, coeff=2)
    tasks.join()
    
    

