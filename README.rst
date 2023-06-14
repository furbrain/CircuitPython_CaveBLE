Introduction
============


.. image:: https://readthedocs.org/projects/circuitpython-distox/badge/?version=latest
    :target: https://circuitpython-distox.readthedocs.io/
    :alt: Documentation Status


.. image:: https://github.com/furbrain/CircuitPython_distox/workflows/Build%20CI/badge.svg
    :target: https://github.com/furbrain/CircuitPython_distox/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

DistoX Bluetooth Protocol - mimic the DistoX protocol for communicating with
paperless cave surveying tools e.g. `TopoDroid <https://github.com/marcocorvi/topodroid>`_ and
`SexyTopo <https://github.com/richsmith/sexytopo>`_


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Adafruit BLE <https://github.com/adafruit/Adafruit_CircuitPython_BLE>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.


Installing from PyPI
====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/circuitpython-distox/>`_.
To install for current user:

.. code-block:: shell

    pip3 install circuitpython-distox

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install circuitpython-distox

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install circuitpython-distox

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install distox

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Example
=============

.. code-block:: python

    import time

    import board
    import keypad
    from adafruit_ble import BLERadio
    from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
    import distox

    ble = BLERadio()
    ble.name = "DistoX"
    print(ble.name)
    disto = distox.DistoXService()
    disto_protocol = distox.SurveyProtocolService()
    advertisement = ProvideServicesAdvertisement(disto, disto_protocol)
    ble.start_advertising(advertisement)


    KEY_PINS = (board.D5, board.D9)
    keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

    compass = 0
    clino = 0
    distance = 5
    while True:
        event = keys.events.get()
        if event:
            key_number = event.key_number
            if event.pressed:
                if key_number == 0:
                    # change the values to send
                    compass = (compass + 10.5) % 360
                    clino += 5.5
                    if clino > 90:
                        clino -= 180
                    distance = (distance + 3.4) % 10000
                    print(compass, clino, distance)
                if key_number == 1:
                    disto.send_data(compass, clino, distance)
                    print("Data sent")
        message = disto.poll()
        if message:
            print(f"Message received: {message}")
        time.sleep(0.03)

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://circuitpython-distox.readthedocs.io/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/furbrain/CircuitPython_distox/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
