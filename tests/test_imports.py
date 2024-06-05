import os
import sys
import importlib

def test_imports():
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    sys.path.insert(0, src_dir)  # Add src directory to Python path
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                module_name = os.path.splitext(os.path.relpath(os.path.join(root, file), src_dir))[0].replace(os.path.sep, '.')
                importlib.import_module(module_name)
