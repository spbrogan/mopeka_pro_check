"""Mopeka Propane Tank Level Sensor BLE Advertisement parser test

Copyright (c) 2021 Sean Brogan

SPDX-License-Identifier: MIT

"""
import unittest
import logging
import copy
from mopeka_pro_check.advertisement import MopekaAdvertisement, NoGapDataException


BLE_NOT_MOPEKA = bytes.fromhex(
    "01 00 01 3b 69 19 46 88 c0 19 02 01 02 11 09 44 56 33 33 30 30 53 2d 34 2e 30 2d 30 39 33 42 03 03 32 a0 a2")
BLE_ZERO_LEN_NO_GAP = bytes.fromhex("01 00 01 3b 69 19 46 88 c0 00 c5")
BLE_MOPEKA_MFG = bytes.fromhex(
    "01 00 01 76 3C C4 05 9D E7 12  0D  FF  59  00  03  5D  31  2C  C1  C4  3C  76  3B  F9  03  02  E5  FE  A0")

_LOGGER = logging.getLogger(__name__)


class NotMopekaAdvertisementTest(unittest.TestCase):
    """ tests for ble advertisements that don't match
        mopeka definitions
    """

    def test_mfg_packet_not_mopeka(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[10] = 4  # change size of mfg data packet
        with self.assertRaises(Exception):
            MopekaAdvertisement(b)

    def test_mfg_packet_mfgid_low_not_mopeka(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[13] = 4  # change from 0059 to 0459
        with self.assertRaises(Exception):
            MopekaAdvertisement(b)

    def test_mfg_packet_mfgid_high_not_mopeka(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[12] = 4  # change from 0059 to 0004
        with self.assertRaises(Exception):
            MopekaAdvertisement(b)

    def test_basics_ble_packet_not_mopeka(self):
        with self.assertRaises(Exception):
            MopekaAdvertisement(BLE_NOT_MOPEKA)


class ZeroLengthMopekaAdPacketTest(unittest.TestCase):
    """ tests related to packet that doesn't have mfg data and has
        no advertisement data
    """

    def test_zero_length_gap(self):
        with self.assertRaises(NoGapDataException):
            MopekaAdvertisement(BLE_ZERO_LEN_NO_GAP)


class MopekaManufacturingDataPacketTest(unittest.TestCase):

    def test_mopeka_mfg_packet(self):
        """ Known good packet """
        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        self.assertEqual(ma.BatteryPercent, 100.0)
        self.assertEqual(ma.ReadingQualityStars, 3)
        self.assertEqual(ma.rssi, -96)
        self.assertEqual(ma.BatteryVoltage, 2.90625)
        self.assertFalse(ma.SyncButtonPressed)
        self.assertEqual(ma.TemperatureInCelsius, 9)
        self.assertEqual(ma.TemperatureInFahrenheit, 48.2)
        self.assertEqual(ma.TankLevelInMM, 126)
        self.assertEqual(ma.TankLevelInInches, 4.96)

    def test_mfg_packet_hardwareid_not_mopeka(self):
        """ hardware id is not supported value """
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[14] = 4  # not HardwareId.STD_BOTTOM_UP_PROPANE
        with self.assertRaises(Exception):
            MopekaAdvertisement(b)

    def test_mopeka_mfg_packet_quality_0(self):
        """ sensor reading confidence/quality measurement of zero """
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[18] = 0  # clear
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.ReadingQualityStars, 0)

    def test_mopeka_mfg_packet_quality_1(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[18] = 0x40  # clear
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.ReadingQualityStars, 1)

    def test_mopeka_mfg_packet_quality_2(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[18] = 0x80
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.ReadingQualityStars, 2)

    def test_mopeka_mfg_packet_quality_3(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[18] = 0xC0
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.ReadingQualityStars, 3)

    def test_mopeka_mfg_packet_button_pressed(self):
        """ sensor reading button pressed"""
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[16] = b[16] | 0x80  # set bit 7
        ma = MopekaAdvertisement(b)
        self.assertTrue(ma.SyncButtonPressed)

    def test_mopeka_mfg_packet_button_not_pressed(self):
        """ sensor reading button not pressed"""
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[16] = b[16] & 0x7F  # clear bit 7
        ma = MopekaAdvertisement(b)
        self.assertFalse(ma.SyncButtonPressed)

    def test_mopeka_mfg_packet_battery_voltage_0(self):
        """ battery voltage zero"""
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[15] = b[15] & 0x80  # clear all but bit 7
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.BatteryVoltage, 0)
        self.assertEqual(ma.BatteryPercent, 0.0)

    def test_mopeka_mfg_packet_battery_voltage_max(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[15] = b[15] | 0x7F  # set to max
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.BatteryVoltage, 3.96875)
        self.assertEqual(ma.BatteryPercent, 100.0)

    def test_mopeka_mfg_packet_battery_voltage_mid(self):
        b = bytearray(BLE_MOPEKA_MFG[:])
        b[15] = (b[15] & 0x80) | 0x50  # set in to 2.5v
        ma = MopekaAdvertisement(b)
        self.assertEqual(ma.BatteryVoltage, 2.5)
        self.assertEqual(ma.BatteryPercent, 46.2)

    def test_mopeka_mfg_packet_to_string(self):
        """ Make sure to string works"""
        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        print(ma)

    def test_mopeka_mfg_packet_dump(self):
        """ Make sure dump routine works"""
        ma = MopekaAdvertisement(BLE_MOPEKA_MFG)
        ma.Dump()
