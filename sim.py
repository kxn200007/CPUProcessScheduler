import re
import sys

ARRIVAL = 0
UNBLOCK = 1

EVENT_TYPE = ["ARRIVAL", "UNBLOCK"]


class Process:
    stats = None

    def __init__(self, pid, arrive, activities):
        self.pid = pid
        self.arrive = arrive
        self.activities = activities

    def __str__(self):
        return "Process " + str(self.pid) + ", Arrive " + str(self.arrive) + ": " + str(self.activities)


class Event:
    def __init__(self, etype, process, time):
        self.type = etype
        self.process = process
        self.time = time

    def __lt__(self, other):
        if self.time == other.time:
            if self.type == other.type:
                return self.process.pid < other.process.pid
            else:
                return self.type < other.type
        else:
            return self.time < other.time

    def __str__(self):
        return "At time " + str(self.time) + ", " + EVENT_TYPE[self.type] + " Event for Process " + str(self.process.pid)


class EventQueue:
    def __init__(self):
        self.queue = []
        self.dirty = False

    def push(self, item):
        if type(item) is Event:
            self.queue.append(item)
            self.dirty = True
        else:
            raise TypeError("Only Events allowed in EventQueue")

    def __prepareLookup(self, operation):
        if self.queue == []:
            raise LookupError(operation + " on empty EventQueue")
        if self.dirty:
            self.queue.sort(reverse=True)
            self.dirty = False

    def pop(self):
        self.__prepareLookup("Pop")
        return self.queue.pop()

    def peek(self):
        self.__prepareLookup("Peek")
        return self.queue[-1]

    def empty(self):
        return len(self.queue) == 0

    def hasEvent(self):
        return len(self.queue) > 0

    def __str__(self):
        tmp = 'EventQueue('
        if len(self.queue) > 0:
            tmp = tmp + str(self.queue[0])
        for e in self.queue[1:]:
            tmp = tmp + "; " + str(e)
        tmp = tmp + ")"
        return tmp

    def __iter__(self):
        if self.dirty:
            self.queue.sort(reverse=True)
            self.dirty = False
        return iter(self.queue)


class SchedulerTemplate:
    def __init__(self, procs):
        self.procs = procs

    def initialize(self, sim):
        print("Initialize")

    def timeout(self, sim):
        print("Timeout")

    def stopRunning(self, sim):
        print("Process stopped running")

    def arrive(self, p, sim):
        print("Process {} arrived".format(p.pid))

    def unblock(self, p, sim):
        print("Process {} unblocked".format(p.pid))

    def idle(self, sim):
        print("CPU Idle")

class FCFS_Scheduler:
    def __init__(self, procs):
        self.procs = procs
        self.ready_queue = []

    def initialize(self, sim):
        for p in sim.procs:
            sim.addArrival(p)

    def timeout(self, sim):
        pass

    def stopRunning(self, sim):
        pass

    def arrive(self, sim, p):
        self.ready_queue.append(p)
        if len(self.ready_queue) == 1:
            sim.runningTime = p.activities[0]

    def unblock(self, p, sim):
        pass

    def idle(self, sim):
        if len(self.ready_queue) > 0:
            p = self.ready_queue.pop(0)
            sim.runningTime = p.activities[0]
            print("Process {} started at time {}".format(p.pid, sim.clock))

    def done(self, p, sim):
        print("Process {} finished at time {}".format(p.pid, sim.clock))

class SPN_Scheduler:
    def __init__(self, procs):
        self.procs = procs
        self.ready_queue = []

    def initialize(self, sim):
        for p in self.procs:
            sim.addArrival(p)

    def add_to_ready_queue(self, proc):
        self.ready_queue.append(proc)
        self.ready_queue.sort(key=lambda x: x.activities[0])

    def timeout(self, sim):
        pass

    def stopRunning(self, sim):
        sim.runningTime = None

    def arrive(self, sim, p):
        self.add_to_ready_queue(p)
        if sim.runningTime is None:
            self.start_next_process(sim)

    def unblock(self, p, sim):
        self.add_to_ready_queue(p)
        if sim.runningTime is None:
            self.start_next_process(sim)

    def idle(self, sim):
        if self.ready_queue:
            self.start_next_process(sim)

    def start_next_process(self, sim):
        if not self.ready_queue:
            return

        next_proc = self.ready_queue.pop(0)
        sim.runningTime = next_proc.activities.pop(0)

class Sim:
    debugMode = False
    SCHED_IDS = ["FCFS", "RR", "SPN", "HRRN", "FEEDBACK"]

    def __init__(self, procs, scheduler):
        self.clock = 0
        self.procs = procs
        self.events = EventQueue()
        self.runningTime = None
        self.sched = scheduler

    def run(self):
        self.sched.initialize(self)
        move = self.getTimeForward()
        while move is not None:
            if self.handleTimeDone(move):
                move = self.getTimeForward()
                while move is not None and self.handleTimeDone(move):
                    move = self.getTimeForward()
            else:
                if self.runningTime is not None:
                    self.runningTime -= move
                self.clock = self.events.peek().time
                self.processEvent(self.events.pop())
            while self.events.hasEvent() and self.events.peek().time == self.clock:
                self.processEvent(self.events.pop())
            if self.runningTime is None:
                self.sched.idle(self)
            move = self.getTimeForward()

    def getTimeForward(self):
        if self.events.hasEvent():
            return self.events.peek().time - self.clock
        elif self.runningTime is not None:
            return self.runningTime
        else:
            return None

    def handleTimeDone(self, move):
        if move is None:
            return False

        canStopRunning = self.runningTime is not None and self.runningTime <= move
        if canStopRunning:
            self.clock += self.runningTime
            self.runningTime = None
            self.sched.stopRunning(self)
            return True
        return False

    def processEvent(self, e):
        if e.type == ARRIVAL:
            self.sched.arrive(self, e.process)
        else:  # e.type == UNBLOCK
            self.sched.unblock(self, e.process)

    def addArrival(self, p):
        self.events.push(Event(ARRIVAL, p, p.arrive))

    def addUnblockEvent(self, p, t):
        self.events.push(Event(UNBLOCK, p, self.clock + t))

    @staticmethod
    def parseProcessFile(procFile):
        procs = []
        with open(procFile) as f:
            lines = [line.rstrip() for line in f]  # Read lines of the file
            lineNumber = 1
            for p in lines:
                tmp = re.split('\s+', p)
                # Check to make sure there is a final CPU activity
                if len(tmp) < 3:
                    raise ValueError("Process with no final CPU activity at line " + str(lineNumber))
                # Check to make sure each activity, represented by a duration,
                # is an integer, and then convert it.
                for i in range(0, len(tmp)):
                    if re.fullmatch('\d+', tmp[i]) == None:
                        raise ValueError("Invalid process on line " + str(lineNumber))
                    else:
                        tmp[i] = int(tmp[i])
                procs.append(Process(lineNumber - 1, tmp[0], tmp[1:]))
                lineNumber = lineNumber + 1
        return procs

    @staticmethod
    def parseSchedulerFile(file):
        with open(file) as f:
            lines = [line.rstrip() for line in f]  # Read lines of the file
            algorithm = lines[0]
            if algorithm not in Sim.SCHED_IDS:
                raise ValueError("Invalid Scheduler ID: {}".format(algorithm))
            options = {}
            lineNumber = 1
            for line in lines[1:]:
                split = re.split(r'\s*=\s*', line)
                if len(split) != 2:
                    raise ValueError("Invalid Scheduler option at line " + str(lineNumber))
                value = Sim.checkSchedOption(algorithm, split[0], split[1])
                if value is None:
                    raise ValueError("Invalid Scheduler option at line " + str(lineNumber))
                options[split[0]] = value
                lineNumber = lineNumber + 1
        return (algorithm, options)

    @staticmethod
    def checkSchedOption(algorithm, option, value):
        if algorithm == "FCFS":
            return None
        elif algorithm in ["VRR", "RR"] and option == "quantum" and value.isdigit():
            return int(value)
        elif algorithm == "FEEDBACK":
            if option == "quantum" and value.isdigit():
                return int(value)
            elif option == "num_priorities" and value.isdigit():
                return int(value)
        elif algorithm in ["SPN", "SRT", "HRRN"]:
            if option == "service_given":
                if value == "true":
                    return True
                elif value == "false":
                    return False
            elif option == "alpha":
                try:
                    return float(value)
                except ValueError:
                    return None
        return None

# Assume you parsed process file and stored the result in procs
procs = Sim.parseProcessFile('processes.txt')

sim_fcfs = Sim(procs, FCFS_Scheduler(procs))
sim_fcfs.run()

sim_spn = Sim(procs, SPN_Scheduler(procs))
sim_spn.run()

print("Sim Done")