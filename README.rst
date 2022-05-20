Firebase Live Data
==================

|PyPI version| |Build Status| |Coverage Status|

Utilities for storing, retrieving, and monitoring Firebase Realtime
Database objects in Python.

This builds on ``Pyrebase`` by providing turnkey support for database
push updates throughout the Python stack. It works by linking together
``Pyrebase`` streams with the venerable ``blinker`` package, through a
custom data structure. It allows arbitrary Python code to subscribe to
notifications whenever data in your Firebase Realtime Database changes.

Q: Can’t I just use ``Pyrebase``
--------------------------------

A: Sure, but if you want to be notified in realtime when your data
changes, you’ll need to set up thread-based stream handlers, and manage
their lifecycles. In addition, the format of events from Firebase can be
tricky to parse (do you know the difference between Firebase ``PUT`` and
``PATCH`` events?)

Firebase Live Data abstracts these concepts into simple ``blinker``
signals that are easy to use.

Installing
----------

.. code:: bash

   pip install FirebaseData -e git+https://github.com/heston/Pyrebase.git@a77bd6f6def656b1dcd77d938fac2707f3c4ba61#egg=Pyrebase

Dependencies
------------

Firebase Live Data has a direct dependency on
`Blinker <https://pypi.python.org/pypi/blinker>`__, and a peer
dependency on `Pyrebase <https://pypi.python.org/pypi/Pyrebase>`__ (see
note below). This means that Blinker will be installed automatically,
while Pyrebase must be installed separately (hence its inclusion in the
``pip`` command above). This is because Pyrebase requires `additional
configuration <https://github.com/thisbejim/Pyrebase#add-pyrebase-to-your-application>`__
that is outside the scope of this document.

**A note on Pyrebase maintenance**: It seems that Pyrebase is no longer
being actively maintained, unfortunately. Please use `this author’s
fork <https://github.com/heston/Pyrebase/tree/upgrade-google-auth>`__ to
get things working:

::

   pip install -e git+https://github.com/heston/Pyrebase.git@a77bd6f6def656b1dcd77d938fac2707f3c4ba61#egg=Pyrebase

Compatibility
-------------

Firebase Live Data is tested against Python 3.7, 3.8, 3.9 and 3.10. It
is not compatible with Python 2.

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

   def my_handler(sender, value=None):
       print(value)


   # Note that the root path (`/my_data` in this case) is omitted from the signal name.

   live.signal('/some/key').connect(my_handler)

``my_handler`` will be invoked with ``sender`` set to the
``FirebaseData`` instance, and the ``value`` keyword argument set to the
value of the key that changed.

You can also set data:

.. code:: python

   live.set_data('my/sub/path', 'my_value')

``blinker`` events will be dispatched whenever data is set, either
locally, like the example above, or via server push events.

Developing
----------

1. Install the development requirements (preferably into a virtualenv):

   .. code:: bash

      python3 -m venv venv
      source venv/bin/activate
      pip install -r requirements.txt

2. Run tests to ensure everything works:

   .. code:: bash

      pytest

.. |PyPI version| image:: https://badge.fury.io/py/FirebaseData.svg
   :target: https://badge.fury.io/py/FirebaseData
.. |Build Status| image:: https://github.com/heston/firebase-live-data/actions/workflows/pytest.yml/badge.svg?branch=master
   :target: https://github.com/heston/firebase-live-data/actions/workflows/pytest.yml?query=branch%3Amaster
.. |Coverage Status| image:: https://coveralls.io/repos/github/heston/firebase-live-data/badge.svg?branch=master
   :target: https://coveralls.io/github/heston/firebase-live-data?branch=master
