from pathlib import Path
from typing import *

import tomlkit


def _traverse(tree: List[str], map: Any = None, create: bool = False) -> Any:
    if len(tree) == 0:
        return map

    key = tree.pop(0)
    if key not in map and create:
        map[key] = tomlkit.table()
    return _traverse(tree, map=map[key], create=create)


class _CustomDict(MutableMapping, dict):
    """Pretend to be a builtin dict."""


class TomlConfig(_CustomDict):
    _path: Path
    _map: tomlkit.TOMLDocument = None

    def __init__(self, config_file: Path, create: bool = False):
        self._path = config_file

        if create and not config_file.exists():
            with open(config_file, "x") as f:
                # Create empty file
                pass

        self.reload()

    def has(self, url: str) -> bool:
        try:
            if self[url]:
                # tomlkit has no `has` function?
                pass
            return True
        except KeyError as e:
            return False

    def __iter__(self) -> Iterator[str]:
        return iter(dict.items(self._map))

    def __repr__(self) -> str:
        return str(self._map)

    def __getitem__(self, url: str) -> Union[tomlkit.TOMLDocument, Iterable]:
        tree = url.split("/")
        return _traverse(tree, self._map)

    def __setitem__(self, url: str, value: Any) -> None:
        tree = url.split("/")
        _traverse(tree[:-1], self._map, create=True)[tree[-1]] = value

    def __delitem__(self, key: str) -> None:
        self._map.remove(key)

    def __contains__(self, url: str):
        return self.has(url)

    def reload(self) -> None:
        if not self._path.is_file():
            if self._map is None:
                self._map = tomlkit.TOMLDocument()
            return

        with open(self._path) as fp:
            self._map = tomlkit.load(fp)

    def save(self, sort_keys: bool = False) -> None:
        with open(self._path, "w") as toml_file:
            tomlkit.dump(self._map, toml_file, sort_keys=sort_keys)

    @property
    def path(self) -> Path:
        return self._path.absolute()

    @property
    def toml(self) -> tomlkit.TOMLDocument:
        return self._map
