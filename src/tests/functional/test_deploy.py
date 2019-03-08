import os
import pytest
import subprocess
# from juju.model import Model

# Treat tests as coroutines
pytestmark = pytest.mark.asyncio

juju_repository = os.getenv('JUJU_REPOSITORY', '.').rstrip('/')
series = ['xenial',
          'bionic',
          pytest.param('cosmic', marks=pytest.mark.xfail(reason='canary')),
          ]
sources = [('local', '{}/builds/duplicati'.format(juju_repository)),
           ('jujucharms', 'cs:~chris.sanders/duplicati'),
           ]


@pytest.fixture(params=series)
def series(request):
    return request.param


@pytest.fixture(params=sources, ids=[s[0] for s in sources])
def source(request):
    return request.param


# @pytest.fixture
# async def model():
#     model = Model()
#     await model.connect_current()
#     yield model
#     await model.disconnect()


# @pytest.fixture(params=series)
@pytest.fixture
async def app(model, series, source):
    return model.applications['duplicati-{}-{}'.format(series, source[0])]


async def test_duplicate_deploy(model, series, source):
    # Starts a deploy for each series and source
    subprocess.check_call(['juju',
                           'deploy',
                           source[1],
                           '-m', model.info.name,
                           'duplicati-{}-{}'.format(series, source[0]),
                           ])

    # await model.deploy(source[1],
    #                    series=series,
    #                    application_name='duplicati-{}-{}'.format(series,
    #                                                              source[0],
    #                                                              ))


async def test_haproxy_deploy(model):
    await model.deploy('cs:~pirate-charmers/haproxy',
                       series='xenial',
                       application_name='haproxy')


async def test_charm_upgrade(model, app):
    if app.name.endswith('local'):
        pytest.skip("No need to upgrade the local deploy")
    # await model.block_until(lambda: app.status == 'active')
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle')
    # await app.upgrade_charm(switch=sources[0][1]) # Not Implemented yet
    subprocess.check_call(['juju',
                           'upgrade-charm',
                           '--switch={}'.format(sources[0][1]),
                           '-m', model.info.name,
                           app.name,
                           ])
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'executing')
    await model.block_until(lambda: unit.agent_status == 'idle')


async def test_duplicati_status(app, model):
    # Verifies status for all deployed series of the charm
    await model.block_until(lambda: app.status == 'active')


async def test_haproxy_status(model):
    haproxy = model.applications['haproxy']
    await model.block_until(lambda: haproxy.status == 'active')


async def test_add_reverse_proxy(model, app):
    haproxy = model.applications['haproxy']
    await app.set_config({'proxy-url': app.name,
                          'proxy-port': '80'})
    await app.add_relation('reverseproxy', 'haproxy:reverseproxy')
    await model.block_until(lambda: haproxy.status == 'maintenance')
    await model.block_until(lambda: haproxy.status == 'active')


# async def test_example_action(units):
#     for unit in units:
#         action = await unit.run_action('example-action')
#         action = await action.wait()
#         assert action.status == 'completed'
