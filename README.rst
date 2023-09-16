Introduction
============

.. image:: https://readthedocs.org/projects/circuitpython-caveble/badge/?version=latest
    :target: https://circuitpython-caveble.readthedocs.io/
    :alt: Documentation Status


.. image:: https://github.com/furbrain/CircuitPython_CaveBLE/workflows/Build%20CI/badge.svg
    :target: https://github.com/furbrain/CircuitPython_CaveBLE/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

Cave Surveying Bluetooth Protocol - a protocol for communicating with
paperless cave surveying tools e.g. `TopoDroid <https://github.com/marcocorvi/topodroid>`_ and
`SexyTopo <https://github.com/richsmith/sexytopo>`_. This protocol was developed for use with
the `Shetland Attack Pony 6 <https://www.shetlandattackpony.co.uk/>`_, but is presented free to use
for anyone who wishes to use it for their cave surveying device.

Protocol
========

In the discussion below, 'instrument' means the device measuring the cave, 'surveyor' means the device
(likely a phone or tablet) receiving the data from the instrument. Description of "read" or "write" is from the
perspective of the surveyor.

This protocol uses a `SurveyProtocolService` on UUID ``137c4435-8a64-4bcb-93f1-3792c6bdc965``.
It has three characteristics:

  * Name characteristis UUID: ``137c4435-8a64-4bcb-93f1-3792c6bdc966``. This characteristic is read
    only and is a simple string indicating which protocol is being used. Currently this is hardcoded to "SAP6"
  * Leg characteristic - UUID: ``137c4435-8a64-4bcb-93f1-3792c6bdc968``. This characteristic is read only and will
    notify each time a shot is taken. It is a sequence of 17 bytes and is little-endian:

      * Byte 0: Sequence bit. This will alternate between 0 and 1 for successive legs. The surveyor
        must respond with an appropriate ACK (see later), otherwise the instrument will resend after 5
        seconds.
      * Bytes 1-4: Azimuth in degrees as a float.
      * Bytes 5-8: Inclination in degrees as a float.
      * Bytes 9-12: Roll in degrees as a float.
      * Bytes 13-16: Distance in metres as a float.

  * Command characteristic - UUID: ``137c4435-8a64-4bcb-93f1-3792c6bdc967``. Write only, surveyor
    can send a single byte to the instrument. Currently defined bytes:

      * ``0x55`` (ACK0): Signals that the surveyor has received a leg with sequence byte 0
      * ``0x56`` (ACK1): Signals that the surveyor has received a leg with sequence byte 1
      * ``0x31`` (START_CAL): Instrument should enter calibration mode
      * ``0x30`` (STOP_CAL): Instrument should leave calibration mode
      * ``0x36`` (LASER_ON): Instrument should turn the laser on
      * ``0x37`` (LASER_OFF): Instrument should turn the laser off
      * ``0x34`` (DEVICE_OFF): Instrument should turn off
      * ``0x38`` (TAKE_SHOT): Instrument should take a reading

    All the above constants are defined in both CircuitPython and Kotlin code

Usage
=====

The software in this repository simplifies use of the above protocol.

CircuitPython
-------------

The CircuitPython code manages the whole notification and responds to ACKs as per the protocol above. It keeps
a queue of legs that have not yet been sent if communication with the surveyor is interrupted and sends these once
communication has been re-established.

Initialising
............

.. code-block:: python

    from adafruit_ble import BLERadio
    from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
    import caveble

    ble = BLERadio()
    ble.name = "SAP6_AB"
    survey_protocol = caveble.SurveyProtocolService()
    advertisement = ProvideServicesAdvertisement(survey_protocol)
    ble.start_advertising(advertisement)

You will need to either call `SurveyProtocolService.poll` repeatedly, or create `SurveyProtocolService.background_task`
as an asyncio task.


Sending data using poll
.......................

.. code-block:: python

    while True:
        survey_protocol.poll()
        # if leg available to send..
            survey_protocol.send_data(azimuth, inclination, distance, roll)
        time.sleep(0.5)

Sending data asynchronously
...........................

.. code-block:: python

    asyncio.create_task(survey_protocol.background_task())
    while True:
        await leg_ready_event
        survey_protocol.send_data(azimuth, inclination, distance, roll)


Receiving commands using poll
.............................

.. code-block:: python

    while True:
        message = survey_protocol.poll()
        if message is not None:
            # do something with message
            # will not receive ACK0 or ACK1 - these are dealt with by `SurveyProtocolService`
        time.sleep(0.5)

Receiving commands asynchronously
.................................

.. code-block:: python

    async def callback(message: int):
        #process the message

    asyncio.create_task(survey_protocol.background_task(callback))
    while True:
        await leg_ready_event
        survey_protocol.send_data(azimuth, inclination, distance, roll)


Kotlin/Java (Android)
---------------------

You can use ``CaveBLE.kt`` in your code - simply change the package to something appropriate on line one. Note Kotlin
is fully compatible with Java and AndroidStudio comfortably uses these files interchangeably in the same project.

To use the device, you must create a ``CaveBLE`` object. you will need to pass in a bluetooth device object, a context,
a leg callback and an optional status callback.
The leg callback will be called whenever a new leg is received
The status callback will be called whenever the device connects or disconnects

Sample Java code
......................

.. code-block:: java

    package xxx.xxx.xxx.xxx;

    import android.bluetooth.BluetoothDevice;
    import android.content.Context;
    import xxx.xxx.xxx.CaveBLE;

    import kotlin.Unit;

    public class SAP6Communicator extends Communicator {

        private final CaveBLE caveBLE;


        public SAP6Communicator(Context context, BluetoothDevice bluetoothDevice) {
            this.caveBLE = new CaveBLE(bluetoothDevice, context, this::legCallback, this::statusCallback);
        }

        public boolean isConnected() {
            return caveBLE.isConnected();
        }

        public void requestConnect() {
            caveBLE.connect();
        }

        public void requestDisconnect() {
            caveBLE.disconnect();
        }

        public void laserOn() {
            caveBLE.laserOn()
        }

        // other commands have similar functions

        public Unit legCallback(float azimuth, float inclination, float roll, float distance) {
            // code to respond to a leg being received here.
            return Unit.INSTANCE; // you must return Unit.INSTANCE for callbacks to Kotlin code
        }

        public Unit statusCallback(int status, String msg) {
            switch (status) {
                case CaveBLE.CONNECTED:
                    // code to run when device connects here
                    break;
                case CaveBLE.DISCONNECTED:
                    Log.device("Disconnected");
                    // code to run when device disconnects here
                    break;
                case CaveBLE.CONNECTION_FAILED:
                    Log.device("Communication error: "+msg);
            }
            return Unit.INSTANCE;
        }
    }


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
PyPI <https://pypi.org/project/circuitpython-caveble/>`_.
To install for current user:

.. code-block:: shell

    pip3 install circuitpython-caveble

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install circuitpython-caveble

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install circuitpython-caveble

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install caveble

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Full Usage Example
==================

.. code-block:: python

    import time

    import board
    import keypad
    from adafruit_ble import BLERadio
    from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
    import caveble

    ble = BLERadio()
    ble.name = "SAP6_AB"
    print(ble.name)
    survey_protocol = caveble.SurveyProtocolService()
    advertisement = ProvideServicesAdvertisement(survey_protocol)
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
                    survey_protocol.send_data(compass, clino, distance)
                    print("Data sent")
        message = survey_protocol.poll()
        if message:
            print(f"Message received: {message}")
        time.sleep(0.03)

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://circuitpython-caveble.readthedocs.io/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/furbrain/CircuitPython_CaveBLE/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
