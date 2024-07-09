import logging
import os
from typing import *
from pathlib import Path

from _jasjas.streamlit.streamlit_launcher import StreamlitApp
from _jasjas.datacollector import MetricCollector
from _jasjas.jasjas_api import JasJasGrowbed


class Jasjas:
    """ """

    _root_dir: Path

    _webapp: StreamlitApp
    _collector: MetricCollector
    _growbed: JasJasGrowbed

    def __init__(self, root: Path) -> None:
        self._root_dir = root
        self._growbed = JasJasGrowbed()

    @property
    def api(self) -> JasJasGrowbed:
        return self._growbed
