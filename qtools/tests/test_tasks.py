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
        # Task callback: check the result
        assert _result == x * x

    
    # Operation task
    # --------------
    def operation(self, x, y, coeff=1):
        time.sleep(.1)
        return coeff * (x + y)
        
    @staticmethod
    def operation_done(x, y, coeff=1, _result=None):
        assert _result == coeff * (x + y)
    
        

#------------------------------------------------------------------------------
# Run task in external threads.
#------------------------------------------------------------------------------
def test_tasksinthread_square():
    """Tests a simple task in an external thread."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.square(3)
    tasks.join()
    
def test_tasksinthread_operation():
    """Tests a simple task in an external thread."""
    tasks = qtools.TasksInThread(TestTasks)
    tasks.operation(3, 4, coeff=2)
    tasks.join()


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
    
    

