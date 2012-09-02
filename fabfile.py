from fabric.api import env, cd, sudo, run

env.hosts = ['sites.lolnet.lan']


def deploy():
    with cd('/home//www/ihatemoney.org/code'):
        sudo('git pull', user="www-data")
    sudo('supervisorctl restart ihatemoney.org')


def whoami():
    run('/usr/bin/whoami')
