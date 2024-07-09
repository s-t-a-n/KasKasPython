# from weakref import WeakValueDictionary
# https://stackoverflow.com/a/43620075


# https://stackoverflow.com/a/6798042
class Singleton(type):
    """Singleton that allows continual reconstruction of a single instance unique to the process"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class FinalSingleton(type):
    """Singleton that allows a single construction of a single instance unique to the process"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]
        else:
            raise RuntimeError(
                "FinalSingleton does not allow multiple construction attempts."
            )
