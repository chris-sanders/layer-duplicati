#!/usr/bin/python3


def test_pytest():
    assert True


def test_dh(dh):
    ''' See if the dh fixture works to load charm configs '''
    assert isinstance(dh.charm_config, dict)


def test_write_config(dh):
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


def test_get_release_url(dh):
    download_url = dh.get_release_url()
    print(download_url)
    assert download_url == 'Test-Download-URL'


def test_action_backup(dh, mock_check_output):
    dh.charm_config['passphrase'] = 'passphrase'
    dh.charm_config['storage-url'] = 'ssh://test:test@127.0.0.1/backup'
    dh.charm_config['source-path'] = '/test1,/test2,/test3'
    dh.charm_config['options'] = '--accept-all-keys,--my-other-option'
    dh.backup()
    expected_args = ['/usr/bin/duplicati-cli',
                     'backup',
                     'ssh://test:test@127.0.0.1/backup',
                     '/test1',
                     '/test2',
                     '/test3',
                     '--passphrase=passphrase',
                     '--accept-all-keys',
                     '--my-other-option']
    mock_check_output.assert_called_with(expected_args, stderr=-2)
