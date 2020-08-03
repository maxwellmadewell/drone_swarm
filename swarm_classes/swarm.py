    
import sys
import time
from tello_mgr import *
import queue
import traceback
import os
from contextlib import suppress

class SwarmUtil(object):
    """
    Creates list of thread pools for each drone, checks thread queue
    """

    @staticmethod
    #Creates list of thread pools for each drone
    def create_execution_pools(num):
        return [queue.Queue() for x in range(num)]

    @staticmethod
    #gets next command from queue sends to each respective drone (blocking until resp recvd)
    def drone_handler(tello, queue):
        while True:
            while queue.empty():
                pass
            command = queue.get()
            tello.send_command(command)

    @staticmethod
    def all_queue_empty(pools):
        for queue in pools:
            if not queue.empty():
                return False
        return True

    @staticmethod
    def all_got_response(manager):
        for log in manager.get_last_logs():
            if not log.got_response():
                return False
        return True

    @staticmethod
    def create_dir(dpath):
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
        diff = end_time - start_time
        time.sleep(0.1)
        return diff > timeout

class Swarm(object):
    """  """
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
        """
        Main loop. Starts the swarm.

        :return: None.
        """
        def is_invalid_command(command):
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
        """
        Waits for all queues to be empty and for all responses
        to be received.

        :return: None.
        """
        while not SwarmUtil.all_queue_empty(self.pools):
            time.sleep(0.5)
        
        time.sleep(1)

        while not SwarmUtil.all_got_response(self.manager):
            time.sleep(0.5)

    def _get_commands(self, fpath):
        """
        Gets the commands.

        :param fpath: Command file path.
        :return: List of commands.
        """
        with open(fpath, 'r') as f:
            return f.readlines()

    def _handle_comments(self, command):
        print(f'[COMMENT] {command}')

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

            print(f'[SCAN] IP = {tello.tello_ip}, ID = {x}')

    def _handle_gte(self, command):
        """
        Handles gte or >.

        :param command: Command.
        :return: None.
        """
        id_list = []
        id = command.partition('>')[0]

        if id == '*':
            id_list = [t for t in range(len(self.tellos))]
        else:
            id_list.append(int(id)-1) 
        
        action = str(command.partition('>')[2])

        for tello_id in id_list:
            sn = self.id2sn[tello_id]
            ip = self.sn2ip[sn]
            id = self.ip2id[ip]

            self.pools[id].put(action)
            print(f'[ACTION] SN = {sn}, IP = {ip}, ID = {id}, ACTION = {action}')

    def _handle_battery_check(self, command):
        """
        Handles battery check. Raises exception if any drone has
        battery life lower than specified threshold in the command.

        :param command: Command.
        :return: None.
        """
        threshold = int(command.partition('battery_check')[2])
        for queue in self.pools:
            queue.put('battery?')

        self._wait_for_all()

        is_low = False

        for log in self.manager.get_last_logs():
            battery = int(log.response)
            drone_ip = log.drone_ip

            print(f'[BATTERY] IP = {drone_ip}, LIFE = {battery}%')

            if battery < threshold:
                is_low = True
        
        if is_low:
            raise Exception('Battery check failed!')
        else:
            print('[BATTERY] Passed battery check')

    def _handle_delay(self, command):
        """
        Handles delay.

        :param command: Command.
        :return: None.
        """
        delay_time = float(command.partition('delay')[2])
        print (f'[DELAY] Start Delay for {delay_time} second')
        time.sleep(delay_time)  

    def _handle_correct_ip(self, command):
        """
        Handles correction of IPs.

        :param command: Command.
        :return: None.
        """
        for queue in self.pools:
            queue.put('sn?') 

        self._wait_for_all()
        
        for log in self.manager.get_last_logs():
            sn = str(log.response)
            tello_ip = str(log.drone_ip)
            self.sn2ip[sn] = tello_ip

            print(f'[CORRECT_IP] SN = {sn}, IP = {tello_ip}')

    def _handle_eq(self, command):
        """
        Handles assignments of IDs to serial numbers.

        :param command: Command.
        :return: None.
        """
        id = int(command.partition('=')[0])
        sn = command.partition('=')[2]
        ip = self.sn2ip[sn]

        self.id2sn[id-1] = sn
        
        print(f'[IP_SN_ID] IP = {ip}, SN = {sn}, ID = {id}')

    def _handle_sync(self, command):
        """
        Handles synchronization.

        :param command: Command.
        :return: None.
        """
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
        """
        Handles keyboard interrupt.

        :param command: Command.
        :return: None.
        """
        print('[QUIT_ALL], KeyboardInterrupt. Sending land to all drones')
        tello_ips = self.manager.tello_ip_list
        for ip in tello_ips:
            self.manager.send_command('land', ip)

    def _handle_exception(self, e):
        """
        Handles exception (not really; just logging to console).

        :param command: Command.
        :return: None.
        """
        print(f'[EXCEPTION], {e}')
