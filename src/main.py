from server.instance import server
import sys, os

# Need to import all resources
# so that they register with the server
from resources.v1.auth import *
from resources.v1.send import *
from resources.v1.sentitems import *
from resources.v1.inbox import *
from resources.v1.outbox import *
from resources.logs import *
from resources.errors import *

if __name__ == '__main__':
    server.run()
