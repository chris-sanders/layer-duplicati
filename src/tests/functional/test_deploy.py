import os
import pytest
from juju.model import Model

# Treat tests as coroutines
pytestmark = pytest.mark.asyncio

series = ['xenial', 'bionic']
juju_repository = os.getenv('JUJU_REPOSITORY', '.').rstrip('/')


@pytest.fixture
async def model():
    model = Model()
    await model.connect_current()
    yield model
    await model.disconnect()


@pytest.fixture
async def apps(model):
    apps = []
    for entry in series:
        app = model.applications['duplicati-{}'.format(entry)]
        apps.append(app)
    return apps


@pytest.fixture
async def units(apps):
    units = []
    for app in apps:
        units.extend(app.units)
    return units


@pytest.mark.parametrize('series', series)
async def test_duplicate_deploy(model, series):
    # Starts a deploy for each series
    await model.deploy('{}/builds/duplicati'.format(juju_repository),
                       series=series,
                       application_name='duplicati-{}'.format(series))


async def test_sftp_deploy(model):
    await model.deploy('cs:~chris.sanders/sftp-server',
                       series='xenial',
                       application_name='sftp-server',
                       config={'sftp-config': 'sftpuser,/tmp:tmp;'}
                       )


async def test_duplicati_status(apps, model):
    # Verifies status for all deployed series of the charm
    for app in apps:
        await model.block_until(lambda: app.status == 'active')


async def test_sftp_status(model):
    sftp_server = model.applications['sftp-server']
    await model.block_until(lambda: sftp_server.status == 'active')


async def test_backup(model, apps, units):
    sftp_server = model.applications['sftp-server']
    for unit in sftp_server.units:
        action = await unit.run_action('set-password',
                                       user='sftpuser',
                                       password='testpass')
        action = await action.wait()
    public_address = sftp_server.units[0].public_address
    for app in apps:
        config = {'storage-url': 'ssh://sftpuser:testpass@{}/tmp/{}'.format(public_address,
                                                                            app.name),
                  'source-path': '/home/ubuntu/',
                  'options': '--ssh-accept-any-fingerprints',
                  }
        await app.set_config(config)
    for unit in units:
        action = await unit.run_action('backup')
        action = await action.wait()
        assert action.status == 'completed'
        assert action.results['outcome'] == 'success'

# async def test_example_action(units):
#     for unit in units:
#         action = await unit.run_action('example-action')
#         action = await action.wait()
#         assert action.status == 'completed'
