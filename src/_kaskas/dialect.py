from enum import Enum, Flag, auto


class Dialect:
    HEADER_API = "@"
    HEADER_LOG = "#"
    HEADER_DEBUG = "!"

    class Operator(Enum):
        REQUEST = ":"
        RESPONSE = "<"
        REQUEST_PRINT_USAGE = "?"
        RESPONSE_FOOTER = ">"
