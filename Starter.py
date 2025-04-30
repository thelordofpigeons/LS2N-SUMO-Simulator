import os, sys, winsound
import traci
import random
import traci.constants as tc
import myPyLib as PL
import xml.etree.ElementTree as ET
import glob
from datetime import datetime
from myPyLib import getHeader
from Lib.linecache import getline

import sys
import os
import glob
from os import path
import myPyLib

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

sumoBinary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"  # sumo-gui

AWT = 0  # Average Waiting time
TWT = 0  # Total Waiting Time
CO = 0
CO2 = 0
mapName = ""
AWTtrk = 0  # Average Waiting time
TWTtrk = 0  # Total Waiting Time
COtrk = 0
CO2trk = 0
distancetrk = 0
checkParking = False
frequency = 2500  # Set Frequency To 2500 Hertz
duration = 1000  # Set Duration To 1000 ms == 1 second
inPort = []  # number of trucks in the port
#Entry and Exit definition
Entry1 = "-13963"
Exit1 = "-2252"

# STATE LISTENER CLASS
class StateListener(traci.StepListener):

    def __init__(self, vehicleIds, emergencyBreakThreshold=-4.0):
        print("__init__!")
        self.vehicleIds = vehicleIds
        self.emergencyBreakThreshold = emergencyBreakThreshold
        self.vehicles = {}
        self.emergencyBreak = False
        self.collision = False
        routesRoot = ET.parse("cases\\" + mapName + "\\MyRoutes.rou.xml").getroot()
        missionRoot = ET.parse("cases\\" + mapName + "\\Missions.mis.xml").getroot()
        
    def step(self, t=0):
        self.retrieveState()
        self.printState()
        # self.checkEmergencyBreak()
        self.checkCollision()
        # indicate that the state publisher should stay active in the next step
        return True

    def retrieveState(self):
        # receive vehicle data
        for vehicleId in self.vehicleIds:
            self.vehicles[vehicleId] = traci.vehicle.getSubscriptionResults(vehicleId)

    def printState(self):
        for vehicleId in self.vehicleIds:
            vehicle = self.vehicles[vehicleId]

    def checkCollision(self):
        # if SUMO detects a collision (e.g. teleports a vehicle) set the collision flag
        if (traci.simulation.getStartingTeleportNumber() > 0):
            print("\nCollision occured...")
            self.collision = True

    def checkEmergencyBreak(self):
        # if any vehicle decelerates more than the emergencyBreakThreshold set the emergencyBreak flag
        for vehicleId in self.vehicleIds:
            vehicle = self.vehicles[vehicleId]
            if vehicle is not None:
                if vehicle[tc.VAR_ACCELERATION ] * 10 < self.emergencyBreakThreshold:
                    print("\nEmergency breaking required...")
                    self.emergencyBreak = True


def initVehicles(self):
    print(".")
    for vehicleId in self.vehicleIds:
        vehicle = self.vehicles[vehicleId]
        if vehicle is not None:  # and (traci.vehicle.getTypeID(vehID) == "TruckT"):
            print("id= %" % traci.vehicle.getTypeID(vehID))
            # traci.vehicle.changeTarget(vehicleId, "--101938#11")


# return the number of remaining adges to the current target
def getRemainingEdges(vehID):
    return(len(traci.vehicle.getRoute(vehID)) - traci.vehicle.getRouteIndex(vehID))


def initMode(mode):
        print("Initiating mode:" + mode)
        val = "1"
       
        for speedID in traci.variablespeedsign.getIDList():
            # traci.poi.highlight("Entry1")
            print(speedID + " initiated with speed=" + val)
            
        if(mode[4] == "0"):
            #traci.edge.setMaxSpeed("Entry1", "0.3")  # 0.3m/s = 1,08km/h 
            #traci.edge.setMaxSpeed("Exit1", "0.5")  # 0.5m/s = 1,8km/h 
            traci.edge.setMaxSpeed(Entry1, "0.3")  # 0.3m/s = 1,08km/h 
            traci.edge.setMaxSpeed(Exit1, "0.5")  # 0.5m/s = 1,8km/h 
            checkParking = False
            # traci.variablespeedsign.setParameter(speedID, "speed", val) 
        elif(mode[4] == "1"):
            traci.edge.setMaxSpeed(Entry1, "1")  # 1m/s = 3,6km/h 
            traci.edge.setMaxSpeed(Exit1, "1")  # 1m/s = 3,6km/h
            #traci.edge.setMaxSpeed("Entry1", "1")  # 1m/s = 3,6km/h 
            #traci.edge.setMaxSpeed("Exit1", "1")  # 1m/s = 3,6km/h
            checkParking = True
        else:
            print("ERROR Unknown MODE !!")
        print("Initiating done")        
# MAIN LAuncher  PROGRAM


def isParkWaiting(vehID, missionRoot):
    return (getRemainingEdges(vehID) <= 2 and traci.vehicle.getSpeed(vehID) == 0 and getAction(vehID, missionRoot).get("type") == 'Park')


def start(mapName, mode):
    #winsound.Beep(frequency, duration)
    sumoConfig = ["-c", "cases\\" + mapName + "\\network.sumocfg", "-S"]
    sumoCmd = [sumoBinary, sumoConfig[0], sumoConfig[1], sumoConfig[2]]
    print("Starting at " + str(datetime.now().strftime("%H:%M:%S")))
    print("routesPath=cases\\" + mapName + "\\MyRoutes.rou.xml")
    print("missionPath=cases\\" + mapName + "\\missionPath.mis.xml")
    print("mapName=" + mapName)
    print(os.path.exists("cases\\Nantes\\missions.mis.xml"))
    print(glob.glob("cases\\" + mapName + "\\*")) 
    print(os.path.exists("cases\\" + mapName + "\\MyRoutes.rou.xml"))
    print(os.path.exists("cases\\" + mapName + "\\missions.mis.xml"))
    
    routesRoot = ET.parse("cases\\" + mapName + "\\MyRoutes.rou.xml").getroot()
    missionRoot = ET.parse("cases\\" + mapName + "\\missions.mis.xml").getroot()
    metadataRoot = ET.parse("cases\\" + mapName + "\\metadata.xml").getroot()
    
    directory = mode
    parent_dir = "cases/" + mapName + "/results/"
    folderPath = os.path.join(parent_dir, directory)
    if not path.exists(folderPath):
        os.mkdir(folderPath)
    
    print("Starting the TraCI server...")
    
    traci.start(sumoCmd)
    initMode(mode)
    step = 1
    ttWaiting = 0
    nbTrucks = PL.countTrucks(missionRoot)
    print("nbTrucks=" + str(nbTrucks))

    inTrucks = []
    outTrucks = []
    begin = datetime.now()
    
    dynamicAvgSpeeds=[]
    dynamicSpeeds=[]
    
    truckReport = ""
    distancesRep = getHeader(nbTrucks, "trk") + "\n"
    speedsRep = getHeader(nbTrucks, "trk") + "\n" 
    speedFactorsRep = getHeader(nbTrucks, "trk") + "\n"
    co2sRep = getHeader(nbTrucks, "trk") + "\n" 
    noxsRep = getHeader(nbTrucks, "trk") + "\n"
    
    distances = PL.initList(nbTrucks, 0)   
    speeds = PL.initList(nbTrucks, 0)
    speedFactors = PL.initList(nbTrucks, 0)
    co2s = PL.initList(nbTrucks, 0)   
    noxs = PL.initList(nbTrucks, 0)
    

    blocked_counter = {}  # <-- NEW: dictionary to track blocked vehicles
    teleport_edges = ["-9857_0", "-9519#1_0"]  # <-- NEW: your specified teleport edges


    while True:
    
        maxCapacity = int(traci.simulation.getParameter("Parking1", "parkingArea.capacity")) + int(traci.simulation.getParameter("Parking2", "parkingArea.capacity"))
        parked = traci.parkingarea.getVehicleCount("Parking1") + traci.parkingarea.getVehicleCount("Parking2") 
        capacity = parked * 100 / int(maxCapacity)
        currentTrucks = []
        dynamicSpeeds=[]
             
        for vehID in traci.vehicle.getIDList(): 

            if ("trk" in vehID): 
                
                if traci.vehicle.getSpeed(vehID)>100:
                    print("*** alert *** "+vehID+" speed= "+( traci.vehicle.getSpeed(vehID)))
                    
                if traci.vehicle.getSpeedFactor(vehID)>2:
                    print("*** alert *** "+vehID+" speedFactor= "+( traci.vehicle.getSpeedFactor(vehID)))   
                
                index = int(vehID[3:len(vehID)])-1
                currentTrucks.append(vehID)
            
                if vehID not in inTrucks:
                    inTrucks.append(vehID)

                '''if vehID=="trk5":
                    print("traci.vehicle.getRoadID(vehID)="+str(traci.vehicle.getRoadID(vehID))+" "+str(isParkWaiting(vehID,missionRoot)))'''
                    
                if traci.vehicle.getRoadID(vehID) == "Entry1" and vehID not in inPort:
                    print(vehID + " entred the port")
                    inPort.append(vehID)
                elif traci.vehicle.getRoadID(vehID) == "Exit1" and vehID in inPort:
                    inPort.remove(vehID)
                    print(vehID + " left the port")
                
                dataa = PL.getData(vehID)
                dataa[0] = step
                dataa[1] = vehID
                dataa[2] = traci.vehicle.getWaitingTime(vehID)
                # search for the corresponding mission
                for mission in missionRoot:
                    if mission.get("id") == vehID:
                        action = getAction(vehID, missionRoot)
                        if action != None: 
                            if(action.get('status') == '0'):
                                action.set('status', '1')
                                assignMission(vehID, action)                           
                                # print(vehID+" New action. Target="+newTarget+" ("+action.get("type")+") status="+action.get("status")+" == "+str(mission[0].text))
                            elif (action.get('status') == '1'): 
                                
                                if (mode[6] == "1") and not traci.vehicle.isStopped(vehID)  and action.get('type') != 'Go':
                                    # test le isfull dans un second temps sinon erreur if 'Go'
                                    if isFull(action.get("target")):
                                        if  traci.vehicle.getSpeedFactor(vehID) > 0.5:
                                            print(vehID + ": reducing speed factor to 0.5")
                                            traci.vehicle.setSpeedFactor(vehID, 0.5)
                                    elif traci.vehicle.getSpeedFactor(vehID) < 1:
                                        print(vehID+": increasing speed factor to 1")
                                        traci.vehicle.setSpeedFactor(vehID, 1)
                                                                              
                                          
                                if action.get('type') == 'Park':
                                    
                                    if(mode[5] == "0"):  # ==Mode*0*
                                        if traci.vehicle.isStopped(vehID):  # start parking
                                            action.set('status', '2')
                                        elif isParkWaiting(vehID, missionRoot):
                                            print(vehID + " is wating parking ")
                                            alternativeAction = PL.getAlternative(metadataRoot, action.get("target"))
                                            traci.vehicle.replaceStop(vehID, 0, "")
                                            setAction(vehID, missionRoot, alternativeAction)
                                            assignMission(vehID, action) 
                                            print("New target is =" + action.get("target"))
                                            print(" ")                                              
                                    elif (mode[5] == "1"):
                                        # print("cheking parking traci.parkingarea.getVehicleCount="+str(traci.parkingarea.getVehicleCount(action.get("target"))))
                                        if traci.vehicle.isStopped(vehID):  # start parking
                                            action.set('status', '2')
                                        elif isFull(action.get("target")):
                                            alternativeAction = PL.getAlternative(metadataRoot, action.get("target"))
                                            if not isFull(alternativeAction.get("target")):
                                                traci.vehicle.replaceStop(vehID, 0, "")
                                                setAction(vehID, missionRoot, alternativeAction)
                                                assignMission(vehID, action) 
                                                print(vehID + ": Futur parking Full --> New target is =" + action.get("target"))
                                                
                                if(action.get('type') == 'Load' and traci.vehicle.isStopped(vehID)):
                                    if(vehID == "trk1"):
                                        print("start loading")
                                    action.set('status', '2')                                      
                                elif(action.get('type') == 'Unload' and traci.vehicle.isStopped(vehID)):
                                    action.set('status', '2')   
                                    if(vehID == "trk1"):
                                        print("start unloading")                                   
                                elif(action.get('type') == 'Park') and traci.vehicle.isStopped(vehID):  # going to Parking 
                                    action.set('status', '2')  
                                    if(vehID == "trk1"):
                                        print("start parking")                                    
                                elif(action.get('type') == 'Go'):
                                    action.set('status', '2')
                                    if traci.vehicle.getSpeedFactor(vehID) == 0.5:
                                        # print(vehID+": increasing speed interval to 1")
                                        traci.vehicle.setSpeedFactor(vehID, 1)
                            elif (action.get('status') == '2'):  # tester si arrive
                                if(action.get('type') == 'Load' and  not traci.vehicle.isStopped(vehID)):
                                    action.set('status', '3')
                                elif(action.get('type') == 'Unload' and  not traci.vehicle.isStopped(vehID)):
                                    action.set('status', '3')
                                elif(action.get('type') == 'Park' and not traci.vehicle.isStopped(vehID)):
                                    action.set('status', '3')
                                elif(action.get('type') == 'Go'):
                                    action.set('status', '3')
                                    
                                        # calcul des vecteurs individuels
                if(traci.vehicle.getDistance(vehID) > 0):
                    distances[index] = distances[index]+traci.vehicle.getDistance(vehID)/ 1000
                
                dynamicSpeeds.append(traci.vehicle.getSpeed(vehID) * 3.6)
                
                if(traci.vehicle.getSpeed(vehID) >= 0):
                    speeds[index] = speeds[index] +traci.vehicle.getSpeed(vehID) * 3.6
                    
                if(traci.vehicle.getSpeedFactor(vehID) >= 0):
                    speedFactors[index] = speedFactors[index] + traci.vehicle.getSpeedFactor(vehID)
                    
                if(traci.vehicle.getCO2Emission(vehID) > 0):
                    co2s[index] =  co2s[index]+ traci.vehicle.getCO2Emission(vehID) / 1000
                    
                if(traci.vehicle.getNOxEmission(vehID) > 0):
                    noxs[index] =  noxs[index]+traci.vehicle.getNOxEmission(vehID) / 1000
                
                if traci.vehicle.getSpeed(vehID)==0:
                    ttWaiting = ttWaiting + 1
            speed = traci.vehicle.getSpeed(vehID)
            # Initialize counter if needed
            if vehID not in blocked_counter:
                blocked_counter[vehID] = 0

            if speed < 0.1:
                blocked_counter[vehID] += 1
            else:
                blocked_counter[vehID] = 0

            # Teleport if stuck too long
            if blocked_counter[vehID] > 50:
                print(f"⚡ {vehID} is blocked. Attempting teleport based on route...")
                try:
                    route = traci.vehicle.getRoute(vehID)
                    route_index = traci.vehicle.getRouteIndex(vehID)

                    candidate_edges = route[route_index:route_index + 2]

                    if not candidate_edges:
                        candidate_edges = route[:2]  # fallback if near end

                    if candidate_edges:
                        chosen_edge = random.choice(candidate_edges)
                        # SUMO expects a lane ID, not just an edge -> add "_0"
                        lane_id = chosen_edge + "_0"
                        traci.vehicle.moveTo(vehID, lane_id, 10.0)  # move to 10 meters ahead on the lane
                        blocked_counter[vehID] = 0
                        print(f"{vehID} teleported to {lane_id}")
                    else:
                        print(f"⚠ {vehID} has no candidate edges for teleportation.")

                except Exception as e:
                    print(f"Error teleporting {vehID}: {e}")

        for v in inTrucks:
            if v not in currentTrucks and v not in outTrucks:
                outTrucks.append(v)
       
        if(len(currentTrucks) == 0):
            dynamicAvgSpeeds.append(0)
        else:
            dynamicAvgSpeeds.append(sum(dynamicSpeeds) / len(currentTrucks))  
        
        #print(dynamicSpeeds)
           
        interval = 60 # data per minute 
        if step % interval == 0 or step == 1:
            if truckReport == "": 
                truckReport = "step;time;inTrucks[#];Total distance[km/T.U];Average Speed[km/h/truck];parked[#];Parkings[%];Total CO2[g/T.U];Total NOx[g/T.U];TWT [T.U];inPort[#];Current Trucks[#]\n"
            truckReport = truckReport + str(step) + ";";               
            truckReport = truckReport + str(step / interval) + ";";
            truckReport = truckReport + str(len(inTrucks)) + ";";
            truckReport = truckReport + str(sum(distances)) + ";";
            
            if(len(currentTrucks) == 0):
                avgSpeed = 0
            else:
                avgSpeed = sum(dynamicAvgSpeeds) / interval  
            #print("avgSpeed="+str(avgSpeed))            
            truckReport = truckReport + str(avgSpeed) + ";";
            
            if avgSpeed>100:
                    print("*** alert *** avgSpeed = "+str(avgSpeed))
            #avgSpeed = 0;
            
            dynamicAvgSpeeds=[]
            truckReport = truckReport + str(parked) + ";";
            truckReport = truckReport + str(capacity) + ";";
            truckReport = truckReport + str(sum(co2s)) + ";";
            truckReport = truckReport + str(sum(noxs)) + ";";
            truckReport = truckReport + str(ttWaiting) + ";";
            ttWaiting = 0
            truckReport = truckReport + str(len(inPort)) + ";";
            truckReport = truckReport + str(len(currentTrucks)) + ";\n";
            
            #Write in the individual report
            for j in range(nbTrucks):
                distancesRep = distancesRep + PL.listToLine(distances,1) + "\n"
                speedsRep = speedsRep + PL.listToLine(speeds,interval) + "\n" 
                speedFactorsRep = speedFactorsRep + PL.listToLine(speedFactors,interval) + "\n" 
                co2sRep = co2sRep + PL.listToLine(co2s,1) + "\n" 
                noxsRep = noxsRep + PL.listToLine(noxs,1) + "\n"
            
            #Reset the individual data
            distances = PL.initList(nbTrucks, 0)   
            speeds = PL.initList(nbTrucks, 0)
            speedFactors = PL.initList(nbTrucks, 0)
            co2s = PL.initList(nbTrucks, 0)   
            noxs = PL.initList(nbTrucks, 0)
            
        #if len(outTrucks) == nbTrucks or step == 0:  # nbTrucks
            #print("break! " + str(nbTrucks))
            #break
        if nbTrucks > 0 and len(outTrucks) == nbTrucks:
            print("All trucks exited. Ending simulation.")
            break    
        traci.simulationStep()
        step += 1   
    # PL.save(xxx)
    print()
    end = datetime.now()
    print("Simulation started at " + str(begin.strftime("%H:%M:%S")) + " ended at " + end.strftime("%H:%M:%S"))
    print('Saving results files')
    
    f = open(folderPath + "/"+mode+"_Truck Report.csv", "w")
    f.write("Simulation started at " + str(begin.strftime("%H:%M:%S")) + " ended at " + end.strftime("%H:%M:%S") + "\n" + truckReport)
    f.close()
    
    f = open(folderPath + "/"+mode+"_DistancesRep.csv", "w")
    f.write(distancesRep)
    f.close()
    f = open(folderPath+"/"+mode+"_SpeedsRep.csv", "w")
    f.write(speedsRep)
    f.close()
    f = open(folderPath+"/"+mode+"_SpeedFactorsRep.csv", "w")
    f.write(speedFactorsRep)
    f.close()
    f = open(folderPath+"/"+mode+"_co2sRep.csv", "w")
    f.write(co2sRep)
    f.close()
    f = open(folderPath+"/"+mode+" _noxsRep.csv", "w")
    f.write(noxsRep)
    f.close()
            
    '''print("Grouping CSV files")
    extension = 'csv'
    all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
    writer = pd.ExcelWriter('IndividualData.xlsx') # Arbitrary output name
    for csvfilename in all_filenames:
        txt = Path(csvfilename).read_text()
        txt = txt.replace(',', '.')
        text_file = open(csvfilename, "w")
        text_file.write(txt)
        text_file.close()
        print("Loading "+ csvfilename)
        df= pd.read_csv(csvfilename,sep=';', encoding='utf-8')
        df.to_excel(writer,sheet_name=os.folderPath.splitext(csvfilename)[0])
        print("done")
    writer.save()
    print("task completed")'''
    
    print("\nStopping the TraCI server...")
    traci.close()
    sys.exit()

def isFull(target):
    free = int(traci.simulation.getParameter(target, "parkingArea.capacity"))
    free = free - traci.parkingarea.getVehicleCount(target)
    if (free == 0):
        return True
    else:
        return False  

def assignMission(vehID, action):
    newTarget = action.get("target")
    newEdge = action.get("edge")
    '''if(vehID=="trk2"):
        print('')'''
    '''if(newTarget!=None):
        print("assining new target="+newTarget)'''
    # traci.vehicle.changeTarget(vehID,newTarget)
    print(str(vehID) + " assignMission " + str(action.get("type")) + " target=" + str(newTarget))
    
    if(action.get("type") == "Load" or action.get("type") == "Unload"):
        traci.vehicle.changeTarget(vehID, newEdge)
        traci.vehicle.setParkingAreaStop(vehID, newTarget, 180)
            
    if(action.get("type") == "Park"):
        traci.vehicle.changeTarget(vehID, newEdge)
        if(vehID == "trk18"):
            print("trk18: new edge= " + newEdge + " newTarget=" + newTarget)
        traci.vehicle.setParkingAreaStop(vehID, newTarget, 600)
        
    if(action.get("type") == "Go"):
        traci.vehicle.changeTarget(vehID, newEdge)
        
    action.set("status", "1")
              
def getAction(vehID, missionRoot):
    for mission in missionRoot:
        if vehID == mission.get("id"):
            for action in mission:
                if action.get("status") != "3":
                    return action

def setAction(vehID, missionRoot, newAction):
    for mission in missionRoot:
        if vehID == mission.get("id"):
            for action in mission:
                if action.get("status") != "3":
                    action.set('target', newAction.get('target'))
                    action.set('edge', newAction.get('edge'))
                    action.set('status', '0')
                    print("setAction replaced")
                    return

def newAction(type, target, edge):
    action = ET.Element("action")
    action.set("type", type)
    action.set("target", target)
    action.set("edge", edge)
    action.set("status", "0")
    return action     

def getTarget(vehID, missionRoot):
    for mission in missionRoot:
        if vehID == mission.get("id"):
            for action in mission:
                # print(vehID+" action [getTarget]-> "+action.get("status"))
                if action.get("status") == "1":
                    # print("current action with status == 1 has taget="+action.get("target"))
                    return action.get("target")
                
                
if __name__ == "__main__":
    mapName = "Nantes"   # <-- Your correct map!
    mode = "Mode111"     # <-- Your mode (can stay Mode111)
    start(mapName, mode)
