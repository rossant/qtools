try:
    from qtools.qtpy.QtCore import QObject
except ImportError:
    QObject = object
class GarbageCollector(QObject):

    '''
    Disable automatic garbage collection and instead collect manually
    every INTERVAL milliseconds.

    This is done to ensure that garbage collection only happens in the GUI
    thread, as otherwise Qt can crash.
    '''

    INTERVAL = 5000

    def __init__(self, parent, debug=False):
        QObject.__init__(self, parent)
        self.debug = debug

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.INTERVAL)
        #gc.set_debug(gc.DEBUG_SAVEALL)

    def check(self):
        #return self.debug_cycles()
        l0, l1, l2 = gc.get_count()
        if self.debug:
            print ('gc_check called:', l0, l1, l2)
        if l0 > self.threshold[0]:
            num = gc.collect(0)
            if self.debug:
                print ('collecting gen 0, found:', num, 'unreachable')
            if l1 > self.threshold[1]:
                num = gc.collect(1)
                if self.debug:
                    print ('collecting gen 1, found:', num, 'unreachable')
                if l2 > self.threshold[2]:
                    num = gc.collect(2)
                    if self.debug:
                        print ('collecting gen 2, found:', num, 'unreachable')

    def debug_cycles(self):
        gc.collect()
        for obj in gc.garbage:
            print (obj, repr(obj), type(obj))
