import traci
import pytz
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import gzip


# Define lane status dictionary
laneStatus = {}
numVehicles = {}

# Dictionary to store vehicle entry times
vehicle_entry_times = {}


def getdatetime():
    utc_now = pytz.utc.localize(datetime.datetime.utcnow())
    currentDT = utc_now.astimezone(pytz.timezone("US/Eastern"))
    DATIME = currentDT.strftime("%Y-%m-%d %H:%M:%S")
    return DATIME


def flatten_list(_2d_list):
    flat_list = []
    for element in _2d_list:
        if isinstance(element, list):
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list


def update_network_file(network_file_path, blocked_lane_ids):
    # Decompress the network file
    with gzip.open(network_file_path, 'rb') as f:
        decompressed_content = f.read().decode('utf-8')

    # Load the network file as XML
    tree = ET.ElementTree(ET.fromstring(decompressed_content))
    root = tree.getroot()

    # Iterate over the edges and lanes
    for edge in root.findall('edge'):
        for lane in edge.findall('lane'):
            lane_id = lane.get('id')
            if lane_id in blocked_lane_ids:
                # Update the 'disallow' attribute of the lane to block all vehicles
                lane.set('disallow', 'all')

    # Save the updated network file
    updated_network_file_path = "updated_net.xml.gz"
    with gzip.open(updated_network_file_path, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    return updated_network_file_path


sumoCmd = ["sumo", "-c", "osm.sumocfg"]
traci.start(sumoCmd)

total_time = 0
vehicle_count = 0
packVehicleData = []
packBigData = []

# Initialize lane status dictionary
for laneID in traci.lane.getIDList():
    laneStatus[laneID] = 0
    numVehicles[laneID] = 0

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    # For each vehicle currently in the network
    for vehid in traci.vehicle.getIDList():
        if vehid not in vehicle_entry_times:
            vehicle_entry_times[vehid] = traci.simulation.getTime()  # store entry time

    vehicles = traci.vehicle.getIDList()

    for i in range(len(vehicles)):
        # Collect vehicle information
        vehid = vehicles[i]
        x, y = traci.vehicle.getPosition(vehicles[i])
        coord = [x, y]
        lon, lat = traci.simulation.convertGeo(x, y)
        gpscoord = [lon, lat]
        spd = round(traci.vehicle.getSpeed(vehicles[i]) * 3.6, 2)
        edge = traci.vehicle.getRoadID(vehicles[i])
        lane = traci.vehicle.getLaneID(vehicles[i])

        # Update numVehicles dictionary
        numVehicles[lane] += 1

        # Update lane status
        status = numVehicles[lane] // 1000
        laneStatus[lane] = min(status, 4)

        # Pack vehicle data
        vehList = [getdatetime(), vehid, coord, gpscoord, spd, edge, lane, laneStatus[lane], numVehicles[lane]]

        print("Vehicle:", vehicles[i], "at datetime:", getdatetime())
        print(vehicles[i], ">>> Position:", coord, "| GPS Position:", gpscoord, "| Speed:", spd, "km/h |",
              "Edge ID of veh:", edge, "| Lane ID of veh:", lane, "| Lane status:", laneStatus[lane],
              "| Num vehicles in lane:", numVehicles[lane])

    # Pack simulated data
    packBigDataLine = flatten_list([vehList])
    packBigData.append(packBigDataLine)

    # For each vehicle that left the network
    for vehid in list(vehicle_entry_times.keys()):
        if vehid not in traci.vehicle.getIDList():
            total_time += traci.simulation.getTime() - vehicle_entry_times[vehid]
            vehicle_count += 1
            del vehicle_entry_times[vehid]

traci.close()

# Calculate average time spent in the network
avg_time_in_network = total_time / vehicle_count if vehicle_count > 0 else 0
# Generate csv file
columnnames = ['dateandtime', 'vehid', 'coord', 'gpscoord', 'spd', 'edge', 'lane', 'lane_status', 'num_vehicles']
dataset = pd.DataFrame(packBigData, index=None, columns=columnnames)
# Add the average time column to the DataFrame
dataset['avg_time_in_network'] = avg_time_in_network
dataset.to_csv("output1.csv", index=False)

# Identify the blocked lanes with status = 4
blocked_lane_ids = [lane_id for lane_id, status in laneStatus.items() if status == 4]

# Update the network file for the second simulation
updated_network_file_path = update_network_file("osm.net.xml.gz", blocked_lane_ids)

# Update the configuration file for the second simulation
updated_config_file_path = "updated_osm.sumocfg"
with open("osm.sumocfg", 'r') as f:
    config_content = f.read()
    updated_config_content = config_content.replace("osm.net.xml.gz", updated_network_file_path)
    with open(updated_config_file_path, 'w') as updated_config_file:
        updated_config_file.write(updated_config_content)

# Run the second simulation using the updated network file and configuration file
sumoCmd = ["sumo", "-c", updated_config_file_path]
traci.start(sumoCmd)

packBigData = []
laneStatus = {}
numVehicles = {}

# Repeat the same process for the second simulation
total_time = 0
vehicle_count = 0
vehicle_entry_times = {}

# Initialize lane status dictionary for the second simulation
for laneID in traci.lane.getIDList():
    laneStatus[laneID] = 0
    numVehicles[laneID] = 0

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    # For each vehicle currently in the network
    for vehid in traci.vehicle.getIDList():
        if vehid not in vehicle_entry_times:
            vehicle_entry_times[vehid] = traci.simulation.getTime()  # store entry time

    vehicles = traci.vehicle.getIDList()

    for i in range(len(vehicles)):
        # Collect vehicle information
        vehid = vehicles[i]
        x, y = traci.vehicle.getPosition(vehicles[i])
        coord = [x, y]
        lon, lat = traci.simulation.convertGeo(x, y)
        gpscoord = [lon, lat]
        spd = round(traci.vehicle.getSpeed(vehicles[i]) * 3.6, 2)
        edge = traci.vehicle.getRoadID(vehicles[i])
        lane = traci.vehicle.getLaneID(vehicles[i])

        # Update numVehicles dictionary
        numVehicles[lane] += 1

        # Update lane status
        status = numVehicles[lane] // 10000
        laneStatus[lane] = min(status, 4)

        # Pack vehicle data
        vehList = [getdatetime(), vehid, coord, gpscoord, spd, edge, lane, laneStatus[lane], numVehicles[lane]]

        print("Vehicle:", vehicles[i], "at datetime:", getdatetime())
        print(vehicles[i], ">>> Position:", coord, "| GPS Position:", gpscoord, "| Speed:", spd, "km/h |",
              "Edge ID of veh:", edge, "| Lane ID of veh:", lane, "| Lane status:", laneStatus[lane],
              "| Num vehicles in lane:", numVehicles[lane])

    # Pack simulated data
    packBigDataLine = flatten_list([vehList])
    packBigData.append(packBigDataLine)

    # For each vehicle that left the network
    for vehid in list(vehicle_entry_times.keys()):
        if vehid not in traci.vehicle.getIDList():
            total_time += traci.simulation.getTime() - vehicle_entry_times[vehid]
            vehicle_count += 1
            del vehicle_entry_times[vehid]

traci.close()

# Calculate average time spent in the network
avg_time_in_network = total_time / vehicle_count if vehicle_count > 0 else 0
# Generate csv file
dataset = pd.DataFrame(packBigData, index=None, columns=columnnames)
# Add the average time column to the DataFrame
dataset['avg_time_in_network'] = avg_time_in_network
dataset.to_csv("output2.csv", index=False)
