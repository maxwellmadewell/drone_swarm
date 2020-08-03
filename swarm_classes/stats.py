from datetime import datetime

class Stats(object):
    
    #class constructor
    def __init__(self, command, id):
        self.command = command
        self.response = None
        self.id = id

        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None
        self.drone_ip = None

    def add_response(self, response, id):
        """
        Updates response state based on drone IP address
        """
        if self.response == None:
            self.response = response
            self.end_time = datetime.now()
            self.duration = (self.end_time-self.start_time).total_seconds()


    def print_stats(self):
        print('\nid: %s' % self.id)
        print('command: %s' % self.command)
        print('response: %s' % self.response)
        print('start time: %s' % self.start_time)
        print('end_time: %s' % self.end_time)
        print('duration: %s\n' % self.duration)

    def got_response(self):
        if self.response is None:
            return False
        else:
            return True
    
    def get_stats(self):
        """
        Gets the statistics.
        :return: Statistics.
        """
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