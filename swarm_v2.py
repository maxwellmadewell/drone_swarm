import socket
import threading
import time
from stats import Stats


class tello_swarm:
    def __init__(self):
        self.local1_ip=''
        self.local2_ip=''
        self.local1_port = 9010
        self.local2_port = 9011
        self.socket1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket1.bind((self.local1_ip, self.local1_port))
        self.socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket2.bind((self.local2_ip, self.local2_port))

        # thread for receiving cmd ack
        # TODO - will this work for multiple tellos?
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        # IP and port of tello 1 and 2
        self.tello1_ip = '192.168.0.100'
        self.tello2_ip = '192.168.0.101'
        self.tello_port = 8889
        self.tello1_address = (self.tello1_ip, self.tello_port)
        self.tello2_address = (self.tello2_ip, self.tello_port)
        
        # set up log of packets for each drone
        self.log1 = []
        self.log2 = []
        
        # set max time out time
        self.MAX_TIME_OUT = 15.0


    # Send the message to Tello and allow for a delay in seconds
        #TODO - add parameter to differentiate between 1 & 2 tello
    def send_command(self, command):
        """
        Send command to tello IP addresses (1 & 2)
        Block until sent cmd gets ack from both
        if error rcvd or time out - resend cmdn to one or both 
        
        log stats from stats file into log
        """
        #logs commands by ip-address
        #TODO - implement argument to differ between 1 & 2 tello
        self.log.append(Stats(command.encode('utf-8'), self.tello1_address))
        self.log.append(Stats(command.encode('utf-8'), self.tello2_address))
        
        self.sock1.sendto(command.encode(), tello1_address)
        print('Drone1, Sending cmd: %s to %s' % (command, self.tello1_ip))

        self.sock2.sendto(command.encode(), tello2_address)
        print('Drone2, Sending cmd: %s to %s' % (command, self.tello2_ip))
        
        start = time.time()
        
      # Try to send the message otherwise print the exception
        #need to differentiate between last response for each drone
        while not self.log1[-1].got_response():
            now1 = time.time()
            diff1 = now1 - start
            if diff1 > self.MAX_TIME_OUT:
                print('Drone 2 - Max timeout exceeded... command %s' % command)
                return
        print('Succcess, Drone 1 - sent command: %s to %s' % (command, self.tello1_ip))

          
        while not self.log2[-1].got_response():
            now2 = time.time()
            diff2 = now2 - start
            if diff2 > self.MAX_TIME_OUT:
                print 'Drone 2 - Max timeout exceeded... command %s' % command
        print 'Succcess, Drone 2 - sent command: %s to %s' % (command, self.tello2_ip)

    # Receive the message from Tello
    def _receive_thread(self):
        """
        Listen for responses from drones
        
        sets self.response to response received from each drone
        """
      # Continuously loop and listen for incoming messages
      while True:
        # Try to receive the message otherwise print the exception
        try:
            #TODO recvfrom default blocks - do we need two separate threads?
          self.response1, ip1_address = sock1.recvfrom(128)
          print("Received message: from Tello EDU #1: " + self.response1.decode(encoding='utf-8'))
          self.log1[-1].add_response(self.response1)
          
          self.response2, ip2_address = sock2.recvfrom(128)
          print("Received message: from Tello EDU #2: " + self.response2.decode(encoding='utf-8'))
          self.log2[-1].add_response(self.response2)
          
          #TODO - update state to show each command has received cmd ack
          
        except Exception as e:
          # If there's an error close the socket and break out of the loop
          sock1.close()
          sock2.close()
          print("Error receiving: " + str(e))
          break

# Create and start a listening thread that runs in the background
# This utilizes our receive functions and will continuously monitor for incoming messages
receiveThread = threading.Thread(target=receive)
receiveThread.daemon = True
receiveThread.start()

# Each leg of the box will be 100 cm. Tello uses cm units by default.
box_leg_distance = 20

# Yaw 90 degrees
yaw_angle = 90

# Yaw clockwise (right)
yaw_direction = "cw"

# Put Tello into command mode
send("command", 3)

# Send the takeoff command
send("takeoff", 2)

send("back 20", 4)

# Loop and create each leg of the box
for i in range(4):
  # Fly forward
  send("forward " + str(box_leg_distance), 4)
  # Yaw right
  send("cw " + str(yaw_angle), 3)

# Land
send("land", 2)

# Print message
print("Mission completed successfully!")

# Close the socket
sock1.close()
#sock2.close()