import datetime
import logging
import queue
import threading

from blinker.base import Namespace

from . import data
from . import watcher

logger = logging.getLogger(__name__)
RETRY_INTERVAL = datetime.timedelta(minutes=1)


class LiveData(object):
    def __init__(self, pyrebase_app, root_path, ttl=None, retry_interval=None):
        self._app = pyrebase_app
        self._root_path = root_path
        self._ttl = ttl
        self._retry_interval = (
            RETRY_INTERVAL if retry_interval is None else retry_interval
        )
        self._db = self._app.database()
        self._streams = {}
        self._gc_streams = queue.Queue()
        self._gc_thread = None
        self._cache = None
        self.events = Namespace()

        self._handlers = {
            'put': self._put_handler,
            'patch': self._patch_handler,
        }

    def get_data(self):
        if self._cache is None:
            # Fetch data now
            value = self._db.child(self._root_path).get().val()
            self._cache = data.FirebaseData(value)
            # Listen for updates
            self.listen()

        return self._cache

    def get_data_silent(self):
        try:
            return self.get_data()
        except Exception:
            logger.exception('Error getting data')

    def set_data(self, path, value):
        path_list = data.get_path_list(path)
        child = self._db.child(self._root_path)

        for path_part in path_list:
            child = child.child(path_part)
        child.set(value)

    def is_stale(self):
        if self._ttl is None:
            return False

        data = self.get_data()
        if data is None or data.last_updated_at is None:
            logger.debug('Data is invalid: %s', data)
            return True

        stale = datetime.datetime.utcnow() - data.last_updated_at > self._ttl
        if stale:
            logger.debug('Data is stale: %s', data)
        else:
            logger.debug('Data is fresh: %s', data)
        return stale

    def signal(self, path, doc=None):
        norm_path = data.normalize_path(path)
        return self.events.signal(norm_path, doc=doc)

    def listen(self):
        stream = self._db.child(self._root_path).stream(self._stream_handler)
        self._streams[id(stream)] = stream
        self._start_stream_gc()
        watcher.watch(
            id(self),
            self.is_stale,
            self.restart,
            interval=self._ttl
        )
        # If the stream and stale watcher are established,
        # the metawatcher is no longer needed.
        self.cancel_metawatcher()

    def get_metawatcher_name(self):
        return 'meta_{}'.format(id(self))

    def start_metawatcher(self):
        watcher.watch(
            self.get_metawatcher_name(),
            lambda: self._cache is None,
            self.get_data_silent,
            interval=self._retry_interval
        )

    def cancel_metawatcher(self):
        watcher.cancel(self.get_metawatcher_name())

    def restart(self):
        self.reset()
        self.start_metawatcher()
        self.get_data_silent()

    def reset(self):
        logger.debug('Resetting all data')
        self.hangup(block=False)
        self._cache = None

    def hangup(self, block=True):
        logger.debug('Marking all streams for shut down')

        watcher.cancel(id(self))

        for stream in self._streams.values():
            self._gc_streams.put(stream)

        if block:
            self._gc_streams.join()

    def _set_path_value(self, path, value):
        data = self.get_data()
        data.set(path, value)
        self._recurse_signal(path)

    def _recurse_signal(self, path):
        path_list = data.get_path_list(path)
        partial_path = ''
        value = self.get_data()

        self.signal('/').send(value, value=value.get(), path=path)
        for part in path_list:
            partial_path = '/'.join((partial_path, part))
            self.signal(partial_path).send(
                value,
                value=value.get(partial_path),
                path=path
            )

    def _put_handler(self, path, value):
        logger.debug('PUT: path=%s data=%s', path, value)
        self._set_path_value(path, value)

    def _patch_handler(self, path, all_values):
        logger.debug('PATCH: path=%s data=%s', path, all_values)

        for rel_path, value in all_values.items():
            full_path = data.normalize_path('{}/{}'.format(path, rel_path))
            self._set_path_value(full_path, value)

    def _valid_message(self, message):
        required_keys = [
            'event',
            'path',
            'data',
        ]

        valid_keys = all(k in message for k in required_keys)
        if not valid_keys:
            return False

        if message['event'] not in self._handlers:
            return False

        return True

    def _stream_handler(self, message):
        logger.debug('STREAM received: %s', message)
        if not self._valid_message(message):
            logger.warn('Invalid message: %s', message)
            return

        handler = self._handlers[message['event']]
        handler(message['path'], message['data'])

    def _gc_stream_worker(self):
        while True:
            stream = self._gc_streams.get()
            logger.debug('Closing stream: %s', stream)

            try:
                stream.close()
                del self._streams[id(stream)]
            except Exception as e:
                logger.warning('Error closing stream %s: %s', stream, e)
            else:
                logger.debug('Stream closed: %s', stream)

            self._gc_streams.task_done()

    def _start_stream_gc(self):
        if self._gc_thread is None:
            self._gc_thread = threading.Thread(target=self._gc_stream_worker, daemon=True)
            self._gc_thread.start()
