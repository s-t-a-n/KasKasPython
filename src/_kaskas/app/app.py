import logging

log = logging.getLogger(__name__)
from pathlib import Path
from types import TracebackType
from typing import *
import os
from rich import print
from rich.prompt import Prompt

from platformdirs import user_data_dir
from typer import Typer
import typer
from typing_extensions import Annotated

from _jasjas.jasjas import Jasjas
from _jasjas.utils.singleton import Singleton


def app_author() -> str:
    return "s-t-a-n"


def app_name() -> str:
    return "jasjas"


def app_version() -> str:
    return "0.0.0"


def app_powered_by() -> str:
    projects = {
        "tiangolo/typer": "https://github.com/tiangolo/typer",
        "Textualize/rich": "https://github.com/Textualize/rich",
    }

    s = ["Powered by "]

    l = len(projects)
    for index, (project_name, project_url) in enumerate(projects.items()):
        s.append(f"[link={project_url}]{project_name}[/link]")

        if index + 2 < l:
            s.append(", ")
        elif index + 1 != l:
            s.append(" and ")
    s.append(".")
    return "".join(s)


def app_tagline() -> str:
    return f"JasJas API by [red]{app_author()}[/red]. {app_powered_by()}"


def app_line() -> str:
    return f"{app_author()}/{app_name()}({app_version()})"


def app_userdir() -> Path:
    return Path(
        user_data_dir(appname=app_name(), appauthor=app_author(), version=app_version())
    )


def app_banner() -> str:
    return r"""
      ___           ___           ___           ___           ___           ___     
     /__/|         /  /\         /  /\         /__/|         /  /\         /  /\    
    |  |:|        /  /::\       /  /:/_       |  |:|        /  /::\       /  /:/_   
    |  |:|       /  /:/\:\     /  /:/ /\      |  |:|       /  /:/\:\     /  /:/ /\  
  __|  |:|      /  /:/~/::\   /  /:/ /::\   __|  |:|      /  /:/~/::\   /  /:/ /::\ 
 /__/\_|:|____ /__/:/ /:/\:\ /__/:/ /:/\:\ /__/\_|:|____ /__/:/ /:/\:\ /__/:/ /:/\:\
 \  \:\/:::::/ \  \:\/:/__\/ \  \:\/:/~/:/ \  \:\/:::::/ \  \:\/:/__\/ \  \:\/:/~/:/
  \  \::/~~~~   \  \::/       \  \::/ /:/   \  \::/~~~~   \  \::/       \  \::/ /:/ 
   \  \:\        \  \:\        \__\/ /:/     \  \:\        \  \:\        \__\/ /:/  
    \  \:\        \  \:\         /__/:/       \  \:\        \  \:\         /__/:/   
     \__\/         \__\/         \__\/         \__\/         \__\/         \__\/    """[
           1:
           ]


def app_banner_filtered() -> str:
    s = app_banner()
    s_split = s.split(sep="\n")

    colours = ["bold red", "bold blue", "bold green"]
    colours_index = 0

    s_new = []
    for s in s_split:
        new = f"[{colours[colours_index]}]{s}[/{colours[colours_index]}]"
        s_new.append(new)

        colours_index += 1
        if colours_index == len(colours):
            colours_index = 0
    return "\n".join(s_new)


def app_banner_length() -> int:
    return len(app_banner().split("\n")[0])


def app_header_centered(columns: int) -> str:
    if app_banner_length() > columns:
        return ""

    extra_spaces = int((columns - app_banner_length()) / 2)
    s = []
    for line in app_banner_filtered().split("\n"):
        w_extra = " " * extra_spaces + line + " " * extra_spaces
        s.append(w_extra)
    centered_banner = "\n".join(s)

    centered_line = " " * extra_spaces + "-" * app_banner_length() + " " * extra_spaces

    # extra_spaces = int((columns - len(app_tagline())) / 2)
    centered_tag_line = " " * extra_spaces + app_tagline() + " " * extra_spaces

    return centered_banner + "\n" + centered_line + "\n" + centered_tag_line + "\n"


def app_header() -> str:
    import sys

    is_interactive = sys.stdout.isatty()
    if not is_interactive:
        return ""

    columns, lines = os.get_terminal_size()

    s = "\b"
    if columns > app_banner_length():
        s += app_banner_filtered()
        s += "\n "
        # s += "-" * app_banner_length()
        s += "\n"
    s += app_tagline()
    return s


def inject_jasjas(app: typer.Typer, kk: Jasjas):
    """Inject all typer entrypoints."""

    from rich.console import Console

    output_console = Console()
    logging_console = Console(stderr=True)

    @app.command("prompt")
    def prompt(
            request: Annotated[Optional[str], typer.Argument(..., help="Module:Command:Optional[Argument]")] = None,
    ):
        """[blue]Set[/blue] a value for a key."""

        def print_help():
            print(f"Request should be formatted as 'MODULE:COMMAND:ARG|ARG'")

        print("JasJas prompt. Enter 'q' to quit");
        while (input := Prompt.ask("$")) != "q":
            if not isinstance(input, str):
                print_help()
                continue
            args = input.split(":")
            if len(args) < 2:
                print_help()
                continue
            response = kk.api.request(args[0], args[1], *args[2:])
            print(response)

        logging_console.print("[bold green]ok")

    @app.command("daemon")
    def start_daemon():
        """[blue]Set[/blue] a value for a key."""
        logging_console.print("[bold green]ok")


class Application(metaclass=Singleton):
    _jasjas: Jasjas

    def __init__(self, root: Path = app_userdir(), loglevel: str = "WARNING"):
        self.setup_logging(loglevel)
        self._jasjas = Jasjas(root=root)

    @staticmethod
    def setup_logging(loglevel: str):
        import logging
        import os

        logging.basicConfig(level=os.environ.get("LOGLEVEL", loglevel))

    @property
    def _typer_app(self) -> Typer:
        app = Typer(no_args_is_help=True, help=app_header(), rich_markup_mode="rich")
        inject_jasjas(app=app, kk=self._jasjas)
        return app

    def run(self):
        """Run the application"""

        if logging.getLogger().level in [logging.DEBUG, logging.INFO]:
            import sys

            sys.tracebacklimit = 0

        app = self._typer_app

        try:
            exit(app())
        except Exception as e:
            import sys

            exception_type, exception_value, exception_traceback = sys.exc_info()
            exception = e

        if exception:
            if logging.getLogger().level in [logging.DEBUG, logging.INFO]:
                raise exception_value.with_traceback(exception_traceback)
            else:

                def tb_info(tb):
                    while tb.tb_next:
                        tb = tb.tb_next

                    return {
                        "filename": tb.tb_frame.f_code.co_filename,
                        "lineno": tb.tb_lineno,
                    }

                traceback = tb_info(exception_traceback)

                from rich.console import Console

                console = Console(stderr=True)
                console.print(
                    f"\n{traceback['filename']}@{traceback['lineno']}: [bold red]ko[default] by [cyan]{exception_type.__name__}[default]: {exception}"
                )
            exit(1)
