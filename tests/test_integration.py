import datetime
import time

import callee
import pytest
from urllib3.exceptions import HTTPError

from firebasedata import data, live


@pytest.fixture
def firebase_data():
    return data.FirebaseData({})


@pytest.fixture
def livedata(firebase_data, mocker):
    app = mocker.Mock()
    root = '/'
    ttl = datetime.timedelta(hours=1)
    live_data = live.LiveData(app, root, ttl)
    live_data._cache = firebase_data
    return live_data


def test_stream__put_data(livedata, firebase_data, mocker):
    message = {
        'path': '/foo/bar/baz',
        'data': 'hola',
        'event': 'put',
    }
    livedata._stream_handler(message)
    expected = {
        'foo': {
            'bar': {
                'baz': 'hola'
            },
        },
    }
    assert firebase_data == expected


def test_stream__patch_data(livedata, firebase_data, mocker):
    message = {
        'path': '/foo/bar',
        'data': {
            'baz/quz': 'hola',
            'qux/fub': 'luego',
        },
        'event': 'patch',
    }
    livedata._stream_handler(message)
    expected = {
        'foo': {
            'bar': {
                'baz': {
                    'quz': 'hola',
                },
                'qux': {
                    'fub': 'luego',
                },
            },
        },
    }
    assert firebase_data == expected


def test_signal_propagation__root(livedata, firebase_data, mocker):
    mock_handler = mocker.MagicMock()

    def handler(*args, **kwargs):
        mock_handler(*args, **kwargs)

    livedata.signal('/').connect(handler)
    message = {
        'path': '/foo/bar/baz',
        'data': 'hola',
        'event': 'put',
    }
    livedata._stream_handler(message)

    mock_handler.assert_called_with(
        firebase_data,
        path='/foo/bar/baz',
        value=firebase_data
    )


def test_signal_propagation__node(livedata, firebase_data, mocker):
    mock_handler = mocker.MagicMock()

    def handler(*args, **kwargs):
        mock_handler(*args, **kwargs)

    livedata.signal('/foo/bar').connect(handler)
    message = {
        'path': '/foo/bar/baz',
        'data': 'hola',
        'event': 'put',
    }
    livedata._stream_handler(message)

    mock_handler.assert_called_with(
        firebase_data,
        path='/foo/bar/baz',
        value={
            'baz': 'hola',
        }
    )


def test_signal_propagation__leaf(livedata, firebase_data, mocker):
    mock_handler = mocker.MagicMock()

    def handler(*args, **kwargs):
        mock_handler(*args, **kwargs)

    livedata.signal('/foo/bar/baz').connect(handler)
    message = {
        'path': '/foo/bar/baz',
        'data': 'hola',
        'event': 'put',
    }
    livedata._stream_handler(message)

    mock_handler.assert_called_with(
        firebase_data,
        path='/foo/bar/baz',
        value='hola'
    )


@pytest.mark.slow
def test_connection_recovery(livedata, mocker):
    watch_mock = mocker.Mock(wraps=live.watcher.watch)
    cancel_mock = mocker.Mock(wraps=live.watcher.cancel)
    live.watcher.watch = watch_mock
    live.watcher.cancel = cancel_mock
    livedata._cache = None
    livedata._ttl = datetime.timedelta(seconds=1)
    livedata._retry_interval = datetime.timedelta(seconds=2)
    livedata.is_stale = lambda: True
    livedata._db.child = mocker.Mock(side_effect=HTTPError('Test error'))

    livedata.restart()
    time.sleep(3)

    watch_mock.assert_any_call(
        'meta_{}'.format(id(livedata)),
        callee.functions.Callable(),
        livedata.get_data,
        interval=livedata._retry_interval
    )

    livedata._db.child = mocker.Mock()
    livedata.is_stale = lambda: False

    time.sleep(3)

    cancel_mock.assert_any_call(
        'meta_{}'.format(id(livedata))
    )
    assert isinstance(livedata._cache, data.FirebaseData)
