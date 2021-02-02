"""Singleton service supporting Mopeka Propane Tank Level Sensors

Many ideas were borrowed from the MIT licensed project here:
https://github.com/Home-Is-Where-You-Hang-Your-Hack/sensor.goveetemp_bt_hci
Code was written referencing that project but it is so significantly different that I am not
including that projects original copyright.


Copyright (c) 2021 Sean Brogan

SPDX-License-Identifier: MIT

"""
import logging
from enum import Enum
from typing import List, Optional, Dict

from bleson.core.hci.constants import EVT_LE_ADVERTISING_REPORT  # type: ignore
from bleson import get_provider, BDAddress

from .advertisement import MopekaAdvertisement, NoGapDataException
from .sensor import MopekaSensor

_LOGGER = logging.getLogger(__name__)
GlobalService = None

class ReadStats(object):
  """ Simple object to store different statistics related
  to service operations"""

  _ignored_ad_count: int
  _processed_ad_count: int
  _error_ad_count: int
  _zero_length_ad_count: int

  def __init__(self):
    self._ignored_ad_count = 0
    self._processed_ad_count = 0
    self._error_ad_count = 0
    self._zero_length_ad_count = 0

  def __str__(self):
    return f"ReadStats ( Ignored Ad Count: {self._ignored_ad_count}, Processed Ad Count: {self._processed_ad_count}, Error Ad Count: {self._error_ad_count}), Zero Data Ad Count: {self._zero_length_ad_count})"

class ServiceScanningMode(Enum):
  """ Enum to define different supported scanning modes for the service"""
  FILTERED_MODE = 0
  """ Scan looking for known sensors and collect their advertisements"""

  DISCOVERY_MODE = 1
  """ Scan looking for sensors with their sync button pressed"""



class MopekaService(object):
  """ Class uses ble stack to listen for advertisements and update data
  This service uses bleson which as of 0.1.8 only actually works on Linux"""

  SensorMonitoredList: Dict[BDAddress, MopekaSensor]
  """ Sensor data received while in Filtered mode per sensor """

  SensorDiscoveredList: Dict[BDAddress, MopekaSensor]
  """ New Sensors discovered while scanning in Discovery mode """

  ServiceStats: ReadStats
  """ Stats for the latest scanning session"""

  _hci_index: int
  _adapter: Optional[object]
  _started: bool
  _should_start: bool

  def __init__(self):
    """ Create a MopekaService instance

    Service is not started upon creation

    """
    self._hci_index = 0
    self._started = False
    self._should_start = False
    self._adapter = None
    self._scanning_mode = ServiceScanningMode.FILTERED_MODE

    self.SensorMonitoredList = dict()
    self.SensorDiscoveredList = dict()
    self.ServiceStats = ReadStats()

  def SetHostControllerIndex(self, index:int) -> bool:
    """ Set the host controller index to bind to.
    This can only be called prior to starting any scanning
    """

    if self._adapter is not None:
      #already started
      return False

    self._hci_index = index
    return True

  def DoSensorDiscovery(self):
    """ Setup the service to scan for all Mopeka sensors
    with the button pressed.  This is how sensors should be
    discovered.

    Note: this will stop any current scan process.
    Note: this will not start scanning
    Note: this will clear any previously discovered sensors
    Note: this will clear all statistics
    """
    self.Stop()
    self.SensorDiscoveredList.clear()
    self._scanning_mode = ServiceScanningMode.DISCOVERY_MODE
    self.ServiceStats = ReadStats()

  def AddSensorToMonitor(self, sensor: MopekaSensor) -> None:
    """ Add a sensor that should be monitored when scanning in filtered mode.
    If the sensor mac address is already listed the sensor will be replaced with
    new sensor.

    Note: Scanning will be stopped while the sensor is added
    """
    if self._scanning_mode == ServiceScanningMode.FILTERED_MODE:
      self._stop()  # stop processing so that we can safely update the shared list

    self.SensorMonitoredList[sensor._bdaddress] = sensor

    # restart scanning if it was previously scanning in filtered mode
    if self._scanning_mode == ServiceScanningMode.FILTERED_MODE and self._should_start:
      self._start()
    return

  def RemoveSensorToMonitor(self, sensor: MopekaSensor) -> None:
    """ Remove a sensor from the list to be monitored.  If the sensor isn't
    found in the list just return.

    Note: Scanning will be stopped while the sensor is removed

    """
    if sensor._bdaddress in self.SensorMonitoredList:
      if self._scanning_mode == ServiceScanningMode.FILTERED_MODE:
        self._stop()
      self.SensorMonitoredList.pop(self.SensorMonitoredList[sensor._bdaddress], None)

      if self._scanning_mode == ServiceScanningMode.FILTERED_MODE and self._should_start:
        self._start()

  def Start(self) -> None:
    """ Start scanning """
    self._should_start = True
    self._start()
    return

  def _start(self) -> None:
    """ Internal start function that doesn't change user intent"""
    if self._started:
      return

    # don't start unless there is a sensor list to filter for
    if self._scanning_mode == ServiceScanningMode.FILTERED_MODE and len(self.SensorMonitoredList) == 0:
      return

    # if adapter is none do initial setup before starting.
    if self._adapter is None:
      self._adapter = get_provider().get_adapter(self._hci_index)
      self._adapter._handle_meta_event = handle_meta_event_override

    self._adapter.start_scanning()
    self._started = True


  def Stop(self) -> None:
    """ stop scanning"""
    self._should_start = False
    self._stop()

  def _stop(self) -> None:
    """ Internal function to stop but doesn't change state for users desire"""
    if self._started:
      self._adapter.stop_scanning()
      self._started = False

  def ProcessAdvertisementPacket(self, hci_packet) -> None:
    """ Function to parse and handle HCI packet data"""

    if self._scanning_mode == ServiceScanningMode.FILTERED_MODE:
      # Filtered Mode is scanning and only processing known sensors
      packet_mac = BDAddress(hci_packet.data[3:9])
      sensor = self.SensorMonitoredList.get(packet_mac)
      if sensor is not None:
        try:
          sensor.AddReading(MopekaAdvertisement(hci_packet.data))
          self.ServiceStats._processed_ad_count += 1

        except NoGapDataException:
          # This is not an error.  Sensor sends advertisements with zero data
          # just ignore them.
          self.ServiceStats._zero_length_ad_count += 1

        except Exception as e:
          _LOGGER.error("Failed to process advertisement from defined sensor.  Exception: %s" % e)
          self.ServiceStats._ignored_ad_count += 1
      else:
        self.ServiceStats._ignored_ad_count += 1

    elif self._scanning_mode == ServiceScanningMode.DISCOVERY_MODE:
      # Discovery mode is looking for all Mopeka Sensors and reporting
      # them if their sync button is pressed
      packet_mac = BDAddress(hci_packet.data[3:9])
      sensor = self.SensorDiscoveredList.get(packet_mac)
      if sensor == None:
        # packet from untracked device
        try:
          ma = MopekaAdvertisement(hci_packet.data)
          self.ServiceStats._processed_ad_count += 1

          if(ma.SyncButtonPressed):
            # Only sensors with button pressed should be discovered
            # Recommendation by Mopeka
            sensor = MopekaSensor(packet_mac.address)
            sensor.AddReading(ma)
            self.SensorDiscoveredList[packet_mac] = sensor

        except:
          self.ServiceStats._ignored_ad_count += 1
          # Not a Mopeka Sensor or supported sensor
          pass

######################################################################################
## Global Functions
######################################################################################
def GetServiceInstance() -> MopekaService:
  """ Function to support getting the Singleton instance of the Mopeka Service"""
  global GlobalService
  if GlobalService is None:
    GlobalService = MopekaService()
  return GlobalService

def handle_meta_event_override(hci_packet) -> None:
  """ This was used in some working examples with bleson and BLE.  It looks
  like the raw data is never actually provided by the bleson implementation.
  """
  # If received BLE packet is of type ADVERTISING_REPORT
  if hci_packet.subevent_code == EVT_LE_ADVERTISING_REPORT:
    service = GetServiceInstance()
    service.ProcessAdvertisementPacket(hci_packet)





