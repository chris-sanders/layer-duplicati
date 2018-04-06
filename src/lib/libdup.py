import fileinput

from charmhelpers.core import (
    hookenv,
    host,
)


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
        for line in fileinput.input(self.config_file, inplace=True):
            if line.startswith("DAEMON_OPTS"):
                line = 'DAEMON_OPTS="{}"'.format(' '.join(options))
            print(line, end='')
        host.service_restart(self.service)
