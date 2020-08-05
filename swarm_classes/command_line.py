import sys
import argparse
from swarm import *

def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--file', 
                        help='Add command text (.txt) file', required=True)
    
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    fpath = args.file

    swarm = Swarm(fpath)
    swarm.start()
