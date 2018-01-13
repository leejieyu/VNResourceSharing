import network
from simulate import Simulation
from networkmodel import Network, SubstrateN

def embed(vnsPerWin, windows, isInf, linkRate, maxCPU, maxBw, maxLife):
    sn_structure = Network.mkGraph(100, 0.5, 100, 1000)
    SN = SubstrateN(sn_structure["nodes"],sn_structure["links"])
    SN.findKShortestPaths()

    test = Simulation(SN, vnsPerWin, windows)
    test.dispatch(isInf, linkRate, maxCPU, maxBw, maxLife)


vns = 10
windows = 10
isInf = False
linkRate = 10
maxCPU = 100
maxBw = 100
maxLife = 5
embed(vns, windows, isInf, linkRate, maxCPU, maxBw, maxLife)