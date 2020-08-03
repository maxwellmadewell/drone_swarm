# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 08:06:32 2020

@author: mxmco
"""


import socket
from stats import Stats
import time
import threading
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
        # TODO - will this work for multiple tellos?
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        #Setup list of drone IP addresses 
        self.tello_ip_list = ['192.168.0.101', '192.168.0.102']
        #list of tello class objects after receiving first OK response from command cmd
        self.tello_list = []
        self.log = defaultdict(list)
        self.MAX_TIME_OUT = 10.0
        self.last_response_idx = {}
        self.str_cmd_idx = {}


    def setup_cmd_drones(self):
        "iterates through tellos and sends initial 'command' cmd"
        for ip in self.tello_ip_list:
            cmd_id = len(self.log[ip])
            self.log[ip].append(Stats('command', cmd_id))
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
        print("Umm - you should never get here")
    
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
                print("[Exception_Error]Caught exception socket.error : %s\n" % exc)
                pass
            
    def get_log(self):
        return self.log

    def get_last_logs(self):
        return [log[-1] for log in self.log.values()]


