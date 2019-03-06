import fileinput

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

    def write_config(self):
        options = []
        options.append('--webservice-port={}'.format(self.charm_config['port']))
        if self.charm_config['remote-access']:
            options.append('--webservice-interface=any')
        if hookenv.relation_ids('reverseproxy'):
            options.append('--webservice-allowed-hostnames=*')
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
