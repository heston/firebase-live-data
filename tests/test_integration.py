import datetime

import pytest

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
