import datetime

import blinker.base
import pytest

from firebasedata import data, live


@pytest.fixture
def livedata(mocker):
    app = mocker.Mock()
    root = '/'
    ttl = datetime.timedelta(hours=1)
    return live.LiveData(app, root, ttl)


@pytest.fixture
def logger(mocker):
    return mocker.patch('firebasedata.live.logger')


class Test_init:
    def test_no_ttl(self, mocker):
        app = mocker.Mock()
        root = '/'

        livedata = live.LiveData(app, root)

        assert livedata._app is app
        assert livedata._root_path is root
        assert livedata._db is app.database.return_value
        assert livedata._ttl is None


    def test_with_ttl(self, mocker):
        app = mocker.Mock()
        root = '/'
        ttl = datetime.timedelta(hours=1)

        livedata = live.LiveData(app, root, ttl)

        assert livedata._ttl is ttl


class Test_get_data:
    def test_cold_cache(self, livedata, mocker):
        livedata.listen = mocker.Mock()
        livedata._db.child.return_value.get.return_value.val.return_value = {}
        result = livedata.get_data()

        livedata._db.child.assert_called_with(livedata._root_path)
        assert livedata._db.child.return_value.get.called
        assert livedata._db.child.return_value.get.return_value.val.called

        assert livedata.listen.called
        assert isinstance(result, data.FirebaseData)

    def test_warm_cache(self, livedata):
        cached = object()
        livedata._cache = cached

        result = livedata.get_data()

        assert result is cached


class Test_set_data:
    def test_set_root(self, livedata):
        value = object()
        livedata.set_data('/', value)

        child_mock = livedata._db.child

        child_mock.assert_called_with(livedata._root_path)
        child_mock.return_value.set.assert_called_with(value)

    def test_set_subpath(self, livedata):
        value = object()
        livedata.set_data('/foo/bar', value)

        child_mock = livedata._db.child.return_value

        child_mock.child.assert_called_with('foo')
        child_mock.child.return_value.child.assert_called_with('bar')
        child_mock.child.return_value.child.return_value.set.assert_called_with(value)


class Test_is_stale:
    def test_missing_ttl(self, livedata):
        livedata._ttl = None

        result = livedata.is_stale()

        assert result is False

    def test_missing_data(self, livedata, mocker):
        livedata.get_data = mocker.Mock(return_value=None)

        result = livedata.is_stale()

        assert result is True

    def test_missing_data_last_updated_at(self, livedata, mocker):
        livedata.get_data = mocker.Mock(**{'return_value.last_updated_at': None})

        result = livedata.is_stale()

        assert result is True

    def test_expired_ttl(self, livedata, mocker):
        last_updated_at = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        livedata.get_data = mocker.Mock(**{
            'return_value.last_updated_at': last_updated_at
        })

        result = livedata.is_stale()

        assert result is True

    def test_valid_ttl(self, livedata, mocker):
        last_updated_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        livedata.get_data = mocker.Mock(**{
            'return_value.last_updated_at': last_updated_at
        })

        result = livedata.is_stale()

        assert result is False


class Test_signal:
    def test_signal_proxy(self, livedata, mocker):
        livedata.events = mocker.Mock()
        livedata.signal('name', doc='doc')
        livedata.events.signal.assert_called_with('name', doc='doc')

    def test_signal(self, livedata):
        signal = livedata.signal('/foo/bar')
        assert isinstance(signal, blinker.base.Signal)

    def test_same_signal(self, livedata):
        signal1 = livedata.signal('/foo/bar')
        signal2 = livedata.signal('/foo/bar')
        assert signal1 is signal2

    def test_new_signal(self, livedata):
        signal1 = livedata.signal('/foo/bar')
        signal2 = livedata.signal('/foo/bar/baz')
        assert signal1 is not signal2


class Test_listen:
    def test_setup_stream(self, livedata):
        livedata.listen()

        livedata._db.child.assert_called_with(livedata._root_path)
        livedata._db.child.return_value.stream.assert_called_with(livedata._stream_handler)

    def test_stream_is_tracked(self, livedata):
        livedata.listen()

        stream = livedata._db.child.return_value.stream.return_value
        stream_id = id(stream)

        assert stream_id in livedata._streams
        assert livedata._streams[stream_id] is stream

    def test_watcher_is_started(self, livedata, mocker):
        watch_mock = mocker.patch('firebasedata.watcher.watch')

        livedata.listen()

        watch_mock.assert_called_with(
            id(livedata),
            livedata.is_stale,
            livedata.restart,
            interval=livedata._ttl
        )

    def test_stream_gc_is_started(self, livedata, mocker):
        livedata._start_stream_gc = mocker.Mock()
        livedata.listen()

        assert livedata._start_stream_gc.called


class Test_reset:
    def test_calls_hangup(self, livedata, mocker):
        livedata.hangup = mocker.Mock()
        livedata.reset()

        livedata.hangup.assert_called_with(block=False)

    def test_resets_cache(self, livedata):
        livedata._cache = object()
        livedata.reset()

        assert livedata._cache is None


class Test_restart:
    def test_calls_reset(self, livedata, mocker):
        livedata.reset = mocker.Mock()
        livedata.restart()

        assert livedata.reset.called

    def test_resets_get_data(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.restart()

        assert livedata.get_data.called


class Test_hangup:
    def test_cancel_watcher(self, livedata, mocker):
        watcher_mock = mocker.patch('firebasedata.live.watcher')

        livedata.hangup()

        watcher_mock.cancel.assert_called_with(id(livedata))

    def test_no_streams_gc(self, livedata, mocker):
        gc_streams = mocker.Mock()
        livedata._gc_streams = gc_streams
        livedata.hangup()

        assert not gc_streams.put.called

    def test_all_streams_gc(self, livedata, mocker):
        gc_streams = mocker.Mock()
        livedata._gc_streams = gc_streams

        stream1 = object()
        stream2 = object()

        livedata._streams = {
            id(stream1): stream1,
            id(stream2): stream2,
        }
        livedata.hangup()

        gc_streams.put.assert_has_calls([
            mocker.call(stream1),
            mocker.call(stream2)
        ])

    def test_queue_joined_with_block(self, livedata, mocker):
        gc_streams = mocker.Mock()
        livedata._gc_streams = gc_streams

        livedata.hangup()

        assert gc_streams.join.called

    def test_queue_not_joined_without_block(self, livedata, mocker):
        gc_streams = mocker.Mock()
        livedata._gc_streams = gc_streams

        livedata.hangup(block=False)

        assert not gc_streams.join.called


class Test_set_path_value:
    def test_get_data(self, livedata, mocker):
        livedata.get_data = mocker.Mock()

        livedata._set_path_value('/', object())

        assert livedata.get_data.called

    def test_value_is_set_on_path(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        path = '/'
        value = object()

        livedata._set_path_value(path, value)

        livedata.get_data.return_value.set.assert_called_with(path, value)

    def test_event_is_dispatched(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata._recurse_signal = mocker.Mock()
        path = '/'
        value = object()

        livedata._set_path_value(path, value)

        livedata._recurse_signal.assert_called_with(path)


class Test_recurse_signal:
    def test_root(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.events = mocker.Mock()

        livedata._recurse_signal('/')

        livedata.get_data.return_value.get.assert_called_with()
        livedata.events.signal.assert_called_with('/')
        livedata.events.signal.return_value.send.assert_called_with(
            livedata.get_data.return_value,
            value=livedata.get_data.return_value.get.return_value
        )

    def test_child_sends_root(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.events = mocker.Mock()

        livedata._recurse_signal('/foo')

        livedata.get_data.return_value.get.assert_any_call()
        livedata.events.signal.assert_any_call('/')

    def test_child_sends_child(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.events = mocker.Mock()

        livedata._recurse_signal('/foo')

        livedata.get_data.return_value.get.assert_any_call('/foo')
        livedata.events.signal.assert_any_call('/foo')

    def test_nested_sends_parent(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.events = mocker.Mock()

        livedata._recurse_signal('/foo/bar')

        livedata.get_data.return_value.get.assert_any_call('/foo')
        livedata.events.signal.assert_any_call('/foo')

    def test_nested_sends_child(self, livedata, mocker):
        livedata.get_data = mocker.Mock()
        livedata.events = mocker.Mock()

        livedata._recurse_signal('/foo/bar')

        livedata.get_data.return_value.get.assert_any_call('/foo/bar')
        livedata.events.signal.assert_any_call('/foo/bar')


def test_put_handler(livedata, mocker):
    livedata._set_path_value = mocker.Mock()
    path = '/'
    value = object()

    livedata._put_handler(path, value)

    livedata._set_path_value.assert_called_with(path, value)


class Test_patch_handler:
    def test_absolute_paths(self, livedata, mocker):
        livedata._set_path_value = mocker.Mock()
        path1 = '/bar'
        value1 = object()
        path2 = '/baz'
        value2 = object()

        livedata._patch_handler('/foo', {
            path1: value1,
            path2: value2,
        })

        livedata._set_path_value.assert_any_call('foo/bar', value1)
        livedata._set_path_value.assert_any_call('foo/baz', value2)

    def test_relative_paths(self, livedata, mocker):
        livedata._set_path_value = mocker.Mock()
        path1 = 'bar'
        value1 = object()
        path2 = 'baz'
        value2 = object()

        livedata._patch_handler('foo', {
            path1: value1,
            path2: value2,
        })

        livedata._set_path_value.assert_any_call('foo/bar', value1)
        livedata._set_path_value.assert_any_call('foo/baz', value2)


class Test_valid_message:
    def test_missing_event(self, livedata):
        message = {
            'path': '/',
            'data': 'foo',
        }
        result = livedata._valid_message(message)
        assert result is False

    def test_missing_path(self, livedata):
        message = {
            'event': 'put',
            'data': 'foo',
        }
        result = livedata._valid_message(message)
        assert result is False

    def test_missing_data(self, livedata):
        message = {
            'event': 'put',
            'path': '/',
        }
        result = livedata._valid_message(message)
        assert result is False

    def test_invalid_event(self, livedata):
        message = {
            'event': 'get',
            'path': '/',
            'data': 'foo',
        }
        result = livedata._valid_message(message)
        assert result is False

    def test_is_valid(self, livedata):
        message = {
            'event': 'put',
            'path': '/',
            'data': 'foo',
        }
        result = livedata._valid_message(message)
        assert result is True


class Test_stream_handler:
    def test_invalid_message(self, livedata, logger):
        message = {
            'event': 'post',
            'path': '/',
            'data': 'foo',
        }
        livedata._stream_handler(message)

        assert logger.warn.called

    def test_put_handler(self, livedata, mocker):
        put_handler = mocker.Mock()
        livedata._handlers['put'] = put_handler
        message = {
            'event': 'put',
            'path': '/',
            'data': 'foo',
        }
        livedata._stream_handler(message)

        put_handler.assert_called_with(message['path'], message['data'])

    def test_patch_handler(self, livedata, mocker):
        patch_handler = mocker.Mock()
        livedata._handlers['patch'] = patch_handler
        message = {
            'event': 'patch',
            'path': '/',
            'data': [
                {
                    'path': 'foo',
                    'data': 'bar',
                },
                {
                    'path': 'baz',
                    'data': 'qux',
                }
            ]
        }
        livedata._stream_handler(message)

        patch_handler.assert_called_with(message['path'], message['data'])


class Test_stream_gc:
    def test_close_normal_stream(self, livedata, mocker, logger):
        stream = mocker.Mock()

        livedata._start_stream_gc()
        livedata._streams[id(stream)] = stream
        livedata._gc_streams.put(stream)
        livedata._gc_streams.join()

        assert stream.close.called
        logger.debug.assert_any_call('Closing stream: %s', stream)
        logger.debug.assert_any_call('Stream closed: %s', stream)

    def test_close_orphan_stream(self, livedata, mocker, logger):
        stream = mocker.Mock()

        livedata._start_stream_gc()
        livedata._gc_streams.put(stream)
        livedata._gc_streams.join()

        assert stream.close.called
        logger.debug.assert_any_call('Closing stream: %s', stream)
        logger.warning.assert_any_call('Error closing stream %s: %s', stream, mocker.ANY)
