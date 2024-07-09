import logging


log = logging.getLogger(__name__)

from pathlib import Path
from types import ModuleType


# def _add_to_pythonpath(file: Path):
#     """ Add a file to the PYTHONPATH directive, allowing module to do relative imports. """
#     import sys, os
#
#     d = os.path.dirname(os.path.abspath(file))
#     log.debug(f"Adding directory '{d}' to PYTHONPATH for file {file}")
#     sys.path.append(os.path.dirname(d))
#     log.debug(sys.path)


def module_from_file(file: Path) -> ModuleType:
    """Load a module from"""
    import importlib.machinery
    import importlib.util
    import sys

    assert file.exists() and file.is_file(), f"Path '{file}' is not a file"
    assert file.suffix == ".py", f"Path '{file}' is not a Python file"

    module_name = file.stem
    loader = importlib.machinery.SourceFileLoader(module_name, str(file))
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)

    return module
