import os.path
import sys

# Add the module path
module_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '..'
))
sys.path.insert(0, module_path)
