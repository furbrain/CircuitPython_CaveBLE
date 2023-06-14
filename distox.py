# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Phil Underwood for Underwood Underground
#
# SPDX-License-Identifier: MIT
"""
`distox`
================================================================================

DistoX Bluetooth Protocol - mimic the DistoX protocol for communicating between
paperless cave surveying tools e.g. `TopoDroid <https://github.com/marcocorvi/topodroid>`_


* Author(s): Phil Underwood

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""
__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/furbrain/CircuitPython_distox.git"

import time
from collections import deque
from struct import pack_into

from adafruit_ble import Service
from adafruit_ble.characteristics.string import FixedStringCharacteristic
from adafruit_ble.services.nordic import UARTService

from adafruit_ble.uuid import VendorUUID

try:
    from typing import Deque, Callable, Optional, Awaitable
except ImportError:
    pass


class SurveyProtocolService(Service):
    # pylint: disable=too-few-public-methods
    """
    This service acts as a marker so cave surveying software can identify
    this as a cave surveying device, regardless of its name
    """

    uuid = VendorUUID("137c4435-8a64-4bcb-93f1-3792c6bdc965")
    protocol_characteristic = FixedStringCharacteristic(
        uuid=VendorUUID("137c4435-8a64-4bcb-93f1-3792c6bdc966"),
    )

    def __init__(self):
        super().__init__(protocol_characteristic="SAP6")


class DistoXService(UARTService):
    """
    Send data to cave surveying apps such as SexyTopo.

    **NOTE** you will need to either regularly call ``poll`` or run ``background_task``
    in the background using
    `asyncio <https://docs.circuitpython.org/projects/asyncio/en/latest/index.html>`_

    """

    ACK = 0x55
    START_CAL = 0x31
    STOP_CAL = 0x30
    START_SILENT = 0x33
    STOP_SILENT = 0x32
    READ_MEM = 0x38
    WRITE_MEM = 0x39

    def __init__(self):
        super().__init__()
        self.last_send_time: float = 0
        # pylint: disable=too-many-function-args
        self.send_queue: Deque[bytes] = deque((), 20, 1)
        self.sent_packet: bytes = b""
        self.last_enqueued_sequence = 0
        self.last_sent_sequence = 0
        self.waiting_for_ack: bool = False
        self.incomplete_packets: bytes = b""

    @staticmethod
    def _get_sequence_bit(msg: bytes):
        return (msg[0] & 0x80) == 0x80

    def send_data(self, azimuth, inclination, distance, roll=0):
        """
        Add a reading to the list to be sent

        :param float azimuth: Compass bearing in degrees
        :param float inclination: Inclination in degrees
        :param float distance: Distance in metres
        """
        packet = bytearray(8)
        # get scaled integer versions of each parameter
        i_distance = int(distance * 1000.0)
        long_bit = 1 if i_distance > 0xFFFF else 0
        i_distance %= 0x10000
        i_clino = int(inclination * 32768.0 / 180.0)
        i_compass = int(azimuth * 32768.0 / 180.0)
        i_roll = int((roll % 360) * 128.0 / 180)
        first_byte = self.last_enqueued_sequence << 7 | long_bit << 6 | 0x01
        pack_into(
            "<BHHhB", packet, 0, first_byte, i_distance, i_compass, i_clino, i_roll
        )
        self.last_enqueued_sequence ^= 0x01  # toggle
        self.send_queue.append(packet)
        self._poll_out()

    def poll(self) -> Optional[int]:
        """
        Check to see if any messages need sending or re-sending. This should be called
        every 100ms or so. It will send any data due to be sent and will resend data if no
        acknowledgement has been received. It will also return any messages received
        (one of ``START_CAL``, ``STOP_CAL``, ``START_SILENT``, ``STOP_SILENT``). Note the memory
        access commands are currently unsupported and will be ignored.

        :return: None
        """
        result = self.poll_in()
        self._poll_out()
        return result

    def _poll_out(self):
        if self.waiting_for_ack:
            # resend if last packet sent more than 5s ago
            if time.monotonic() - self.last_send_time > 5.0:
                self.write(self.sent_packet)
                self.last_send_time = time.monotonic()
        else:
            if self.send_queue:
                self.sent_packet = self.send_queue.popleft()
                self.last_sent_sequence = self._get_sequence_bit(self.sent_packet)
                self.write(self.sent_packet)
                self.waiting_for_ack = True
                self.last_send_time = time.monotonic()

    def poll_in(self) -> Optional[int]:
        """
        Check for new messages and return that info...

        :return: Any message received or None
        """

        if self.in_waiting:
            packet = self.read(self.in_waiting)
            return self._process_message_in(packet)
        if self.incomplete_packets:
            return self._process_message_in(b"")
        return None

    def _process_ack(self, sequence):
        if sequence == self.last_sent_sequence:
            self.waiting_for_ack = False

    def _process_message_in(self, packet: bytes) -> Optional[int]:
        """
        Read a message that has come in and process it
        :return: List of messages
        """
        packet = self.incomplete_packets + packet
        if packet[0] & 0x7F == self.ACK:
            sequence = self._get_sequence_bit(packet)
            self._process_ack(sequence)
            self.incomplete_packets = packet[1:]
            return None
        if packet[0] in [
            self.START_CAL,
            self.STOP_CAL,
            self.START_SILENT,
            self.STOP_SILENT,
        ]:
            self.incomplete_packets = packet[1:]
            return packet[0]
        if packet[0] == self.READ_MEM:
            if len(packet) >= 3:  # we have a full frame
                # no action taken as not supported
                self.incomplete_packets = packet[3:]
            else:
                self.incomplete_packets = packet
            return None
        if packet[0] == self.WRITE_MEM:
            if len(packet) >= 7:  # we have a full frame
                # no action taken as not supported
                self.incomplete_packets = packet[3:]
            else:
                self.incomplete_packets = packet
            return None
        # unrecognised start byte: discard
        self.incomplete_packets = packet[1:]
        return None

    async def _input_task(self, callback: Optional[Callable[[int], Awaitable]] = None):
        # pylint: disable=import-outside-toplevel
        """
        Monitor for packets in and call cb with each packet found
        :return:
        """
        import asyncio

        callback_tasks = set()
        stream = asyncio.StreamReader(self._rx)
        try:
            while True:
                data: bytes = await stream.readexactly(1)
                message = self._process_message_in(data)
                if callback:
                    task = asyncio.create_task(callback(message))
                    callback_tasks.add(task)
                    callback_tasks = {
                        x for x in callback_tasks if not x.done
                    }  # discard completed tasks
        finally:
            for x in callback_tasks:
                x.cancel()

    async def background_task(
        self, callback: Optional[Callable[[int], Awaitable]] = None
    ):
        # pylint: disable=import-outside-toplevel
        """
        You can use this as a background async task instead of doing regular polls. It
        will check for new messages and if there are any outstanding outgoing messages
        every 100ms or so.

        :param Callable callback: Function to call with any messages received
        :return: None
        """
        import asyncio

        input_task = asyncio.create_task(self._input_task(callback))
        try:
            while True:
                await asyncio.sleep(0.1)
                self._poll_out()
        finally:
            input_task.cancel()
