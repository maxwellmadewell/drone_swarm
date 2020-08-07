#Max Coursey, Craig Topham Vanderbilt Networking
#Sources used
#https://tellopilots.com/wiki/protocol/
#https://github.com/hanyazou/TelloPy
#https://pypi.org/project/easytello/
#https://tello.oneoffcoder.com/
#https://github.com/dji-sdk/Tello-Python

import socket
import time
import threading
from datetime import datetime
from collections import defaultdict

class Tello(object):
    def __init__(self, tello_ip, tello_mgr):
        self.tello_ip = tello_ip
        self.tello_mgr = tello_mgr

    def send_command(self, command):
        return self.tello_mgr.send_command(command, self.tello_ip)

class TelloMgr(object):
    
    def __init__(self):
        self.local_ip=''
        self.local_port = 9010
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.local_ip, self.local_port))
        # thread for receiving cmd ack
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        #Setup list of drone IP addresses 
        #Need to manually match up with swarm.py file
        self.tello_ip_list = ['192.168.0.101', '192.168.0.102']
        #list of tello class objects after receiving first OK response from command cmd
        self.tello_list = []
        self.log = defaultdict(list)
        #Drone times outs if no cmd received after 15 sec.
        self.MAX_TIME_OUT = 10.0
        self.last_response_idx = {}
        self.str_cmd_idx = {}


    def setup_cmd_drones(self):
        "iterates through tellos and sends initial 'command' cmd"
        self.tello_list.append(Tello("192.168.0.101", self))
        self.tello_list.append(Tello("192.168.0.102", self))
        print("tello obj list setup-cmd-drones")
        print(self.tello_list)
        for ip in self.tello_ip_list:
            cmd_id = len(self.log[ip])
            self.log[ip].append(Stats('command', cmd_id))
            print("setup cmd drones (find avail)")
            print(self.log)
            #StateSnapshot
            #{'192.168.0.101': [{'cmd': 'command', 'id': 0}], '192.168.0.100': [{'cmd': 'command', 'id': 0}]})
            try:
                self.socket.sendto(b'command',(ip, 8889))#TODO - what is up and port??
            except:
                print(f'Error setting up socket: {ip}:8889')
                pass

    def get_tello_list(self):
        return self.tello_list
    
    def send_command(self, command, ip):
        #TODO - option to send single/multi commands?
        
        #single command
        self.socket.sendto(command.encode('utf-8'), (ip, 8889))
        print(f'Command: {command} sent to IP:{ip}')
        
        self.log[ip].append(Stats(command, len(self.log[ip])))
        #State snapshot send one takeoff command to IP..101
        #{'192.168.0.101': [{'cmd': 'command', 'id': 0}, {'cmd': 'takeoff', 'id': 1}], '192.168.0.100': [{'cmd': 'command', 'id': 0}]})
        start = time.time()
        
        #checks if stat.add_response func was called from _receive_thread below
        #Blocks until resposne received or time out exceeded for each command
        #checks last command in the log (default dict) for a certain IP
        while not self.log[ip][-1].got_response():
            now = time.time()
            diff = now - start
            if diff > self.MAX_TIME_OUT:
                print(f'Error: Timeout Exceeded:  Command: {command}  IP:{ip}')
                return
    
    def _receive_thread(self):
        while True:
            try:
                #response is data section of packet
                response, ip = self.socket.recvfrom(1024)
                response = response.decode('utf-8')
                self.response = response
                
                ip = ''.join(str(ip[0]))
                
                #assuming tello_ip_list is static and confirmed
                if self.response.upper() == "OK": #and ip not in self.tello_ip_list
                    #no need to add new IPs
                    #self.tello_ip_list.append(ip)
                    #100 indicates OK and to continue (http)
                    self.last_response_idx[ip] = 100
                    self.tello_list.append(Tello(ip, self))
                    self.str_cmd_index[ip] = 1
                
                #TODO -  confirm single/multi response/command item
                # print(f'[SINGLE_RESPONSE], IP={ip}, RESPONSE={self.response}')

                #adds packet data to last send command in log dictionary
                #udpated response flags send command func to finish
                self.log[ip][-1].add_response(self.response, ip)
                
                         
            except socket.error as exc:
                # swallow exception
                print("socket.error : %s\n" % exc)
                pass
            
    def get_log(self):
        return self.log

    def get_last_logs(self):
        print("mgr - get last log")
        print(self.log.values())
        return [log[-1] for log in self.log.values()]

class Stats(object):

    def __init__(self, command, id):
        self.command = command
        self.response = None
        self.id = id

        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None
        self.drone_ip = None

    def add_response(self, response, ip):
        if self.response == None:
            self.response = response
            self.end_time = datetime.now()
            self.duration = self.get_duration()
            self.drone_ip = ip

    def get_duration(self):
        diff = self.end_time - self.start_time
        return diff.total_seconds()

    def print_stats(self):
        print(self.get_stats())

    def got_response(self):
        return False if self.response is None else True

    def get_stats(self):
        return {
            'id': self.id,
            'command': self.command,
            'response': self.response,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration
        }

    def get_stats_delimited(self):
        stats = self.get_stats()
        keys = ['id', 'command', 'response', 'start_time', 'end_time', 'duration']
        vals = [f'{k}={stats[k]}' for k in keys]
        vals = ', '.join(vals)
        return vals

    def __repr__(self):
        return self.get_stats_delimited()
