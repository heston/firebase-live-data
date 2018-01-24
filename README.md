# Firebase Live Data

Utilities for storing, retrieving, and monitoring Firebase Realtime Database objects in
Python.

This builds on `Pyrebase` by providing turnkey support for database push updates
throughout the Python stack. It works by linking together `Pyrebase` streams with the
venerable `blinker` package, through a custom data structure. It allows arbitrary Python
code to subscribe to notifications whenever data in your Firebase Realtime Database
changes.

## Q: Can't I just use `Pyrebase`

A: Sure, but if you want to be notified in realtime when your data changes, you'll need to
set up thread-based stream handlers, and manage their lifecycles. In addition, the format
of events from Firebase can be tricky to parse (do you know the difference between
Firebase `PUT` and `PATCH` events?)

Firebase Live Data abstracts these concepts into simple `blinker` signals that are easy to use.


## Usage

```python
import pyrebase

from firebasedata import LiveData

pyrebase_config = {
    # ...
}

app = pyrebase.initialize_app(pyrebase_config)
connection = LiveData(app, 'my_db_path', event_prefix='fb')

# Get a snapshot of all data at the path, `my_db_path`.
#
# This also sets up a persistent push connection to the Firebase Realtime Database
# at that path. Any updates under this path will trigger `blinker` events.
#
# This behaves somewhat like a normal Python dictionary.
data = connection.get_data()
```

To get notified if something changes within your Live Data connection, just connect
to the database path using `blinker`.

```python
import blinker


def my_handler(data):
    print(data)


# The signal name is the prefix (if specified), followed by a colon, and then the
# dot-separated path to the data. If no prefix is specified, the colon is omitted.
signal_name = 'fb:my_db_path.some.key'
blinker.signal(signal_name).connect(my_handler)
```
