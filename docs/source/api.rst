API Reference
=============

High-level Python API for controlling Quectel cellular modems.

This API is centered around :class:`quectelpy.QuectelModem` and its feature
managers:

- ``modem.device`` – Device information & SIM state
- ``modem.network`` – Network registration, signal, operator
- ``modem.sms`` – SMS sending, reading, listing

----

QuectelModem
------------

.. autoclass:: quectelpy.QuectelModem
    :members:
    :undoc-members:
    :show-inheritance:

----

Device Operations
-----------------

.. automodule:: quectelpy.features.device_info
    :members:
    :undoc-members:
    :show-inheritance:

----

Network Operations
------------------

.. automodule:: quectelpy.features.network
    :members:
    :undoc-members:
    :show-inheritance:

----

SMS Operations
--------------

.. automodule:: quectelpy.features.sms
    :members:
    :undoc-members:
    :show-inheritance:

----

Types
-----

.. automodule:: quectelpy.types
    :members:
    :undoc-members:
    :show-inheritance:
    :noindex:

----

Exceptions
----------

.. automodule:: quectelpy.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

