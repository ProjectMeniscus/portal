import sys
import portal.env as env

from multiprocessing import Process, Value

# Set up logging and get useful env variables for init
_LOG = env.get_logger('netpype')
_PROFILE_ENABLED = env.get('PROFILE', False)

# Enable profiling
if _PROFILE_ENABLED:
    _LOG.warn("""Warning! You have enabled profiling. To shut profiling off
        please unset the environment variable PROFILE.""")
    import cProfile

# Process states
_STATE_NEW = 0
_STATE_RUNNING = 1
_STATE_STOPPED = 2


class PersistentProcess(object):

    def __init__(self, name, **kwargs):
        self._name = name
        self._state = Value('i', _STATE_NEW)

        if not _PROFILE_ENABLED:
            self._process = Process(
                target=self._run, kwargs={'state': self._state})
        else:
            self._process = Process(
                target=self._run_profiled, kwargs={'state': self._state})

    def stop(self):
        self._state.value = _STATE_STOPPED
        self._process.join()
        self.on_halt()

    def start(self):
        if self._state.value != _STATE_NEW:
            raise WorkerStateError('Worker has been started once already.')

        self._state.value = _STATE_NEW
        self._process.start()

    def _run_profiled(self, state):
        cProfile.runctx('self._run(state)', globals(), locals())

    def _run(self, state):
        self.on_start()
        ## TODO: Fix to state Running
        while state.value == _STATE_NEW:
            try:
                self.process()
            except Exception as ex:
                self._state.value = _STATE_STOPPED
                _LOG.exception(ex)

    def process(self):
        raise NotImplementedError

    def on_start(self):
        pass

    def on_halt(self):
        pass
