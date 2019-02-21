#!/usr/bin/python3
import pytest
import mock

import sys
import shutil


@pytest.fixture
def mock_layers():
    sys.modules["charms.layer"] = mock.Mock()
    sys.modules["reactive"] = mock.Mock()


@pytest.fixture
def mock_hookenv_config(monkeypatch):
    import yaml

    def mock_config():
        cfg = {}
        yml = yaml.load(open('./config.yaml'))

        # Load all defaults
        for key, value in yml['options'].items():
            cfg[key] = value['default']

        return cfg

    monkeypatch.setattr('libdup.hookenv.config', mock_config)


@pytest.fixture
def mock_github(monkeypatch):
    asset = mock.Mock()
    asset.name = 'Test-Asset-Name.deb'
    asset.browser_download_url = 'Test-Download-URL'
    release = mock.Mock()
    release.title = 'Test-Release-Title'
    release.get_assets.return_value = [asset, ]
    repo = mock.Mock()
    repo.get_releases.return_value = [release, ]
    github = mock.Mock()
    github.get_repo = mock.Mock(return_value=repo)
    monkeypatch.setattr('libdup.Github', mock.Mock(return_value=github))


@pytest.fixture
def dh(tmpdir, mock_layers, mock_hookenv_config, monkeypatch,
       mock_github):
    from libdup import DuplicatiHelper
    dh = DuplicatiHelper()

    # Set correct charm_dir
    monkeypatch.setattr('libdup.hookenv.charm_dir', lambda: '.')

    # Patch the config file to a tmpfile
    config_file = tmpdir.join("duplicati")
    dh.config_file = config_file.strpath

    # Copy example config into tmp location
    shutil.copyfile('./tests/unit/duplicati', dh.config_file)

    # Any other functions that load DH will get this version
    monkeypatch.setattr('libdup.DuplicatiHelper', lambda: dh)

    return dh
