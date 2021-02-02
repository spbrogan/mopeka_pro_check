"""Mopeka Propane Tank Level Sensor BLE Advertisement parser

Copyright (c) 2021 Sean Brogan

SPDX-License-Identifier: MIT

"""
from enum import Enum
import logging
from typing import Optional

from bleson import BDAddress
from bleson.core.hci.type_converters import rssi_from_byte
from bleson.core.hci.constants import GAP_MFG_DATA, GAP_NAME_COMPLETE

# converting sensor value to height - contact Mopeka for other fluids/gases
MOPEKA_TANK_LEVEL_COEFFICIENTS_PROPANE = (0.573045, -0.002822, -0.00000535)

MOPEKA_MANUFACTURE_ID = 0x0059

_LOGGER = logging.getLogger(__name__)

class NoGapDataException(Exception):
    """ Special subclass to gracefully handle zero length GAP
    caller should catch these exception types specifically
    """
    pass


class HardwareId(Enum):
    """ definition of the known Mopeka hardware ids."""
    STD_BOTTOM_UP_PROPANE = 0x3
    TOP_DOWN_AIR_SPACE = 0x4
    BOTTOM_UP_WATER = 0x5


class MopekaAdvertisement(object):
    """ BLE GAP/Advertisement parser.
    Will parse a single packet with multiple GAP reports.

    Designed to only parse Mopeka sensor GAP reports

    Exceptions will be raised in the init function if the packet
    is not formated as expected and/or not complete.
    """

    rssi: int
    name: Optional[str]
    mac: BDAddress

    # Private Members
    _raw_mfg_data: bytes

    def __init__(self, data: bytes):
        """ init from ble advertising data

        preamble: 3
        Access Address: 6
        GAP Packet: N
        GAP Packet[1]: N
        GAP_Packet[2]: N

        GAP Packet:
            length: 1 (length of packet not including the length byte)
            type: 1
            Payload: N
        """

        self.rssi = rssi_from_byte(data[-1])
        self.mac = BDAddress(data[3:9])
        self.name = None
        self._raw_mfg_data = None

        gap_data = data[10:-1]  # trim the data to just the ad data
        offset = 0
        # parse the GAP reports in a loop
        while offset < len(gap_data):
            length = gap_data[offset]
            # process gap data starting with type byte (first byte after size)
            self._process_gap(gap_data[offset + 1 : offset + 1 + length])
            offset += 1 + length

        if len(gap_data) < 1:
            # catch packets that have no GAP data as
            # the mopeka sensor does send these and they
            # should not be considered an error.
            raise NoGapDataException("No GAP data")

        if self._raw_mfg_data is None:
            # Make sure we found the required MFG_DATA for Mopeka Sensor
            raise Exception("Incomplete Sensor Data")

    def _process_gap(self, data: bytes) -> None:
        """ Process supported BLE GAP reports.

        data should be buffer starting with type and have length matching
        the report length.
        """

        if data[0] == GAP_MFG_DATA:
            self._process_gap_mfg_data(data)

        elif data[0] == GAP_NAME_COMPLETE:
            self._process_gap_name_complete(data)

        else:
            _LOGGER.debug(
                "Unsupported GAP report type 0x%X on sensor %s"
                % (data[0], str(self.mac))
            )

    def _process_gap_name_complete(self, data:bytes) -> None:
        """ process GAP data of type GAP_NAME_COMPLETE """
        self.name = data[1:].decode("ascii")

    def _process_gap_mfg_data(self, data:bytes) ->None:
        """ process GAP data of type GAP_MFG_DATA

        data should be buffer in format defined by Mopeka
        """

        MfgDataLength = len(data)
        if MfgDataLength != 13:
            raise Exception(f"Unsupported Data Length (0x{MfgDataLength:X})")

        self.ManufacturerId = data[1] + (data[2] << 8)
        if self.ManufacturerId != MOPEKA_MANUFACTURE_ID:
            raise Exception(
                f"Advertising Data has Unsupported Manufacturer ID 0x{self.ManufacturerId}"
            )

        self.HardwareId = HardwareId(data[3])
        if self.HardwareId != HardwareId.STD_BOTTOM_UP_PROPANE:
            raise Exception(
                f"Advertising Data has Unsupported Hardware ID {self.HardwareId}"
            )

        self._raw_battery = data[4] & 0x7F

        self.SyncButtonPressed = bool(data[5] & 0x80 > 0)
        """ True if Sync Button is currently pressed """

        self._raw_temp = data[5] & 0x7F
        self._raw_tank_level = ((int(data[7]) << 8) + data[6]) & 0x3FFF

        self.ReadingQualityStars = data[7] >> 6
        """ Confidence or Quality of the reading on a scale of 0-3.  Higher is more confident """

        self._raw_x_accel = data[11]
        self._raw_y_accel = data[12]

        # Set raw data for debug late.  Do it last as it can also be used
        # as successful parsing indicator
        self._raw_mfg_data = data


    @property
    def BatteryVoltage(self) -> float:
        """Battery reading in volts"""
        return self._raw_battery / 32.0

    @property
    def BatteryPercent(self) -> float:
        """Battery Percentage based on 3 volt CR2032 battery"""
        percent = ((self.BatteryVoltage - 2.2) / 0.65) * 100
        if percent > 100.0:
            return 100.0
        if percent < 0.0:
            return 0.0
        return round(percent, 1)

    @property
    def TemperatureInCelsius(self) -> int:
        """Temperature in Celsius

        Note: This temperature has not been characterized against ambient temperature
        """
        return self._raw_temp - 40

    @property
    def TemperatureInFahrenheit(self) -> float:
        """Temperature in Fahrenheit

        Note: This temperature has not been characterized against ambient temperature
        """
        return ((self.TemperatureInCelsius * 9) / 5) + 32

    @property
    def TankLevelInMM(self) -> int:
        """ The tank level/depth in mm for propane gas"""
        return int(
            self._raw_tank_level
            * (
                MOPEKA_TANK_LEVEL_COEFFICIENTS_PROPANE[0]
                + (MOPEKA_TANK_LEVEL_COEFFICIENTS_PROPANE[1] * self._raw_temp)
                + (
                    MOPEKA_TANK_LEVEL_COEFFICIENTS_PROPANE[2]
                    * self._raw_temp
                    * self._raw_temp
                )
            )
        )

    @property
    def TankLevelInInches(self) -> float:
        """ The tank level/depth in inches"""
        return round(self.TankLevelInMM / 25.4, 2)

    def __str__(self) -> str:
        return ("MopekaAdvertisement -  " +
                f"RSSI: {self.rssi}dBm  " +
                f"Battery: {self.BatteryVoltage} volts {self.BatteryPercent}%  " +
                f"Button Pressed: {self.SyncButtonPressed}  " +
                f"Temperature {self.TemperatureInCelsius}C {self.TemperatureInFahrenheit}F  " +
                f"Confidence Stars {self.ReadingQualityStars}  " +
                f"Fluid Height {self.TankLevelInMM} mm")

    def Dump(self):
        """ Helper routine that prints ad data plus all mfg data"""
        print(self)
        print("MfgData: ", end="")
        for a in self._raw_mfg_data:
            print("0x%02X" % a, end="  ")
        print("\n")
