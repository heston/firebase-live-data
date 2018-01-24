import logging
import queue
import threading

from . import data

logger = logging.getLogger(__name__)


class LiveData(object):

    def __init__(self, pyrebase_app, root_path, event_prefix=None):
        self._app = pyrebase_app
        self._db = self.app.database()
        self._streams = {}
        self._gc_streams = queue.Queue()
        self._gc_thread = None
        self._cache = {}
        self._root_path = root_path
        self._event_prefix = event_prefix

    def get_data(self):
        try:
            return self._cache[self._root_path]
        except KeyError:
            # Fetch data now
            data = db.child(self._root_path).get().val()
            self._cache[self._root_path] = data.FirebaseData(
                data,
                event_prefix=self._event_prefix
            )
            # Listen for updates
            self.listen()
            return self._cache[self._root_path]

    def set_data(self, path, data):
        path_list = data.get_path_list(path)
        child = self._db.child(self._root_path)
        for path_part in path_list:
            child = child.child(path_part)
        child.set(data)

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

    def _put_handler(self, path, data):
        logger.debug('PUT: path=%s data=%s', path, data)
        data = self.get_data()
        data.set(path, data)

    def _patch_handler(self, path, data):
        logger.debug('PATCH: path=%s data=%s', path, data)
        data = self.get_data()
        data.merge(path, data)


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
