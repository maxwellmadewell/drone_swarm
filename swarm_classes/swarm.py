import time
from tello_mgr import *
import queue
import traceback
import os
from contextlib import suppress

class SwarmUtil(object):
    #Creates list of thread pools for each drone, checks thread queue

    @staticmethod
    #Creates queue for thread pools for each drone (num)
    def create_execution_pools(num):
        return [queue.Queue() for x in range(num)]

    @staticmethod
    #gets next command from queue sends to each respective drone (blocking until resp recvd)
    def drone_handler(tello, queue):
        while True:
            while queue.empty():
                pass
            command = queue.get()
            print("drone_handler - command to send")
            print(command)
            tello.send_command(command)

    @staticmethod
    def all_queue_empty(pools):
        
        print("Checking if each queue is empty")
        for queue in pools:
            print(queue)
            if not queue.empty():
                print("queue not empty")
                return False
        print("queue is empty")
        return True

    @staticmethod
    def all_got_response(manager):
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
        SwarmUtil.create_dir(dpath)

        start_time = str(time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())))
        fpath = f'{dpath}/{start_time}.txt'

        with open(fpath, 'w') as out:
            log = manager.get_log()
            for cnt, stats in enumerate(log.values()):
                out.write(f'------\nDrone: {cnt + 1}\n')

                s = [stat.get_stats_delimited() for stat in stats]
                s = '\n'.join(s)

                out.write(f'{s}\n')

        print(f'[LOG] Saved log files to {fpath}')

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
        self.sn2ip = {
            '0TQZGANED0021X': '192.168.0.101',
            '0TQZGANED0020C': '192.168.0.102',
            '0TQZGANED0023H': '192.168.3.104'
        }
        self.id2sn = {
            0: '0TQZGANED0021X',
            1: '0TQZGANED0020C',
            2: '0TQZGANED0023H'
        }
        self.ip2id = {
            '192.168.0.101': 0,
            '192.168.3.102': 1,
            '192.168.3.104': 2
        }

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

                if '//' in command:
                    self._handle_comments(command)
                elif 'scan' in command:
                    self._handle_scan(command)
                elif '>' in command:
                    self._handle_gte(command)
                elif 'battery_check' in command:
                    self._handle_battery_check(command)
                elif 'delay' in command:
                    self._handle_delay(command)
                elif 'correct_ip' in command:
                    self._handle_correct_ip(command)
                elif '=' in command:
                    self._handle_eq(command)
                elif 'sync' in command:
                    self._handle_sync(command)
            
            self._wait_for_all()
        except KeyboardInterrupt as ki:
            self._handle_keyboard_interrupt()
        except Exception as e:
            self._handle_exception(e)
            traceback.print_exc()
        finally:
            SwarmUtil.save_log(self.manager)

    def _wait_for_all(self):
        print("waiting on all queue empty ")
        print(f'Length of queue {len(self.pools)}')
        while not SwarmUtil.all_queue_empty(self.pools):
            time.sleep(0.5)
        
        time.sleep(1)
        
        print("queue empty - wait for all got response")
        while not SwarmUtil.all_got_response(self.manager):
            time.sleep(0.5)
        print("all got response")
    def _get_commands(self, fpath):
        with open(fpath, 'r') as f:
            return f.readlines()

    def _handle_comments(self, command):
        print(f'File has comment: {command}')

    def _handle_scan(self, command):
        #number of drones
        n_tellos = int(command.partition('scan')[2])
        print('number of tellos')
        print(n_tellos)
        self.manager.setup_cmd_drones
        self.tellos = self.manager.get_tello_list()
        print('self.tellos')
        print(self.tellos)
        self.pools = SwarmUtil.create_execution_pools(n_tellos)

        for x, (tello, pool) in enumerate(zip(self.tellos, self.pools)):
            self.ip2id[tello.tello_ip] = x

            t = Thread(target=SwarmUtil.drone_handler, args=(tello, pool))
            t.daemon = True
            t.start()

            print(f'Scanning Drone IPs = {tello.tello_ip}, ID = {x}')

    def _handle_gte(self, command):
        id_list = []
        id = command.partition('>')[0]

        if id == '*':
            id_list = [t for t in range(len(self.tellos))]
        else:
            id_list.append(int(id)-1) 
        
        cmd = str(command.partition('>')[2])

        for tello_id in id_list:
            sn = self.id2sn[tello_id]
            ip = self.sn2ip[sn]
            id = self.ip2id[ip]

            self.pools[id].put(action)
            print(f'Drone Cmd: IP = {ip}, ID = {id}, CMD = {cmd}')

    def _handle_battery_check(self, command):
        threshold = int(command.partition('battery_check')[2])
        for queue in self.pools:
            queue.put('battery?')
            print(queue.get())

        print("batt check")
        print(self.tellos)
        self._wait_for_all()
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

    def _handle_delay(self, command):
        delay_time = float(command.partition('delay')[2])
        print (f'Start Delay for {delay_time} second')
        time.sleep(delay_time)  

    def _handle_correct_ip(self, command):
        for queue in self.pools:
            queue.put('sn?') 

        self._wait_for_all()
        
        for log in self.manager.get_last_logs():
            sn = str(log.response)
            tello_ip = str(log.drone_ip)
            self.sn2ip[sn] = tello_ip

            print(f'Drone: SN = {sn}, IP = {tello_ip}')

    def _handle_eq(self, command):
        #ip to Sn mapping
        id = int(command.partition('=')[0])
        sn = command.partition('=')[2]
        ip = self.sn2ip[sn]

        self.id2sn[id-1] = sn
        
        print(f'[IP_SN_ID] IP = {ip}, SN = {sn}, ID = {id}')

    def _handle_sync(self, command):
        timeout = float(command.partition('sync')[2])
        print(f'[SYNC] Sync for {timeout} seconds')

        time.sleep(1)

        try:
            start = time.time()
            
            while not SwarmUtil.all_queue_empty(self.pools):
                now = time.time()
                if SwarmUtil.check_timeout(start, now, timeout):
                    raise RuntimeError('Sync failed since all queues were not empty!')

            print('[SYNC] All queues empty and all commands sent')
           
            while not SwarmUtil.all_got_response(self.manager):
                now = time.time()
                if SwarmUtil.check_timeout(start, now, timeout):
                    raise RuntimeError('Sync failed since all responses were not received!')
            
            print('[SYNC] All response received')
        except RuntimeError:
            print('[SYNC] Failed to sync; timeout exceeded')

    def _handle_keyboard_interrupt(self):
        print('[QUIT_ALL], KeyboardInterrupt. Sending land to all drones')
        tello_ips = self.manager.tello_ip_list
        for ip in tello_ips:
            self.manager.send_command('land', ip)

    def _handle_exception(self, e):

        print(f'[EXCEPTION], {e}')
