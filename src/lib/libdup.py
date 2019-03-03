import fileinput
import subprocess

from charmhelpers.core import (
    hookenv,
    host,
)
from github import Github


class DuplicatiHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.config_file = "/etc/default/duplicati"
        self.service = 'duplicati.service'
        self.cli = '/usr/bin/duplicati-cli'

    def write_config(self):
        options = []
        options.append('--webservice-port={}'.format(self.charm_config['port']))
        if self.charm_config['remote-access']:
            options.append('--webservice-interface=any')
        for line in fileinput.input(self.config_file, inplace=True):
            if line.startswith("DAEMON_OPTS"):
                line = 'DAEMON_OPTS="{}"'.format(' '.join(options))
            print(line, end='')
        host.service_restart(self.service)

    def get_release_url(self):
        github = Github()
        releases = github.get_repo('duplicati/duplicati').get_releases()

        latest_release = None
        for release in releases:
            if 'canary' not in release.title:
                latest_release = release
                break
        if not latest_release:
            return None
        for asset in latest_release.get_assets():
            if asset.name.endswith('.deb'):
                return asset.browser_download_url
        return None

    def backup(self):
        cmd = [self.cli,
               'backup',
               self.charm_config['storage-url']]
        cmd.extend([path for path in self.charm_config['source-path'].split(',')])
        cmd.append('--passphrase={}'.format(self.charm_config['passphrase']))
        cmd.extend([option for option in self.charm_config['options'].split(',')])
        try:
            subprocess.check_call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return False
        return True
