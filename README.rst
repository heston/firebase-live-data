Firebase Live Data
==================

|Build Status| |Coverage Status|

Utilities for storing, retrieving, and monitoring Firebase Realtime
Database objects in Python.

This builds on ``Pyrebase`` by providing turnkey support for database
push updates throughout the Python stack. It works by linking together
``Pyrebase`` streams with the venerable ``blinker`` package, through a
custom data structure. It allows arbitrary Python code to subscribe to
notifications whenever data in your Firebase Realtime Database changes.

Q: Can't I just use ``Pyrebase``
--------------------------------

A: Sure, but if you want to be notified in realtime when your data
changes, you'll need to set up thread-based stream handlers, and manage
their lifecycles. In addition, the format of events from Firebase can be
tricky to parse (do you know the difference between Firebase ``PUT`` and
``PATCH`` events?)

Firebase Live Data abstracts these concepts into simple ``blinker``
signals that are easy to use.

Usage
-----

.. code:: python

    import pyrebase

    from firebasedata import LiveData

    pyrebase_config = {
        # ...
    }

    app = pyrebase.initialize_app(pyrebase_config)
    live = LiveData(app, '/my_data')

    # Get a snapshot of all data at the path, `/my_data`.
    #
    # This also sets up a persistent push connection to the Firebase Realtime Database
    # at that path. Any updates under this path will trigger `blinker` events.
    #
    # `data` is a local (greedy) cache of the data at the root path (`/my_data`). It behaves
    # somewhat like a Python dictionary.
    data = live.get_data()
    all_data = data.get() #  this also works: data.get('/')
    sub_data = data.get('my/sub/path')

The push connection is established lazily, after the first call to
``get_data``.

To get notified if something changes within your LiveData connection,
just connect to the signal at that database path.

.. code:: python

    def my_handler(data):
        print(data)


    # Note that the root path (`/my_data` in this case) is omitted from the signal name.

    live.signal('/some/key').connect(my_handler)

You can also set data:

.. code:: python

    live.set_data('my/sub/path', 'my_value')

``blinker`` events will be dispatched whenever data is set, either
locally, like the example above, or via server push events.

Compatibility
-------------

Firebase Live Data is tested against Python 3.4, 3.5, and 3.6. It is not
compatible with Python 2.

Developing
----------

1. Install the development requirements (preferably into a virtualenv):

   .. code:: bash

       pip install -r requirements.txt

2. Run tests to ensure everything works:

   .. code:: bash

       py.test

.. |Build Status| image:: https://travis-ci.org/heston/firebase-live-data.svg?branch=master
   :target: https://travis-ci.org/heston/firebase-live-data
.. |Coverage Status| image:: https://coveralls.io/repos/github/heston/firebase-live-data/badge.svg?branch=master
   :target: https://coveralls.io/github/heston/firebase-live-data?branch=master
