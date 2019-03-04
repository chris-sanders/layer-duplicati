import os
import pytest
import subprocess

# Treat all tests as coroutines
pytestmark = pytest.mark.asyncio

juju_repository = os.getenv('JUJU_REPOSITORY', '.').rstrip('/')
series = ['xenial',
          'bionic',
          # pytest.param('cosmic', marks=pytest.mark.xfail(reason='canary')),
          ]
sources = [('local', '{}/builds/duplicati'.format(juju_repository)),
           # ('jujucharms', 'cs:...'),
           ]


# Uncomment for re-using the current model, useful for debugging functional tests
# @pytest.fixture(scope='module')
# async def model():
#     from juju.model import Model
#     model = Model()
#     await model.connect_current()
#     yield model
#     await model.disconnect()


# Custom fixtures
@pytest.fixture(params=series)
def series(request):
    return request.param


@pytest.fixture(params=sources, ids=[s[0] for s in sources])
def source(request):
    return request.param


@pytest.fixture
async def app(model, series, source):
    app_name = 'duplicati-{}-{}'.format(series, source[0])
    return await model._wait_for_new('application', app_name)


async def test_duplicati_deploy(model, series, source, request):
    # Starts a deploy for each series
    # Using subprocess b/c libjuju fails with JAAS
    # https://github.com/juju/python-libjuju/issues/221
    application_name = 'duplicati-{}-{}'.format(series, source[0])
    cmd = ['juju', 'deploy', source[1], '-m', model.info.name,
           '--series', series, application_name]
    if request.node.get_closest_marker('xfail'):
        cmd.append('--force')
    subprocess.check_call(cmd)


async def test_haproxy_deploy(model):
    await model.deploy('cs:~pirate-charmers/haproxy',
                       series='xenial',
                       application_name='haproxy')


async def test_sftp_deploy(model):
    await model.deploy('cs:~chris.sanders/sftp-server',
                       series='xenial',
                       application_name='sftp-server',
                       config={'sftp-config': 'sftpuser,/tmp:tmp;'}
                       )


async def test_charm_upgrade(model, app):
    if app.name.endswith('local'):
        pytest.skip("No need to upgrade the local deploy")
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle')
    subprocess.check_call(['juju',
                           'upgrade-charm',
                           '--switch={}'.format(sources[0][1]),
                           '-m', model.info.name,
                           app.name,
                           ])
    await model.block_until(lambda: unit.agent_status == 'executing')


# Tests
async def test_duplicati_status(model, app):
    # Verifies status for all deployed series of the charm
    await model.block_until(lambda: app.status == 'active')
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle')


async def test_haproxy_status(model):
    haproxy = model.applications['haproxy']
    await model.block_until(lambda: haproxy.status == 'active')


async def test_sftp_status(model):
    sftp_server = model.applications['sftp-server']
    await model.block_until(lambda: sftp_server.status == 'active')


async def test_add_reverse_proxy(model, app):
    haproxy = model.applications['haproxy']
    await app.set_config({'proxy-url': app.name,
                          'proxy-port': '80'})
    await app.add_relation('reverseproxy', 'haproxy:reverseproxy')
    await model.block_until(lambda: haproxy.status == 'maintenance')
    await model.block_until(lambda: haproxy.status == 'active')


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


async def test_restore(model, apps, units):
    for unit in units:
        action = await unit.run_action('restore')
        action = await action.wait()
        assert action.status == 'completed'
        assert action.results['outcome'] == 'success'
