import datetime
import logging
import queue
import threading

from blinker.base import Namespace

from . import data

logger = logging.getLogger(__name__)


class LiveData(object):
    def __init__(self, pyrebase_app, root_path, ttl=None):
        self._app = pyrebase_app
        self._root_path = root_path
        self._ttl = ttl
        self._db = self._app.database()
        self._streams = {}
        self._gc_streams = queue.Queue()
        self._gc_thread = None
        self._cache = None
        self.events = Namespace()


    def get_data(self):
        if self._cache is None:
            # Fetch data now
            value = self._db.child(self._root_path).get().val()
            self._cache = data.FirebaseData(value)
            # Listen for updates
            self.listen()

        return self._cache

    def set_data(self, path, data):
        path_list = data.get_path_list(path)
        child = self._db.child(self._root_path)

        for path_part in path_list:
            child = child.child(path_part)
        child.set(data)

    def is_stale(self):
        if self._ttl is None:
            return False

        data = self.get_data()
        if not data or not data.last_updated_at:
            logger.debug('Data is stale: %s', data)
            return True

        stale = datetime.datetime.utcnow() - data.last_updated_at > self._ttl
        if stale:
            logger.debug('Data is stale: %s', data)
        else:
            logger.debug('Data is fresh: %s', data)
        return stale

    def signal(self, *args, **kwargs):
        return self.events.signal(*args, **kwargs)

    def listen(self):
        stream = self._db.child(self._root_path).stream(self._stream_handler)
        self._streams[id(stream)] = stream
        self._start_stream_gc()

    def reset(self):
        logger.debug('Resetting all data')
        self.hangup(block=False)
        self._cache.clear()

    def hangup(self, block=True):
        logger.debug('Marking all streams for shut down')

        for stream in self._streams.values():
            self._gc_streams.put(stream)

        if block:
            self._gc_streams.join()

    def _set_path_value(self, path, value):
        data = self.get_data()
        data.set(path, value)
        self.events.signal(path).send(data, value=value)

    def _put_handler(self, path, value):
        logger.debug('PUT: path=%s data=%s', path, value)
        self._set_path_value(path, value)

    def _patch_handler(self, path, all_values):
        logger.debug('PATCH: path=%s data=%s', path, all_values)

        for rel_path, value in all_values.items():
            full_path = '{}/{}'.format(path, rel_path)
            self._set_path_value(path, value)

    def _stream_handler(self, message):
        logger.debug('STREAM received: %s', message)
        handlers = {
            'put': self._put_handler,
            'patch': self._patch_handler,
        }
        handler = handlers.get(message['event'])

        if handler:
            handler(message['path'], message['data'])
        else:
            logger.warn('No handler configured for message: %s', message)

    def _gc_stream_worker(self):
        while True:
            stream = self._gc_streams.get()
            logger.debug('Closing stream: %s', stream)
            stream.close()
            self._gc_streams.task_done()

            try:
                del self._streams[id(stream)]
            except:
                pass

            logger.debug('Stream closed: %s', stream)

    def _start_stream_gc(self):
        if self._gc_thread is None:
            self._gc_thread = threading.Thread(target=self._gc_stream_worker, daemon=True)
            self._gc_thread.start()
