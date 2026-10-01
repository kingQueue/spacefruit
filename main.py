"""SpaceFruit compatibility entry point.

The application is now organized under the ``spacefruit`` package. This
module re-exports the public classes so existing tests and ``python main.py``
work without changes.
"""

from spacefruit.models import *
from spacefruit.catalog import *
from spacefruit.hardware import *
from spacefruit.recommendations import *
from spacefruit.planner import *
from spacefruit.web import *
from spacefruit.robot import *

def main():
    FarmingRobot().run()

if __name__ == "__main__":
    main()
