import random
import math


class Node(object):
    def __init__(self,cpu):
        self.cpu = cpu
        self.usage = []


class Link(object):
    def __init__(self,src,dst,bw):
        self.src = src
        self.dst = dst
        self.bw = bw
        self.usage = []


class Network(object):
    def __init__(self, nodes, links):
        self.nodes = nodes
        self.links = links
        for i, node in enumerate(self.nodes):
            node.id = i
        for i, link in enumerate(self.links):
            link.id = i

    def sum_nodes(self):
        return len(self.nodes)

    def sum_links(self):
        return len(self.links)

    @staticmethod
    def mkGraph(sum_n, linkRate, maxCPU, maxBw):
        """generate a network(nodes and links)
           avoid unconnected graph; sum_n should>= 3
        """
        nodes = []
        links = []
        for i in range(0 , sum_n):
            while True:
                tmpNode = Node(random.random()*maxCPU)
                if tmpNode != 0:
                    break
            nodes.append(tmpNode)
        l = Link(0, 1, random.random()*maxCPU)
        links.append(l)
        for i in range(2 , len(nodes)):
            flag = True
            for j in range(0 , i):
                if random.random() <= linkRate:
                    tmpL = Link(j , i, random.random()*maxBw)
                    links.append(tmpL)
                    flag = False
            if flag:
                target = math.floor(random.random()*i)
                if target == i:
                    target -= 1
                tmpL = Link(target, i, random.random()*maxBw)
                links.append(tmpL)
        net = {"nodes": nodes,"links":links}
        return net


class VirtualN(Network):
    def __init__(self, id, nodes, links, life):
        super(VirtualN, self).__init__(nodes, links)
        self.id = id
        self.state = "R"
        self.tryCounts = 0

        #self.resourceUsage = {"CPU": [ [] for i in range[self.sum_nodes()] ],"BW":[ [] for i in range[self.sum_links()] ]}

        if life != None:
            self.life = life
        else:
            self.life = 1
        tmp = 0
        for node in self.nodes:
            tmp += node.cpu

        self.revenue = tmp
        tmp = 0
        for link in self.links:
            tmp += link.bw
        self.revenue += tmp


class SubstrateN(Network):
    # def __init__(self, nodes, links):
    #     super(SubstrateN,self).__init__(nodes,links)
    #     nodeResource = [{"unallocated": ,""}]
    def getMaxWeightedNode(self,exception, cpu):
        weights = [0 for i in range(self.sum_nodes()) ]
        for link in self.links:
            weights[link.src] += link.bw
            weights[link.dst] += link.bw
        for i,node in enumerate(self.nodes):
            weights[i] *= node.cpu

        max = {"id": -1, "value":0}

        for i, val in enumerate(weights):
            if self.nodes[i].cpu >= cpu and val > max["value"]:
                try:
                    self.nodes[i].usage.index(exception)
                except ValueError:
                    max["id"] = i
                    max["value"] = val
        return max["id"]

    def alterNodeResource(self, node, val, type, vnID):
        if type == "add":
            self.nodes[node].cpu += val
            tmpID = self.nodes[node].usage.index(vnID)
            if tmpID != -1:
                self.nodes[node].usage.pop(tmpID)
        elif type == "sub":
            if self.nodes[node].cpu < val :
                raise Exception("Node" + node + "CPU is not enough!")
            self.nodes[node].cpu -= val
            self.nodes[node].usage.append(vnID)
        else:
            raise Exception("Unknown alter node resource type!")

    def alterLinksResource(self, linkIndexs, val, type, vnID):
        if type == "add":
            for linkIndex in linkIndexs:
                self.links[linkIndex].bw += val
                #self.links[linkIndex].usage.pop(self.links[linkIndex].usage.index.py(vnID))
                self.links[linkIndex].usage.remove(vnID)
        elif type == "sub":
            isEnough = True
            for linkIndex in linkIndexs:
                if self.links[linkIndex].bw < val:
                    isEnough = False
                    break
            if isEnough:
                for linkIndex in linkIndexs:
                    self.links[linkIndex].bw -= val
                    self.links[linkIndex].usage.append(vnID)
            else:
                raise Exception("Link resource not met!")
        else:
            raise Exception("Unknown alter links resource type!")

    #找出一张网络中任意两节点之间的k条最短路径
    def findKShortestPaths(self):
        sum_nodes = self.sum_nodes()
        weights = [[10000 for i in range(sum_nodes)] for i in range(sum_nodes)]
        self.paths = [[-1 for i in range(sum_nodes)] for i in range(sum_nodes)]
        #初始化
        for i in range(sum_nodes):
            for j in range(sum_nodes):
                if i == j:
                    weights[i][j] = 0
                    self.paths[i][j] = j
        #将物理拓扑填进去
        for link in self.links:
            if link.src >= 0 and link.dst >=0:
                weights[link.src][link.dst] = 1
                weights[link.dst][link.src] = 1
                self.paths[link.src][link.dst] = link.dst
                self.paths[link.dst][link.src] = link.src

        for k in range(sum_nodes):
            for i in range(sum_nodes):
                for j in range(sum_nodes):
                    if i == k or j == k or i ==j:
                        continue
                    if(weights[i][k] + weights[k][j] < weights[i][j]):
                        weights[i][j] = weights[i][k] + weights[k][j]
                        self.paths[i][j] = self.paths[i][k]

