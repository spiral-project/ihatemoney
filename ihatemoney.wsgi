import sys
import os

__HERE__ = os.path.dirname(os.path.abspath(__file__))

# Wrapper around application to get the env var set by Apache
def application(environ, start_response):
    if environ.get('IHATEMONEY_VENV_PATH'):
        activate_this = os.path.join(environ.get('IHATEMONEY_VENV_PATH'), 'bin/activate_this.py')
        execfile(activate_this, dict(__file__=activate_this))
    # Add the budget directory to the path so we can then import from run
    sys.path.insert(0, os.path.join(__HERE__, 'budget'))
    from run import app as _application
    return _application(environ, start_response)
