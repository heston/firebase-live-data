from datetime import timedelta
import time

import pytest

from firebasedata import watcher


@pytest.fixture
def log_mock(mocker):
    return mocker.patch('firebasedata.watcher.logger')


@pytest.fixture
def timer_fake(mocker):
    return mocker.patch('firebasedata.watcher.Timer')


@pytest.fixture
def watcher_stub(mocker, timer_fake):
    is_stale = mocker.Mock()
    update = mocker.Mock()
    interval = timedelta(seconds=.001)
    return watcher.Watcher(is_stale, update, interval)


def test_Watcher_init(watcher_stub, timer_fake):
    assert watcher_stub.running is False
    assert not timer_fake.called


def test_Watcher_start(watcher_stub, timer_fake):
    watcher_stub.start()

    assert watcher_stub._should_cancel is False
    assert watcher_stub.running is True
    assert timer_fake.called
    assert timer_fake.return_value.start.called


def test_Watcher_cannot_start_while_running(watcher_stub, log_mock):
    watcher_stub.start()
    watcher_stub.start()

    log_mock.debug.assert_called_with(
        'Watcher already running: %s',
        id(watcher_stub)
    )


def test_Watcher_cancel(watcher_stub):
    watcher_stub.cancel()

    assert watcher_stub._should_cancel is True


def test_Watcher_cannot_start_after_cancel(watcher_stub, log_mock):
    watcher_stub.cancel()
    watcher_stub.start()

    log_mock.warning.assert_called_with(
        'Cannot start cancelled watcher: %s',
        id(watcher_stub)
    )


def test_Watcher_action__not_stale(mocker, watcher_stub):
    watcher_stub._should_update.return_value = False
    watcher_stub.start = mocker.Mock()
    watcher_stub._should_cancel = False
    watcher_stub._action()

    assert watcher_stub._should_update.called
    assert not watcher_stub._update_func.called
    assert watcher_stub.running is False
    assert watcher_stub.start.called


def test_Watcher_action__stale(mocker, watcher_stub):
    watcher_stub._should_update.return_value = True
    watcher_stub.start = mocker.Mock()
    watcher_stub._should_cancel = False
    watcher_stub._action()

    assert watcher_stub._should_update.called
    assert watcher_stub._update_func.called
    assert watcher_stub.running is False
    assert watcher_stub.start.called


def test_Watcher_action__should_cancel(mocker, watcher_stub):
    watcher_stub.start = mocker.Mock()
    watcher_stub._should_cancel = True
    watcher_stub._action()

    assert not watcher_stub._should_update.called
    assert not watcher_stub._update_func.called
    assert watcher_stub.running is False
    assert not watcher_stub.start.called


def test_watch__unknown_name(mocker):
    watcher_stub = mocker.patch('firebasedata.watcher.Watcher')
    is_stale = mocker.Mock()
    update = mocker.Mock()
    interval = timedelta(seconds=.001)

    # Reset watchers
    watcher.cancel_all()
    watcher.watch('test_watcher', is_stale, update, interval)

    watcher_stub.assert_called_with(is_stale, update, interval)
    assert watcher_stub.return_value.start.called
    assert 'test_watcher' in watcher._watchers


def test_watch__existing_name(mocker, log_mock):
    watcher_stub = mocker.patch('firebasedata.watcher.Watcher')
    is_stale = mocker.Mock()
    update = mocker.Mock()
    interval = timedelta(seconds=.001)

    # Reset watchers
    watcher.cancel_all()
    watcher.watch('test_watcher', is_stale, update, interval)
    watcher.watch('test_watcher', is_stale, update, interval)

    assert watcher_stub.call_count == 1
    log_mock.warning.assert_called_with(
        'Cannot start watcher. Watcher already running: %s',
        watcher_stub.return_value
    )


def test_cancel__unknown_name(mocker):
    result = watcher.cancel('whatever')

    assert result is None


def test_cancel__known_name(mocker):
    watcher_stub = mocker.Mock()
    watcher._watchers['something'] = watcher_stub
    result = watcher.cancel('something')

    assert result is True
    assert watcher_stub.cancel.called


def test_cancel__known_name__empty_value():
    watcher._watchers['something'] = None
    result = watcher.cancel('something')

    assert result is True
    assert 'something' not in watcher._watchers


def test_cancel_all(mocker):
    watcher_stub1 = mocker.Mock()
    watcher_stub2 = mocker.Mock()
    watcher._watchers['watcher1'] = watcher_stub1
    watcher._watchers['watcher2'] = watcher_stub2

    watcher.cancel_all()

    assert watcher_stub1.cancel.called
    assert watcher_stub2.cancel.called
    assert not watcher._watchers


def test_watch__not_stale(mocker):
    is_stale = mocker.Mock()
    is_stale.side_effect = [
        False,
        False,
        False,
    ]
    update = mocker.Mock()
    interval = timedelta(seconds=.001)

    watcher.watch('test_watcher', is_stale, update, interval=interval)
    time.sleep(.1)
    watcher.cancel('test_watcher')

    assert is_stale.call_count == 4
    assert update.called is False


def test_watch__stale(mocker):
    is_stale = mocker.Mock()
    is_stale.side_effect = [
        False,
        False,
        True,
    ]
    update = mocker.Mock()
    interval = timedelta(seconds=.001)

    watcher.watch('test_watcher', is_stale, update, interval=interval)
    time.sleep(.1)
    watcher.cancel('test_watcher')

    assert is_stale.call_count == 4
    assert update.called is True
