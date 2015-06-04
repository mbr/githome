
from click.testing import CliRunner
from githome.cmd import cli
import pytest


@pytest.fixture
def runner():
    return CliRunner()


# the most basic tests tells us whether or not we messed up any dependencies
def test_cli_basic(runner):
    runner.invoke(cli, ['--help'])
