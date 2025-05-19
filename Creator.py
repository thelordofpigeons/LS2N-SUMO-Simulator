import Starter
import myPyLib
import xml.etree.ElementTree as ET
from random import randint
from xml.dom import minidom
import random
import xml.dom
from decimal import Decimal
import os
import sumolib
# from libsumo.libsumo import vehicle

inputs = []
outputs = []
missions = []
parkings = []
stops = []
routes = []

mapName = "Nantes"


def sortchildrenby(parent, attr):
    parent[:] = sorted(parent, key=lambda child: float(child.get(attr)))


def is_route_possible(net, from_edge_id, to_edge_id):
    fromEdge = net.getEdge(from_edge_id)
    toEdge = net.getEdge(to_edge_id)

    if fromEdge and toEdge:
        route = net.getShortestPath(fromEdge, toEdge)
        return route is not None
    else:
        return False


def injectionTraffic(mapName, nbTrucks, vehicle_type):

    net = sumolib.net.readNet('cases/' + mapName + '/MyNetwork.net.xml')
    meta = myPyLib.readMeta(mapName, nbTrucks)
    inputs = meta[0]
    outputs = meta[1]
    missions = meta[2]
    parkings = meta[3]
    stops = meta[4]
    routes = meta[5]
    '''for i in meta:
        print(i)
   
    meta[]
    0 inputs=[]
    1 outputs=[]
    2 missions=[]
    3 parkings=[]
    4 stops=[]
    5 routes=[]'''

    injectionTraffic = myPyLib.randomList(missions, nbTrucks)

    print(injectionTraffic)
    id = 1
    script = ""

    '''1 Creation des vehicules'''
    print("reading ..."+'cases/'+mapName+'/myRoutes.rou.xml'+" -->> inRoot")
    inRoot = ET.parse('cases/'+mapName+'/myRoutes.rou.xml').getroot()

    '''2 recuperer les anciens vehicules'''
    vehRoot = ET.Element("routes")
    for veh in inRoot:
        if veh.tag == "vehicle":
            veh_id = veh.get("id")
            if veh_id and not veh_id.startswith("trk"):
                vehRoot.append(veh)

    '''3 creation et tri des departs'''
    departs = []
    for i in range(nbTrucks):
        departs.append(randint(0, nbTrucks*120))
    departs.sort()
    print("depart=" + str(departs))

    id = 1  # initialize before loop

    while id <= nbTrucks:
        # Randomly pick one safe predefined route
        selected_route = random.choice(routes)  # routes loaded from MetaData
        edge_list = selected_route.split()  # split string into list of edges

        # Now create the vehicle and assign this route
        vehicle = ET.SubElement(vehRoot, "vehicle")
        vehicle.set("id", "trk" + str(id))
        vehicle.set("color", "255,0,0")
        vehicle.set("type", vehicle_type)
        vehicle.set("depart", str(departs[id - 1]) + ".00")

        route_elem = ET.SubElement(vehicle, "route")
        route_elem.set("edges", " ".join(edge_list))
        print(f"✅ Added vehicle {vehicle.get('id')} with route {edge_list}")

        id += 1

    ''' 5 Trier inRoot '''
    sortchildrenby(vehRoot, 'depart')
    ET.dump(vehRoot)

    ''' 6 fusion avec outRoot'''
    outRoot = ET.Element("routes")
    # if(inRoot.findtext("vType")==None):

    vType = ET.SubElement(outRoot, "vType")
    vType.set("id", vehicle_type)

    if vehicle_type == "Truck":
        vType.set("vClass", "trailer")
        vType.set("guiShape", "truck")
    else:  # MissionVehicle
        vType.set("vClass", "passenger")
        vType.set("guiShape", "passenger")
        vType.set("color", "0,0,255")
        vType.set("accel", "2.6")
        vType.set("decel", "4.5")
        vType.set("length", "4.5")
        vType.set("maxSpeed", "25")

    for veh in vehRoot:
        outRoot.append(veh)

    '''7 formatage et sauvegarde'''
    dom = minidom.parseString(ET.tostring(
        outRoot, encoding="unicode", method=None))
    formated = dom.toprettyxml(indent="  ", newl="")
    f = open("cases/"+mapName+"/MyRoutes.rou.xml", "w")
    f.write(formated)

    " Supprimer les lignes vides "

    f.close()
    return outRoot


def createMissions(mapName, nbTrucks, traffic):

    print("Creating " + str(nbTrucks) + " missions")
    missionRoot = ET.Element("Missions")
    missionsList = []

    meta = myPyLib.readMeta(mapName, nbTrucks)
    inputs = meta[0]
    outputs = meta[1]
    missions = meta[2]
    parkings = meta[3]
    stops = meta[4]
    routes = meta[5]

    i = 0
    for trk in range(nbTrucks):  # traffic.findall("vehicle"):
        # if trk.get("id").contains("trk"):
        newMission = random.choice(missions)
        missionsList.append(newMission)
        # print(missionsList)
        # missionRoot.append(newMission)
        pmission = ET.SubElement(missionRoot, "mission")
        pmission.set("id", "trk" + str(i + 1))
        pmission.set("type", newMission)

        for j in range(len(newMission)):
            pAction = ET.SubElement(pmission, "action")

            if newMission[j] == "L":
                pAction.set("type", "Load")
                rdmStop = random.choice(stops)
                pAction.set("target", rdmStop["name"])
                pAction.set("edge", rdmStop["edge"])
                pAction.set("status", "0")
            elif newMission[j] == "U":
                pAction.set("type", "Unload")
                rdmStop = random.choice(stops)
                pAction.set("target", rdmStop["name"])
                pAction.set("edge", rdmStop["edge"])
                pAction.set("status", "0")
            elif newMission[j] == "P":
                pAction.set("type", "Park")
                rdmParking = random.choice(parkings)
                pAction.set("target", rdmParking.get('name'))
                pAction.set("edge", rdmParking.get('edge'))
                pAction.set("status", "0")
            elif newMission[j] == "G":
                pAction.set("type", "Go")
                output = random.choice(outputs)
                pAction.set("target", output)
                pAction.set("edge", output)
                pAction.set("status", "0")
        i += 1

    f = open('cases/'+mapName+"/missions.mis.xml", "w")
    # , parser).parse("data/output.xml") # or xml.dom.minidom.parseString(xml_string)
    dom = minidom.parseString(ET.tostring(missionRoot, encoding="unicode"))
    missionFormated = dom.toprettyxml(indent="  ", newl="\n")
    # print(missionFormated)
    f.write(missionFormated)


def create(mapName, nbTrucks, vehicle_type):
    print("Welcome to Instance Creator ")
    print("..creating "+str(nbTrucks)+'trucks on the map "'+mapName+'"')
    # create()
    traffic = injectionTraffic(mapName, nbTrucks, vehicle_type)
    createMissions(mapName, nbTrucks, traffic)


# Launcher.start("data/MyRoutes.rou.xml","data/missions.mis.xml")
# create("MarsFull",100)
