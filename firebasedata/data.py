import collections
import datetime
import logging

from blinker import signal

logger = logging.getLogger(__name__)

Node = collections.namedtuple('Node', 'value parent key')


def get_path_list(path):
    path = path.strip('/')

    if path == '':
        return []

    return path.split('/')


class FirebaseData(dict):
    last_updated_at = None
    data_ttl = datetime.timedelta(hours=2)

    def _set_last_updated(self):
        self.last_updated_at = datetime.datetime.utcnow()

    def __init__(self, *args, **kwargs):
        self.event_prefix = kwargs.pop('event_prefix', name)
        self._set_last_updated()
        super().__init__(*args, **kwargs)

    def _get_signal_name(self, name):
        return '{}:{}'.format(self.event_prefix, name) if self.event_prefix else name

    def get_node_for_path(self, path):
        keys = get_path_list(path)
        node = self
        p_node = self
        p_key = None

        if not len(keys):
            key = None
        else:
            for key in keys:
                try:
                    new_node = node[key]
                    p_node = node
                    node = new_node
                except KeyError:
                    new_node = {}
                    node[key] = new_node
                    p_node = node
                    node = new_node
                except TypeError:
                    new_node = {}
                    p_new_node = {
                        key: new_node
                    }
                    p_node[p_key] = p_new_node
                    p_node = p_new_node
                    node = new_node
                p_key = key

        return Node(
            value=node,
            parent=p_node,
            key=key
        )

    def set(self, path, data):
        node = self.get_node_for_path(path)
        if not node.key:
            if data is None:
                node.value.clear()
            else:
                node.value.update(data)
        else:
            if data is None:
                del node.parent[node.key]
            else:
                node.parent[node.key] = data

        self._set_last_updated()
        signal(self._get_signal_name(path)).send(self, value=data)

    def merge(self, path, data):
        for rel_path, value in data.items():
            full_path = '{}/{}'.format(path, rel_path)
            self.set(full_path, value)

    def get(self, path):
        parts = get_path_list(path)
        node = self
        for part in parts:
            try:
                node = node[part]
            except (KeyError, TypeError):
                return None
        return node

    def is_stale(self):
        if not self.last_updated_at:
            logger.debug('Data is stale: %s', self)
            return True

        stale = datetime.datetime.utcnow() - self.last_updated_at > self.data_ttl
        if stale:
            logger.debug('Data is stale: %s', self)
        else:
            logger.debug('Data is fresh: %s', self)
        return stale

    def __repr__(self):
        tmpl = '{cls}(id={id}, last_updated_at={ts}, data={data})'
        return tmpl.format(
            cls=type(self).__name__,
            id=id(self),
            ts=self.last_updated_at,
            data=super().__repr__(),
        )
