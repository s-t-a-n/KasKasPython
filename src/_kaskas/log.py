import logging
from rich.logging import RichHandler
import os

import os
from rich.logging import RichHandler

fmt = "%(message)s"
loglevel = os.environ.get('LOGLEVEL', 'warning').upper()
logging.basicConfig(
    level=loglevel, format=fmt, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger(__name__)
