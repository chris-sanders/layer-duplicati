import os
import socket
import subprocess
import urllib.request

from charms.reactive import when_not, set_state, when_all
from charmhelpers import fetch
from charmhelpers.core import hookenv
from libdup import DuplicatiHelper

dh = DuplicatiHelper()


@when_not('duplicati.installed')
def install_duplicati():
    hookenv.status_set('maintenance', 'installing mono')
    fetch.add_source("deb http://download.mono-project.com/repo/ubuntu stable-{series} main",
                     key="3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF")
    fetch.apt_update()
    fetch.apt_install('mono-devel')

    # Create deb directory
    filepath = './debs'
    try:
        os.mkdir(filepath)
    except OSError as e:
        if e.errno == 17:
            pass

    # Download release
    download_url = dh.get_release_url()
    filename = download_url.split('/')[-1]
    fullpath = os.path.join(filepath, filename)
    if not os.path.isfile(fullpath):
        hookenv.status_set('maintenance', 'downloading duplicati')
        hookenv.log('Downloading duplicati', 'INFO')
        urllib.request.urlretrieve(download_url, fullpath)

    # Install
    hookenv.log('Installing duplicati', 'INFO')
    hookenv.status_set('maintenance', 'installing duplicati')
    fetch.apt_install(fullpath)
    subprocess.check_call(['systemctl', 'enable', dh.service])
    dh.write_config()
    hookenv.status_set('active', 'Duplicati is ready')
    hookenv.open_port(dh.charm_config['port'])
    set_state('duplicati.installed')


@when_all('config.changed.port', 'duplicati.installed')
@when_all('config.changed.remote-access', 'duplicati.installed')
def update_config():
    dh.write_config()


@when_all('reverseproxy.triggered', 'reverseproxy.ready')
@when_not('reverseproxy.configured', 'reverseproxy.departed')
def configure_reverseproxy(reverseproxy, *args):
    hookenv.log("Setting up reverseproxy", "INFO")
    proxy_info = {'urlbase': dh.charm_config['proxy-url'],
                  'subdomain': dh.charm_config['proxy-domain'],
                  'rewrite-path': True,  # Duplicati doesn't handle urlbase
                  'acl-local': dh.charm_config['proxy-private'],
                  'group_id': dh.charm_config['proxy-group'],
                  'external_port': dh.charm_config['proxy-port'],
                  'internal_host': socket.getfqdn(),
                  'internal_port': dh.charm_config['port']
                  }
    reverseproxy.configure(proxy_info)
