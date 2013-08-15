import sys
from qtools.qtpy import QtCore, QtGui

def get_application():
    """Get the current QApplication, or create a new one."""
    app_created = False
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtGui.QApplication(sys.argv)
        app_created = True
    return app, app_created
    
def show_window(window, **kwargs):
    """Create a Qt window in Python, or interactively in IPython with Qt GUI
    event loop integration:
    
        # in ~/.ipython/ipython_config.py
        c.TerminalIPythonApp.gui = 'qt'
        c.TerminalIPythonApp.pylab = 'qt'
    
    See also:
        http://ipython.org/ipython-doc/dev/interactive/qtconsole.html#qt-and-the-qtconsole
    
    """
    app, app_created = get_application()
    app.references = set()
    if not isinstance(window, QtGui.QWidget):
        window = window(**kwargs)
    app.references.add(window)
    window.show()
    if app_created:
        app.exec_()
    return window

