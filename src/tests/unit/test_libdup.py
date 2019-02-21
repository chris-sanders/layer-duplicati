#!/usr/bin/python3


class TestLibDuplicati():

    def test_pytest(self):
        assert True

    def test_dh(self, dh):
        ''' See if the dh fixture works to load charm configs '''
        assert isinstance(dh.charm_config, dict)

    def test_write_config(self, dh):
        # Check default file is blank
        with open(dh.config_file, 'r') as configs:
            assert 'DAEMON_OPTS=""' in configs.read()

        # Check with default configs
        dh.write_config()
        with open(dh.config_file, 'r') as configs:
            assert 'DAEMON_OPTS="--webservice-port=8200 --webservice-interface=any"' in configs.read()

        # Check custom config
        dh.charm_config['port'] = 8400
        dh.charm_config['remote-access'] = False
        dh.write_config()
        with open(dh.config_file, 'r') as configs:
            assert 'DAEMON_OPTS="--webservice-port=8400"' in configs.read()
