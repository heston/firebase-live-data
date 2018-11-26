import datetime
import logging
from threading import Timer

DEFAULT_INTERVAL = datetime.timedelta(minutes=30)

_watchers = {}
logger = logging.getLogger(__name__)


class Watcher:
    def __init__(self, should_update, update_func, interval=None):
        self._should_update = should_update
        self._update_func = update_func
        self._interval = DEFAULT_INTERVAL if interval is None else interval
        self._should_cancel = False
        self.running = False

    def start(self):
        if self._should_cancel:
            logger.warning('Cannot start cancelled watcher: %s', id(self))
            return

        if self.running:
            logger.debug('Watcher already running: %s', id(self))
            return

        self._timer = Timer(self._interval.total_seconds(), self._action)
        self._timer.daemon = True
        self._timer.start()
        self.running = True

    def _action(self):
        if self._should_cancel:
            logger.debug('Stopping cancelled watcher: %s', id(self))
            self.running = False
            return

        logger.debug(
            'Watcher (%s) checking if update is requested: %s',
            id(self),
            self._should_update
        )

        if self._should_update():
            logger.debug(
                'Update requested. Watcher (%s) updating: %s',
                id(self),
                self._update_func
            )
            self._update_func()

        # Mark this timer as complete, and start a new timer
        self.running = False
        self.start()

    def cancel(self):
        self._should_cancel = True


def watch(name, should_update, update_func, interval=None):
    """Watch something and call a function when it should be updated.

    Arguments:
        name: A unique identifier for this watcher. May be any hashable value.
        should_update: Callable that returns True if the thing being watched
            should be updated, or False otherwise.
        update_func: Callable that updates the thing being watched when {should_update}
            returns True. Watching and updating occurs in a separate thread,
            so ensure this function is threadsafe.
        interval: datetime.timedelta indicating how often to poll {should_update}.
    """
    if name in _watchers:
        logger.warning(
            'Cannot start watcher. Watcher already running: %s',
            _watchers[name]
        )
        return

    watcher = Watcher(should_update, update_func, interval)
    logger.debug('New watcher started %s: %s', name, id(watcher))
    _watchers[name] = watcher
    watcher.start()


def cancel(name):
    if name not in _watchers:
        return None
    watcher = _watchers[name]
    if watcher:
        logger.debug('Cancelling watcher %s: %s', name, id(watcher))
        watcher.cancel()
    del _watchers[name]
    return True


def cancel_all():
    logger.debug('Stopping all watchers')
    for watcher in _watchers.values():
        watcher.cancel()
    _watchers.clear()
