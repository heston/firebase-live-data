import collections
import datetime
import os.path
import logging

logger = logging.getLogger(__name__)
Node = collections.namedtuple('Node', 'value parent key')


def get_path_list(path):
    path = path.strip('/')

    if path == '':
        return []

    return path.split('/')


def normalize_path(path):
    return os.path.normpath(
        '/'.join(
            get_path_list(path)
        )
    )


class FirebaseData(dict):
    last_updated_at = None

    def __init__(self, *args, **kwargs):
        self._set_last_updated()

        try:
            super().__init__(*args, **kwargs)
        except (TypeError, ValueError):
            if len(args) == 1:
                super().__init__()
                initial = args[0]
                self._default_value = initial
            else:
                raise

    def _set_last_updated(self):
        self.last_updated_at = datetime.datetime.utcnow()

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

    def _update(self, node, value):
        try:
            node.update(value)
            try:
                del self._default_value
            except AttributeError:
                pass
        except (TypeError, ValueError):
            self._default_value = value

    def set(self, path, value):
        node = self.get_node_for_path(path)

        if not node.key:
            if value is None:
                node.value.clear()
            else:
                self._update(node.value, value)
        else:
            if value is None:
                del node.parent[node.key]
            else:
                self._update(node.parent, {node.key: value})

        self._set_last_updated()

    def get(self, path='/'):
        parts = get_path_list(path)
        node = self

        for part in parts:
            try:
                node = node[part]
            except (KeyError, TypeError):
                return None

        try:
            return node._default_value
        except AttributeError:
            return node

    def __repr__(self):
        tmpl = '{cls}(id={id}, last_updated_at={ts}, data={data})'

        try:
            data = self._default_value
        except AttributeError:
            data = super().__repr__()

        return tmpl.format(
            cls=type(self).__name__,
            id=id(self),
            ts=self.last_updated_at,
            data=data,
        )
