import sumolib

net = sumolib.net.readNet('cases/Nantes/MyNetwork.net.xml')

fromEdge = net.getEdge('-14864')
toEdge = net.getEdge('-3542')

if fromEdge and toEdge:
    route = net.getShortestPath(fromEdge, toEdge)
    if route is None:
        print("⚠ No valid route!")
    else:
        print("✅ Valid route exists.")
