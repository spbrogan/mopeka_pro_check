"""Module that represents a Mopeka Pro Check sensor test.

Copyright (c) 2021 Sean Brogan

SPDX-License-Identifier: MIT

"""
import unittest
import logging
from mopeka_pro_check.sensor import MopekaSensor
from mopeka_pro_check.advertisement import MopekaAdvertisement


BLE_MOPEKA_MFG = bytes.fromhex(
    "01 00 01 76 3C C4 05 9D E7 12  0D  FF  59  00  03  5D  31  2C  C1  C4  3C  76  3B  F9  03  02  E5  FE  A0")

_LOGGER = logging.getLogger(__name__)


class MopekaSensorTest(unittest.TestCase):

    def test_mopeka_sensor_basic(self):
        """ Known good packet """

        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        ms = MopekaSensor(ma.mac.address)
        ms.AddReading(ma)

        self.assertIs(ms.GetReading(), ma)

    def test_mopeka_sensor_to_string(self):
        """ Make sure to string works"""
        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        ms = MopekaSensor(ma.mac.address)
        ms.AddReading(ma)

        print(ms)

    def test_mopeka_sensor_dump(self):
        """ Make sure dump routine works"""
        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        ms = MopekaSensor(ma.mac.address)
        ms.AddReading(ma)
        ms.Dump()
