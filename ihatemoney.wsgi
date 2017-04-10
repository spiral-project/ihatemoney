import sys
import os

__HERE__ = os.path.dirname(os.path.abspath(__file__))

# Add the budget directory to the path so we can then import from run
sys.path.insert(0, os.path.join(__HERE__, 'budget'))

from run import app as application
