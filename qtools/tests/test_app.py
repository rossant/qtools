"""Test the tasks module with use_master_thread=False. This means that
the master loop happens on the GUI thread and not on an external thread. It
is implemented with a QTimer instead. This way, we ensure that signals
emitted when a remote task is done are emitted on the main GUI thread.
"""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------
import time
import sys
import os
import traceback

from nose.tools import raises

from qtools import QtCore, QtGui
import qtools


#------------------------------------------------------------------------------
# Utility functions
#------------------------------------------------------------------------------
def get_application():
    """Get the current QApplication, or create a new one."""
    app_created = False
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtGui.QCoreApplication(sys.argv)
        app_created = True
    return app, app_created


#------------------------------------------------------------------------------
# Test tasks.
#------------------------------------------------------------------------------
class TestTasks(QtCore.QObject):
    squareDone = QtCore.pyqtSignal(int)

    # Constructor
    # -----------
    def __init__(self, parent=None):
        super(TestTasks, self).__init__(parent)
    
    
    # Square task
    # -----------
    def square(self, x):
        time.sleep(.1)
        return x * x
        
    def square_done(self, x, _result=None):
        self.squareDone.emit(_result)
        
    
    # Operation task
    # --------------
    def operation(self, x, y, coeff=1):
        time.sleep(.1)
        return coeff * (x + y)


#------------------------------------------------------------------------------
# Run task in external threads.
#------------------------------------------------------------------------------
tasks0 = None
tasks1 = None

def main0():
    global tasks0, tasks1
    
    tasks0 = qtools.TasksInThread(TestTasks, use_master_thread=False)
    tasks0.squareDone.connect(square_done)
    tasks0.square(3)
    
    tasks1 = qtools.TasksInProcess(TestTasks, use_master_thread=False)
    tasks1.operation(3, 4, coeff=2)
    
    
#------------------------------------------------------------------------------
# Start the Qt application
#------------------------------------------------------------------------------
R = False
def square_done(x):
    assert x == 9
    global R
    R = True

def exit():
    
    global tasks0, tasks1
    tasks0.join()
    tasks1.join()
    
    app = QtCore.QCoreApplication.instance()
    app.exit()
    
def wrap(fun):
    def wrapped():
        try:
            fun()
        except Exception as e:
            print(traceback.format_exc())
    return wrapped
    
def start_delayed(fun, delay):
    _timer_master = QtCore.QTimer()
    _timer_master.setSingleShot(True)
    _timer_master.setInterval(int(delay * 1000))
    _timer_master.timeout.connect(wrap(fun))
    _timer_master.start()
    return _timer_master
    
def main():
    app, app_created = get_application()
    app.references = set()
    
    # Launch tasks.
    t0 = start_delayed(main0, 0)
    
    # Exit.
    t2 = start_delayed(exit, 1.)
    
    if app_created:
        app.exec_()
        
    assert R

def setup():
    main()
    
def test():
    pass

def teardown():
    pass
        
if __name__ == '__main__':
    main()
    
    