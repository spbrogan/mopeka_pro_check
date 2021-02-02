from mopeka_pro_check.service import MopekaService, MopekaSensor, GetServiceInstance
from time import sleep

service = GetServiceInstance()
service.SetHostControllerIndex(0)
service.AddSensorToMonitor(MopekaSensor("e7:9d:05:c4:3c:76"))
service.Start()
sleep(15)
service.Stop()

print("Stats %s" % str(service.ServiceStats))

for s in service.SensorMonitoredList.values():
  s.Dump()

print("Do Discovery")
service.DoSensorDiscovery()
service.Start()
sleep(5)
service.Stop()

print(f"\n\nFinished Discovery.  Found {len(service.SensorDiscoveredList)} new sensors")
print("Stats %s" % str(service.ServiceStats))
for s in service.SensorDiscoveredList.values():
  s.Dump()



