import datetime

import pytest

from firebasedata import data, live


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


@pytest.fixture
def livedata(mocker):
    app = mocker.Mock()
    root = '/'
    ttl = datetime.timedelta(hours=1)
    return live.LiveData(app, root, ttl)


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
