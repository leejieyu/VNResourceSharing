import math
import random
import logging
import queue
from networkmodel import Network, VirtualN
class Simulation(object):
    RETRY_TIMES = 2
    MIN_NODE_PER_REQ = 3

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename='log/emulation.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    def __init__(self, sn, vnsPerWin, windows):
        self.sn = sn
        self.vnsPerWin = vnsPerWin
        self.windows = windows
        self.counter = 0
        self.currSum = 0
        self.sucRev = 0
        self.sucCos = 0
        self.sucSum = 0
        self.failSum = 0

        self.aliveVN = []
        #Two queues for ready requests and postponed requests
        self.readyQueue = []
        self.postQueue = queue.Queue()


        self.indices = []
        self.sucArray = []

    # greedy algorithm
    def mapNode(self, vnIndex):
        vn = self.readyQueue[vnIndex]
        if vn.state != "R": # check the sate of vn, R indicate "ready"
            raise Exception("Wrong state(" + vn.state + ") of request" + vn.id + "in ready queue")

        for i in range(len(vn.nodes)): # mapping nodes of vn based greedy algorithm
            node = vn.nodes[i]
            maxID= self.sn.getMaxWeightedNode(vn.id, node.cpu)
            if maxID < 0 or node.cpu > self.sn.nodes[maxID].cpu:
                for node in vn.nodes:
                    if len(node.usage) > 0:
                        self.sn.alterNodeResource(node.usage[0], node.cpu, "add", vn.id)
                        node.usage.pop(0)
                if vn.tryCounts < Simulation.RETRY_TIMES:
                    vn.tryCounts += 1
                    self.postQueue.put(vn)
                    vn.state = "P"
                return -1
            node.usage.append(maxID)
            self.sn.alterNodeResource(maxID, node.cpu, "sub", vn.id)

        vn.state = "NF"
        return 0


    def mapLink2Steps(self, vnIndex, isInf):
        vn = self.readyQueue[vnIndex]
        tmpLinks = []
        flag = 0
        cost = 0
        if vn.state != "NF":
            raise Exception("Wrong state(" + vn.state + ") of request" + vn.id + "in ready queue")
            return -1
        for i in range(len(vn.links)):
            link = vn.links[i]
            l_from = vn.nodes[link.src].usage[0] # 找到这个虚拟节点所映射的物理节点
            l_to = vn.nodes[link.dst].usage[0]
            tmpLinks = []
            link.usage = []
            while l_from != l_to:
                next = self.sn.paths[l_from][l_to]
                if next == -1:
                    flag = 2
                    break
                index = -1
                for i, l in enumerate(self.sn.links):
                    if (l.src == l_from and l.dst == next) or (l.src == next and l.dst == l_from):
                        index = i
                if index == -1 or self.sn.links[index].bw < link.bw:
                    flag = 1
                    break
                tmpLinks.append(index)
                link.usage.append(index)
                l_from = next

            if flag == 1:
                while flag == 1:
                    tmpLinks =[]
                    link.usage = []
                    self.indices.append({"index":index, "src": self.sn.links[index].src, "dst": self.sn.links[index].dst})
                    self.sn.links[index].src = -1
                    self.sn.links[index].dst = -1
                    self.sn.findKShortestPaths()
                    l_from = vn.nodes[link.src].usage[0]
                    flag = 0
                    while l_from != l_to:
                        next = self.sn.paths[l_from][l_to]
                        if next == -1:
                            flag = 2
                            break
                        index = -1
                        for i,l in enumerate(self.sn.links):
                            if (l.src == l_from and l.dst == next) or (l.src == next and l.dst == l_from):
                                index = i
                        if index == -1 or self.sn.links[index].bw < link.bw :
                            flag = 1
                            break
                        tmpLinks.append(index)
                        link.usage.append(index)
                        l_from = next

            if flag == 0:
                cost += link.bw * (len(tmpLinks) - 1)
                self.sn.alterLinksResource(tmpLinks, link.bw, "sub", vn.id)

            elif flag == 2:
                for node in vn.nodes:
                    if len(node.usage) == 0:
                        raise  Exception("Node resource error in link resource releasing.")
                    self.sn.alterNodeResource(node.usage[0], node.cpu, "add", vn.id)
                    node.usage = []
                for link in vn.links:
                    if len(link.usage):
                        self.sn.alterLinksResource(link.usage, link.bw, "add", vn.id)
                        link.usage = []
                if vn.tryCounts < Simulation.RETRY_TIMES:
                    vn.tryCounts += 1
                    self.postQueue.put(vn)
                    vn.state = "P"
                break
        for indice in self.indices:
            self.sn.links[indice["index"]].src = indice["src"]
            self.sn.links[indice["index"]].dst = indice["dst"]
        self.indices = []
        if flag == 0:
            self.sucRev += vn.revenue - len(vn.links)
            self.sucCos += cost + vn.revenue -len(vn.links)
            vn.state = "LF"
            return  0
        return -1


    def dispatch(self, isInf, linkRate, maxCPU, maxBw, maxLife):
        """the main process of emulation"""
        win = min(self.windows, 1000) # 定义窗口大小
        logging.info("Total time windows:" + str(win))
        for k in range(win): # 循环
            logging.info("Time window No." + str(k+1))

            # 考虑虚网离开的情况, 将满足离开标准的虚网移除。
            if not isInf:
                logging.info("choice.///")
                for vn in self.aliveVN:#遍历当前映射的虚网
                    if vn.life <= k: # 如果虚网的生存期小于k，就将该虚网释放。？？ 不是很懂
                        doneReq = vn
                        if doneReq.state != "LF":
                            raise Exception("Uncorrect state in inQueue!")
                        logging.info("Release resources of request " + str(doneReq.id))
                        for node in doneReq.nodes:
                            if len(node.usage) == 0:
                                raise  Exception("Node resource error in link resource releasing.")
                            self.sn.alterNodeResource(node.usage[0], node.cpu, "add", doneReq.id)
                        for link in doneReq.links:
                            if len(link.usage) > 0:
                                self.sn.alterLinksResource(link.usage, link.bw, "add", doneReq.id)
                        self.aliveVN.remove(vn)
            logging.info("the alive VN " + str(len(self.aliveVN)))

            # 当拒绝请求队列不为空，将拒绝队列里的虚网加入待映射队列
            while not self.postQueue.empty():
                tmpPostReq = self.postQueue.get()
                tmpPostReq.state = "R"
                self.readyQueue.append(tmpPostReq)
                self.failSum -= 1

            #随机生成新的请求
            randomSum = int(math.floor(random.random() * (self.vnsPerWin + 1) + self.vnsPerWin * 1/2))
            for j in range(randomSum):
                logging.info("have virtual network" + str(j))
                tmpNode = math.floor(random.random() * 7 + Simulation.MIN_NODE_PER_REQ)
                tmpReq = Network.mkGraph(tmpNode, linkRate, maxCPU, maxBw)
                tmpLife = (0 if isInf else k + 1 + math.floor(random.random() * maxLife))
                req = VirtualN(self.counter, tmpReq["nodes"], tmpReq["links"], tmpLife)

                self.counter += 1
                self.readyQueue.append(req)

            #映射待映射队列里的虚网请求
            self.readyQueue.sort(key = lambda tmp : tmp.revenue, reverse=True)
            logging.info("readyQueue " + str(len(self.readyQueue)))
            while len(self.readyQueue) > 0:
                self.currSum += 1
                if self.readyQueue[0].state != "R":
                    raise Exception("Request in ready queue with uncorrect state: " + self.readyQueue[0].state)
                if self.mapNode(0) != 0:
                    self.failSum += 1
                else:
                    if self.mapLink2Steps(0, isInf) == 0:
                        self.sucSum += 1
                        self.aliveVN.append(self.readyQueue[0])
                        #if not isInf:
                        #    self.aliveVN.append()
                    else:
                        self.failSum += 1
                self.readyQueue.pop(0)
            self.sucArray.append(self.sucSum)
        if self.sucCos == 0:
            logging.info("sucCos = 0")
        else:
            logging.info("prov R/C " + str(self.sucRev / self.sucCos))




