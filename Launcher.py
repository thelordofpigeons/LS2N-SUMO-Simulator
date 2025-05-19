import os, sys
import sumolib ,traci
import random
import traci.constants as tc
import myPyLib
import xml.etree.ElementTree as ET
import assign

routesPath=""
missionPath=""
    
# STATE LISTENER CLASS
class StateListener(traci.StepListener):
    def __init__(self, vehicleIds, emergencyBreakThreshold=-4.0):
        print("__init__!")
        self.vehicleIds = vehicleIds
        self.emergencyBreakThreshold = emergencyBreakThreshold
        self.vehicles = {}
        self.emergencyBreak = False
        self.collision = False
        print("routesPath="+routesPath)
        print("missionPath="+missionPath)
        routesTree = ET.parse(routesPath)
        routesRoot = routesTree.getroot()
        missionTree = ET.parse(missionPath)
        missionRoot = missionTree.getroot()
        
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

        # print vehicle data
        for vehicleId in self.vehicleIds:
            vehicle = self.vehicles[vehicleId]
            # if vehicleId="truck1"
            #    print("truck %s" % (tc.CMD_LOAD))
            # if vehicle is not None:
            # print("a=%s" % (vehicleId))
            # print("%s vel_t: %.2f m/s acc_t-1: %.2f m/s^2 dist: %.2f" % (vehicleId, vehicle[tc.VAR_SPEED], vehicle[tc.VAR_ACCELERATION], traci.lane.getLength(vehicle[tc.VAR_LANE_ID]) - vehicle[tc.VAR_LANEPOSITION]))

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
                if vehicle[tc.VAR_ACCELERATION ] *10 < self.emergencyBreakThreshold:
                    print("\nEmergency breaking required...")
                    self.emergencyBreak = True

def initVehicles(self):
    print(".")
    for vehicleId in self.vehicleIds:
        vehicle = self.vehicles[vehicleId]
        if vehicle is not None :  # and (traci.vehicle.getTypeID(vehID) == "TruckT"):
            #print("id= %" % traci.vehicle.getTypeID(vehID))
            print("id= %s" % traci.vehicle.getTypeID(vehicleId))
            # traci.vehicle.changeTarget(vehicleId, "--101938#11")

def randomInOut():
    if (random.randint(0, 1)):
        input =random.choice(data.northIn)
        output =random.choice(data.southOut)
    else:
        input =random.choice(data.southIn)
        output =random.choice(data.northOut)
    result =[input ,output]
    return result

# MAIN LAuncher  PROGRAM 
# start(rouPath,misPath)
def start(mapName,modeName):
    routesPath="cases/"+mapName+"/MyRoutes.rou.xml"
    missionPath="cases/"+mapName+"/Missions.mis.xml"
    routesTree = ET.parse(routesPath)
    routesRoot = routesTree.getroot()
    missionTree = ET.parse(missionPath)
    missionRoot = missionTree.getroot()
    print("Starting the TraCI server...")
    sumoBinary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"
    sumoCmd = [sumoBinary, "-c","cases/"+mapName+"/Network.sumocfg"]
    traci.start(sumoCmd)
    print("Subscribing to vehicle data...")
    print("Constructing a StateListener...")
    stateListener = StateListener(["0" ,"1"])
    traci.addStepListener(stateListener)
# disable speed control by SUMO

def assignMission(vehID,action):
    newTarget=action.get("target")
    print("assining new target="+newTarget)
    #traci.vehicle.changeTarget(vehID,newTarget)
    print("assignMission : Type="+str(action.get("type"))+" target="+str(action.get("target")))
    
    if(action.get("type")=="Load" or action.get("type")=="Unload"):
        print(action.get("type"))
        if(newTarget=='ContEdge0_0'):
            traci.vehicle.changeTarget(vehID,"ContEdge0")
            traci.vehicle.setContainerStop(vehID, "CS0", 200, 200, 0)
        else:
            traci.vehicle.changeTarget(vehID,"ContEdge0")
            traci.vehicle.setContainerStop(vehID, "CS0", 150, 150, 0)
            
    if(action.get("type")=="Park"):
        traci.vehicle.changeTarget(vehID, newTarget)
        traci.vehicle.setStop(vehID, newTarget, 100, 0, 0)
        
    if(action.get("type")=="Go"):
        traci.vehicle.changeTarget(vehID, newTarget)
               
def getAction(vehID,missionTree):
    for mission in missionTree.getroot():
        if vehID==mission.get("id"):
            for action in mission:
                if action.get("status")!="3":
                    return action

def getTarget(vehID,missionTree):
    for mission in missionTree.getroot():
        if vehID==mission.get("id"):
            for action in mission:
                #print(vehID+" action [getTarget]-> "+action.get("status"))
                if action.get("status")=="1":
                    #print("current action with status == 1 has taget="+action.get("target"))
                    return action.get("target")

def launch(mapName,modeName):
    
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")
    
    sumoBinary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"  # sumo-gui
    sumoConfig = ["-c", "cases/"+mapName+"/network.sumocfg", "-S"]
    sumoCmd = [sumoBinary, sumoConfig[0], sumoConfig[1], sumoConfig[2]]
    #TWT+=0
    
    #  #print(random.choice(list(containersDico.keys())))
    
    # Variables
    
    AWT =0  # Average Waiting time
    TWT =0  # Total Waiting Time
    CO =0
    CO2 =0
    
    AWTtrk =0  # Average Waiting time
    TWTtrk =0  # Total Waiting Time
    COtrk =0
    CO2trk =0
    distancetrk =0
    routesPath="cases/"+mapName+"/MyRoutes.rou.xml"
    missionPath="cases/"+mapName+"/missions.mis.xml"

# traci.vehicle.setSpeedMode("veh0",0)
# traci.vehicle.slowDown("veh0",1,3)
    step = 1
# add(self, vehID, routeID, typeID='DEFAULT_VEHTYPE', depart=None, departLane='first', departPos='base',
# departSpeed='0', arrivalLane='current', arrivalPos='max', arrivalSpeed='current', fromTaz='', toTaz='',
# line='', personCapacity=0, personNumber=0)
# (self, vehID, stopID, duration=-1073741824.0, until=-1073741824.0, flags=1)
# traci.vehicle.rerouteParkingArea("1", "parkingArea_--101938#11_0_0")
    TWT=0
    CO2=0
    CO =0
    NOx =0
    Noxtrk = 0
    distancetrk = 0  # truck distance
    distance = 0  # total distance
    count = 0
    xxx = []
    tab = []
    boool = 0
    
    stopped=[]
    initiated=[]
    
    parking1Rang=[]
    parking2Rang=[]
    VehLineStationEndPos1=[95.72 , 82.84 , 70.28 , 57.82 , 46]
    VehLineStationstartPos1=[84.50 , 72.03 , 59.62 , 47.12 , 35]
    VehLineStationEndPos2=[ 161.99 , 149.68 , 136.77 , 124.78 , 112.43 ]
    VehLineStationstartPos2=[ 151.07 , 138.94 , 126.24 , 113.77 , 101.43]
    vehpark1=[]
    vehpark2=[]

    counter=0
    routesTree = ET.parse( "cases/"+mapName+"/MyRoutes.rou.xml")
    missionTree = ET.parse("cases/"+mapName+"/Missions.mis.xml")
    
   
    
    while step < 3000:
        print(traci.vehicle.getIDList())
        flowVehicles = []
    # print(traci.vehicle.getDistance("1"))

        for vehID in traci.vehicle.getIDList():
            if ("trk" in vehID) :
                
                dataa = myPyLib.getData(vehID)
                #flowVehicles.append(vehID)
                dataa[0] = step
                dataa[1] = vehID
                dataa[2] = traci.vehicle.getWaitingTime(vehID)
                
                #search for the corresponding mission
                for mission in missionTree.getroot():
                    if mission.get("id")==vehID:
                        action=getAction(vehID,missionTree)
                        #si deja en cours ..break
                        if(action.get('status')=='0'):
                            newTarget= action.get("target")
                            action.set('status','1')
                            assignMission(vehID, action)                           
                            print(vehID+" New action. Target="+newTarget+" ("+action.get("type")+") status="+action.get("status")+" == "+str(mission[0].text))
                        elif (action.get('status')=='1'):
                            #tester si arrive
                            if(traci.vehicle.getStopState(vehID)!=0):
                                print("getStopState="+str(traci.vehicle.getStopState(vehID)))
                            if(action.get('type')=='Load' and traci.vehicle.getStopState(vehID)==33):
                                #newTarget= action.get("target")
                                action.set('status','3')
                            elif(action.get('type')=='Unload' and traci.vehicle.getStopState(vehID)==33):
                                #newTarget= action.get("target")
                                action.set('status','3')
                            elif(action.get('type')=='Park' and traci.vehicle.getStopState(vehID)==3):
                                newTarget= action.get("target")
                                action.set('status','2')
                            elif(action.get('type')=='Go'):
                                newTarget= action.get("target")
                                action.set('status','2')
                        
                            #tester si fini"   
                # traci.vehicle.setStop(vehID,"cs0",20,23,0)
        # print("flowVehicles= %s" % (flowVehicles))
        if(TWT==0):
            TWTrate =0
        else:
            TWTrate =(TWTtrk *100 ) /TWT
    
        if(CO2==0):
            CO2rate =0
        else:
            CO2rate =(CO2trk *100 ) /CO2
    
        if(CO==0):
            COrate =0
        else:
            COrate =(COtrk *100 ) /CO
    
        if(NOx==0):
            Noxrate =0
        else:
            Noxrate =(COtrk *100 ) /NOx
        #prk1rate =traci.parkingarea.getVehicleCount("Prk1" ) *100 /10
        #prk2rate =traci.parkingarea.getVehicleCount("Prk2" ) *100 /10
    
        # print(traci.parkingarea.getVehicleCount("Prk1"))
    
        # if (step % 10 ==0):
        # print("\n%s" % step)
        # print("distancetrk= %.2f Km Totaldistance %.2f Km" % ((distancetrk/1000),(distance/1000)))
        # print("TWTrate= %.2f TWTtrk= %s TWT= %.2f" % (TWTrate,TWTtrk,TWT))
        # print("prk1rate = %.2f%% prk2rate = %.2f%% " % (prk1rate,prk2rate))
        # print("CO2rate= %.2f CO2trk= %s CO2= %.2f" % (CO2rate,CO2trk,CO2))
        # print("COrate= %.2f COtrk= %s CO2= %.2f" % (COrate,COtrk,CO))
        # print("Noxrate= %.2f Noxtrk= %.2f CO2= %.2f" % (Noxrate,Noxtrk,NOx))
        # advance the simulation
        # print("\nstep: %i %s" %(step,traci.vehicle.getCO2Emission("1")))
        traci.simulationStep()
        step+=1
    
    myPyLib.save(xxx)
    print()
    print("\nStopping the TraCI server...")
    traci.close()


#start
launch("Nantes", "NOCITS")
#start("Nantes", "NOCITS")