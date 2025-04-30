'''
Created on 21 juin 2021

@author: wbouazza
'''
import random
import os, sys
import sumolib,traci
import xml.etree.ElementTree as ET
from Lib.pickle import NONE

class dataOut:
    test=[]
    
def randomList(list,nbElement):
    r=[]
    i=0
    print("randomList of %s elements from %s"%(nbElement,list))
    while i< nbElement:
        #print(random.choice(list))
        r.append(random.choice(list))
        i+=1
    return r 

def countTrucks(missionRoot):
    result=0
    for element in missionRoot:
        result=result+1
    return result

def rdmMission(nbOperMax,listOper):
    nbOper=random.randint(1, nbOperMax)
    results=[]
    for i in range(nbOper):
        results.append(random.choice(listOper))
    return results

def keep(substring,IdList):
    result=[]

    for i in IdList:
        if substring in i:
            result.append(i)
    return result


def randomElement(tab):
    '''
    :param tab:
    '''
    return random.choice(tab)

def readMeta(mapName,nbTrucks):
    inputs=[]
    outputs=[]
    missions=[]
    parkings=[]
    stops=[]
    routes=[]
    
    metaTree = ET.parse('Cases/'+mapName+'/metaData.xml')
    metaRoot = metaTree.getroot()
    
    for element in metaRoot:
        if element.tag=="inputs":
            for input in element:
                inputs.append(input.get("value"))
    print("inputs="+str(inputs))
    
    for element in metaRoot:
        if element.tag=="outputs":
            for output in element:
                outputs.append(output.get("value"))
    print("outputs="+str(outputs))
    
    for element in metaRoot:
        if element.tag=="missions":
            for mission in element:
                missions.append(mission.get("value"))
    print("missions="+str(missions))
    
    for element in metaRoot:
        if element.tag=="parkings":
            for parking in element:
                dic=dict()
                dic['name']=parking.get("value")
                dic['edge']=parking.get("edge")
                parkings.append(dic)
                #parkings.append(parking.get("edge"))                   
    print("parkings="+str(parkings))  
    
    for element in metaRoot:
        if element.tag=="stops":
            for stop in element:
                dico=dict()
                dico["name"]=stop.get("value")
                dico["edge"]=stop.get("edge")
                stops.append(dico)                
    print("stops="+str(stops))  
    
    for element in metaRoot:
        if element.tag=="routes":
            for route in element:
                routes.append(route.get("edges"))                
    print("routes="+str(routes))  
    return (inputs,outputs,missions,parkings,stops,routes)

def getAlternative(metadataRoot,target):
    action = ET.Element("action")
    for element in metadataRoot:
        if element.tag=="parkings":
            for parking in element:
                #print("searching for alternatives to "+ target+"...found: "+parking.get('value'))
                if parking.get('value')!=target:
                    action.set("type", "Park") 
                    action.set("target",parking.get('value'))
                    action.set("edge",parking.get('edge'))
                    action.set("status","1") 
                    return action
        
    return "no alternatives"
            
def generateMission(missionType,id,data,choseParking,randomStopingDurationIndex):
    '''

    :param missionType:"P","LP","UP","LG","UG" or "PG"
    :param id:
    :param data:
    '''
    sequence=[]
    stopingDuration=[1800, 900 , 3600, 900, 2400, 3600]
    #missiions=["P","LP","UP","LG","UG","PG"]
    if missionType=="P":
        #print(missionType)
        sequence.append(generateP(data))
        #p=random.choice(data.parkingDico)

        #parkingDico={'Prk1': "--101938#11", 'Prk2': "--101932"}
        #x=random.randint(0, 1)

        if (choseParking==0) :
            traci.vehicle.changeTarget(id, "--101938#11")
            traci.vehicle.setParkingAreaStop(id, "Prk1", stopingDuration[randomStopingDurationIndex])
            #print("ID = %s   StopingDuration = %.2f " % (id, stopingDuration[randomStopingDurationIndex]))

        if (choseParking==1) :
            traci.vehicle.changeTarget(id, "--101932")
            traci.vehicle.setParkingAreaStop(id, "Prk2", stopingDuration[randomStopingDurationIndex])
            #print("ID = %s  ||  StopingDuration = %.2f " % (id, stopingDuration[randomStopingDurationIndex]))



    if missionType=="LP":
        print(missionType)
        sequence.append(generateL(data))
        sequence.append(generateP(data))

    if missionType=="L":
        sequence.append(generateL(data))


    if missionType=="UP":
        print(missionType)
        sequence.append(generateU(data))
        sequence.append(generateP(data))
    if missionType=="LG":
        print(missionType)
        sequence.append(generateL(data))
        sequence.append(generateG(data))
    if missionType=="UG":
        print(missionType)
        sequence.append(generateU(data))
        sequence.append(generateG(data))
    if missionType=="PG":
        print(missionType)
        sequence.append(generateP(data))
        sequence.append(generateG(data))

def generateP(data):

    result=[] #parking name + egde
    #result.append()

def generateL(data):
    print("")
def generateU(data):
    print("")
def generateG(data):
    print("")




def getData(vehID):

    AWT=0 #Average Waiting time
    TWT=0 #Total Waiting Time
    CO=0
    CO2=0
    TWT= traci.vehicle.getAccumulatedWaitingTime(vehID)
    CO2=traci.vehicle.getCO2Emission(vehID)
    CO=traci.vehicle.getCO2Emission(vehID)
    NOx=traci.vehicle.getCO2Emission(vehID)
    d=traci.vehicle.getDistance(vehID)
    resultTable=[vehID,TWT,CO2,CO,NOx,d]
    return resultTable




def printResult(xxx,count) :
    for i in range(count):
        print("ID = %s  ||  TWT = %.2f  || CO2=%.2f   || CO=%.2f  || NOx =%.2f || distance=%.2f " % (xxx[i][0], xxx[i][1], xxx[i][2], xxx[i][3], xxx[i][4], xxx[i][5]))


def Sum(xxx,count,id,index): #1=TWT / 2=CO2 / 3=CO / 4=NOx / 5=Distance
    add=0
    for i in range(count):
        if (xxx[i][0]==id):
            add+=xxx[i][index]
    return add




def save(dataa):
    df = pd.DataFrame(dataa).T
    df.to_excel(excel_writer = "data/test.xlsx")


def AddVehicleToTable(tab,vehID) : #list of veh "flow" not duplicated
    if vehID not in tab:
        tab.append(vehID)

def initList(size,value) : #list of veh "flow" not duplicated
    result=[]
    for i in range(size):
        result.append(value)
    return result

def getHeader(nbTrucks,prefix) : #list of veh "flow" not duplicated
    result=""
    for i in range(nbTrucks):
        result=result+prefix+str(i+1)+";"
    return result

def listToLine(list,divisor):
    line=""
    for item in list:
        line=line+str(int(item)/divisor)+";"
    return line

def ChangeParkingIfFull(veh) :
    x1 = traci.parkingarea.getVehicleCount("Prk1")
    x2 = traci.parkingarea.getVehicleCount("Prk2")
    edge= traci.vehicle.getRoadID(veh)
    if (edge =="--101938#11") :
        if(x1==10 and x2<10 and traci.vehicle.getStopState(veh)==0 ) :
            return ("--101932")
    elif (edge =="--101932") :
        if (x1<10 and x2==10 and traci.vehicle.getStopState(veh)==0) :
            return ("--101938#11")


def StopAtRoadSide(veh,endpos,startpos) :
    x1 = traci.parkingarea.getVehicleCount("Prk1")
    x2 = traci.parkingarea.getVehicleCount("Prk2")
    edge= traci.vehicle.getRoadID(veh)
    if (x1==10 and edge=="--101938#11") :
        traci.vehicle.setStop(veh,"--101938#11",endpos ,0 ,10000 , 1,startpos, -1)
    if (x2==10 and edge=="--101932") :
        traci.vehicle.setStop(veh,"--101932",endpos ,0 ,10000 , 1,startpos, -1)



def ChooseParkingBeforeArrival(veh) :
    x1 = traci.parkingarea.getVehicleCount("Prk1")
    x2 = traci.parkingarea.getVehicleCount("Prk2")
    if (x1 == 10 and x2 < 10 and traci.vehicle.getStopState(veh) == 0):
        return ("--101932")
    elif  (x1<10 and x2==10 and traci.vehicle.getStopState(veh)==0) :
        return ("--101938#11")
    else:
        return ("0")







