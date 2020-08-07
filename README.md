#Drone Swarm - Set up and Flight Sequence

##Files
- command_line.py - CLI to import text file with flight sequence commands
- tello_mgr.py - tello object and manager classes to handle drone set up, send commands, receive and parse response, saves logs of commands/responses and attributes of each
- swarm.py - handles command and response processing - use thread pools, blocking on response received, processes commands from text file
- c2.txt - text file containing text commands for drone flight sequence
-->scan x (e.g scan 2, where 2 is the number of drones to include in the swarm
-->battery? y (e.g. battery 50, where 50 is the minimum percentage good of the battery for flight sequence to commence
--> d=command (e.g. d can be * for all drones, 1,2,3,..,n where n is number of drones)
----> command is acceptable string command to be received by drone (e.g. rc 0 0 0 20, takeoff, land, etc.)
----> x=takeoff, 1=rc 0 0 0 20, 2=0 0 0 -20

##Start
-open swarm.py and tello_mgr.py files.
--swarm.py - manually update IP address in the swarm class object file for all drones to potentially use in swarm in 'self.id_getip' and 'self.ip_getid' - need to update ids incrementally too
--tello_mgr.py - manually update IP addresses in field 'self.tello_ip_list'
- navigate to swarm_class directory and run "python command_line.py -f c2.txt"
- 
