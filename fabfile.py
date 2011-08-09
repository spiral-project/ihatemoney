from fabric.api import *

env.hosts = ['lolnet.org:20002']
env.shell = "/usr/local/bin/bash -c"
env.path = "/usr/local/bin/:/usr/bin/"

def deploy():
    with cd('/usr/local/www/notmyidea.org/ihatemoney'):
        sudo('git pull', user="www")
    sudo('supervisorctl restart ihatemoney')

def whoami():
    run('/usr/bin/whoami')
