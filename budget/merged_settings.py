"""
Merges default settings with user-defined settings
"""

from default_settings import *

try:
    from settings import *
except ImportError:
    pass
