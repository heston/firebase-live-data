import datetime

from firebasedata import data as firebase_data


class Test_get_path_list:
    def test_no_path(self):
        result = firebase_data.get_path_list('')
        assert result == []

    def test_root_path(self):
        result = firebase_data.get_path_list('/')
        assert result == []

    def test_absolute_child_path(self):
        result = firebase_data.get_path_list('/foo/bar')
        assert result == ['foo', 'bar']

    def test_relative_child_path(self):
        result = firebase_data.get_path_list('foo/bar')
        assert result == ['foo', 'bar']


class TestFirebaseData_set:
    def test_set_root(self):
        data = firebase_data.FirebaseData()
        data.set('/', {'foo': 1})
        assert data == {'foo': 1}

    def test_set_missing_child(self):
        data = firebase_data.FirebaseData()
        data.set('/foo/bar', 1)
        assert data == {'foo': {'bar': 1}}

    def test_set_existing_child(self):
        data = firebase_data.FirebaseData({'foo': {'bar': 1}})
        data.set('/foo/bar', 2)
        assert data == {'foo': {'bar': 2}}

    def test_set_missing_then_set_existing(self):
        data = firebase_data.FirebaseData()
        data.set('/foo', {'bar': 1})
        data.set('/foo/bar', 2)
        assert data == {'foo': {'bar': 2}}

    def test_set_different_type(self):
        data = firebase_data.FirebaseData({'foo': 1})
        data.set('/foo/bar', 2)
        assert data == {'foo': {'bar': 2}}

    def test_set_missing_then_set_different_type(self):
        data = firebase_data.FirebaseData()
        data.set('/foo', 1)
        data.set('/foo/bar', 2)
        assert data == {'foo': {'bar': 2}}

    def test_set_different_type_then_set_missing(self):
        data = firebase_data.FirebaseData({'foo': 1})
        data.set('/foo/bar', 2)
        data.set('/foo/bar/baz', {'qux': 1})
        assert data == {'foo': {'bar': {'baz': {'qux': 1}}}}

    def test_unset_root(self):
        data = firebase_data.FirebaseData({'foo': {'bar': 1}})
        data.set('/', None)
        assert data == {}

    def test_unset_child(self):
        data = firebase_data.FirebaseData({'foo': {'bar': 1}})
        data.set('/foo/bar', None)
        assert data == {'foo': {}}

    def test_unset_missing_child(self):
        data = firebase_data.FirebaseData({'foo': {'bar': 1}})
        data.set('/foo/bar/baz', None)
        assert data == {'foo': {'bar': {}}}


class TestFirebaseData_get:
    def test_get_root(self):
        data = firebase_data.FirebaseData()
        result = data.get('/')
        assert result == {}

    def test_get_missing_key(self):
        data = firebase_data.FirebaseData()
        result = data.get('/foo/bar')
        assert result == None

    def test_get_different_type_key(self):
        data = firebase_data.FirebaseData({'foo': 1})
        result = data.get('/foo/bar')
        assert result == None

    def test_existing_key(self):
        data = firebase_data.FirebaseData({'foo': {'bar': 1}})
        result = data.get('/foo/bar')
        assert result == 1


class TestFirebaseData_staleness:
    def test_last_updated_at__set_on_init(self):
        data = firebase_data.FirebaseData()

        assert isinstance(data.last_updated_at, datetime.datetime)

    def test_last_updated_at__updated_after_update(self):
        data = firebase_data.FirebaseData()
        old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        data.last_updated_at = old_time

        data.set('foo', 'bar')
        assert data.last_updated_at > old_time


def test_FirebaseData_repr():
    data = firebase_data.FirebaseData(a=1)
    data_id = id(data)
    data.last_updated_at = datetime.datetime(
        year=2017, month=9, day=2, hour=20, minute=2, second=59
    )
    result = str(data)
    assert result == (
        'FirebaseData('
            'id={}, '
            'last_updated_at=2017-09-02 20:02:59, '
            'data={{\'a\': 1}}'
        ')'.format(data_id)
    )

