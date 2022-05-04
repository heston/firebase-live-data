import os.path
import logging
import sys

# Add the module path
module_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '..'
))
sys.path.insert(0, module_path)

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.DEBUG
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\""
    )
