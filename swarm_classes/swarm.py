#Max Coursey, Craig Topham Vanderbilt Networking
#Sources used
#https://tellopilots.com/wiki/protocol/
#https://github.com/hanyazou/TelloPy
#https://pypi.org/project/easytello/
#https://tello.oneoffcoder.com/
#https://github.com/dji-sdk/Tello-Python

import time
from tello_mgr import *
import queue
import traceback
import os
from contextlib import suppress

class SwarmProcessing(object):
    #Creates list of thread pools for each drone, checks thread queue

    @staticmethod
    #Creates queue for thread pools for each drone (num)
    def create_threadpool_queue(swarm_num):
        return [queue.Queue() for x in range(swarm_num)]

    @staticmethod
    #gets next command from queue sends to each respective drone (blocking until resp recvd)
    #takes a tello class object and a threadpool queue
    def drone_handler(tello, queue):
        while True:
            while queue.empty():
                pass
            command = queue.get()
            print("drone_handler - command to send")
            print(command)
            tello.send_command(command)

    @staticmethod
    def check_empty_queue(th_pools):
        
        print("Checking if each queue is empty")
        for queue in th_pools:
            print(queue)
            if not queue.empty():
                print("queue not empty")
                return False
        print("queue is empty")
        return True

    @staticmethod
    def check_cmd_resp_recvd(manager):
        print("checking if all commands recvd resp")
        for log in manager.get_last_logs():
            if not log.got_response():
                print("1+ cmd not responded to")
                return False
        print("all cmds recvd resp")
        return True

    @staticmethod
    def create_dir(dpath):
        #creates saved log directory
        if not os.path.exists(dpath):
            with suppress(Exception):
                os.makedirs(dpath)

    @staticmethod
    def save_log(manager):
        dpath = './log'
        SwarmProcessing.create_dir(dpath)

        start_time = str("DS",time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())))
        fpath = f'{dpath}/{start_time}.txt'

        with open(fpath, 'w') as out:
            log = manager.get_log()
            for cnt, stats in enumerate(log.values()):
                out.write(f'------\nDrone: {cnt + 1}\n')

                s = [stat.get_stats_delimited() for stat in stats]
                s = '\n'.join(s)
                out.write(f'{s}\n')
    @staticmethod
    def check_timeout(start_time, end_time, timeout):
        #check if duration of cmd is longer than max timeout
        diff = end_time - start_time
        time.sleep(0.1)
        return diff > timeout

class Swarm(object):
    def __init__(self, fpath):
        self.fpath = fpath
        self.commands = self._get_commands(fpath)
        self.manager = TelloMgr()
        self.tellos = []
        self.pools = []
        self.id_getip = {
            #NEED TO MANUALLY UPDATE 
             0: '192.168.0.101',
             1 : '192.168.0.102',
             2: '192.168.3.104'}
        
        self.ip_getid = {
            #NEED TO MANUALLY UPDATE 
             '192.168.0.101' : 0,
             '192.168.0.102' : 1,
             '192.168.3.104' : 2}

    def start(self):
        #main start func
        def is_invalid_command(command):
            #make a little more robust to handle bad txt files
            if command is None:
                return True
            c = command.strip()
            if len(c) == 0:
                return True
            if c == '':
                return True
            if c == '\n':
                return True
            return False
        
        try:
            print('swarm - start - try - print self.commands\n')
            print(self.commands)
            for command in self.commands:
                if is_invalid_command(command):
                    continue
                print(command)
                command = command.rstrip()

                elif 'scan' in command:
                    self._handle_scan(command)
                elif 'battery?' in command:
                    self._handle_battery_check(command)
                elif '=' in command:
                    self._handle_cmd(command)
            
            self._wait_emptyqueue_and_allresp_recvd()
        except KeyboardInterrupt as kb_interrupt:
            self._handle_keyboard_interrupt()
        except Exception as e:
            self._handle_exception(e)
            traceback.print_exc()
        finally:
            SwarmProcessing.save_log(self.manager)

    def _wait_emptyqueue_and_allresp_recvd(self):
        print("waiting empty queue")
        print(f'Length of queue {len(self.pools)}')
        while not SwarmProcessing.check_empty_queue(self.pools):
            time.sleep(0.5)
        
        time.sleep(1)
        
        print("queue is empty - wait for all cmd resps")
        while not SwarmProcessing.check_cmd_resp_recvd(self.manager):
            time.sleep(0.5)
        print("all cmds recvd resp")
        
    def _get_commands(self, fpath):
        with open(fpath, 'r') as f:
            return f.readlines()

    def _handle_scan(self, command):
        n_tellos = int(command.partition('scan')[2])
        print('number of tellos')
        print(n_tellos)
        self.manager.setup_cmd_drones
        self.tellos = self.manager.get_tello_list()
        self.pools = SwarmProcessing.create_execution_pools(n_tellos)

        for x, (tello, pool) in enumerate(zip(self.tellos, self.pools)):
            self.ip_getid[tello.tello_ip] = x
            t = Thread(target=SwarmProcessing.drone_handler, args=(tello, pool))
            t.daemon = True
            t.start()

            print(f'Scanning Drone IPs = {tello.tello_ip}, ID = {x}')

    def _handle_battery_check(self, command):
        #number threshold for battery % good check
        threshold = int(command.partition('battery?')[2])
        for queue in self.pools:
            queue.put('battery?')
            print(queue.get())

        print("batt check")
        print(self.tellos)
        self._wait_emptyqueue_and_allresp_recvd()
        is_low = False

        for log in self.manager.get_last_logs():
            print("BC - print log")
            print(log.response)
            print(log)
            battery = int(log.response)
            drone_ip = log.drone_ip
            print(f'Battery Status IP = {drone_ip}, batt% = {battery}%')
            if battery < threshold:
                is_low = True
        
        if is_low:
            raise Exception('Drone has low battery')
        else:
            print('Drone Batteries exceed threshold')

    def _handle_cmd(self, command):
        id_list = []
        id = command.partition('>')[0]

        if id == '*':
            id_list = [t for t in range(len(self.tellos))]
        else:
            id_list.append(int(id)-1) 
        
        cmd = str(command.partition('=')[2])

        for tello_id in id_list:
            ip = self.id_getip[tello_id]
            self.pools[tello_id].put(action)
            print(f'IP = {ip}: CMD = {cmd}')

    def _handle_keyboard_interrupt(self):
        print('Interrupt Progam. Land cmds being sent to each drone')
        tello_ips = self.manager.tello_ip_list
        for ip in tello_ips:
            self.manager.send_command('land', ip)

    def _handle_exception(self, e):
        print(e)
