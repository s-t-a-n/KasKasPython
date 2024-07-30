from _kaskas.log import log

from pathlib import Path
from types import TracebackType
from typing import *
import os
from rich import print
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from platformdirs import user_data_dir
from typer import Typer
import typer
from typing_extensions import Annotated

from _kaskas.daemon import Daemon
from _kaskas.utils.singleton import Singleton


def app_author() -> str:
    return "s-t-a-n"


def app_name() -> str:
    return "kaskas"


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
    return f"KasKas API by [red]{app_author()}[/red]. {app_powered_by()}"


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


def inject_kaskas(app: typer.Typer, daemon: Daemon, progress: Progress):
    """Inject all typer entrypoints."""

    @app.command("prompt")
    def prompt(
            remote: Annotated[bool, typer.Option(help=".")] = False,
            remote_host: Annotated[str, typer.Option(help=".")] = None,
            request: Annotated[str, typer.Argument(help="module:command:arg1|arg2|..")] = None,
    ):
        """[blue]Set[/blue] a value for a key."""

        progress.stop()

        def print_help():
            print(f"Request should be formatted as 'MODULE:COMMAND:ARG|ARG'")

        history = []

        def process_request(input: str):
            if not isinstance(input, str):
                print_help()
                return

            arrow_up_keycode = "\x1b[A"
            if input == arrow_up_keycode:  # redo last command
                input = history[-1]

            components = None

            def process_api_request(input: str):
                components = input.split(":")
                if len(components) < 2:  # not enough components to built request
                    print_help()
                    return
                response = daemon.api.request(module=components[0], command=components[1], args=components[2:])
                print(str(response))
                history.append(input)

            def process_print_usage_request(input: str):
                components = ["?", "", ""]
                response = daemon.api.request(module=components[0], command=components[1], args=components[2:])
                print(response.arguments)
                print(str(response.arguments[0]))

            if input == "?":  # this is a request to print usage
                process_print_usage_request(input)
            else:
                process_api_request(input)

        daemon.launch_api(remote=remote, remote_host=remote_host)

        if request:
            process_request(request)
            daemon.shutdown()
            return

        print("[bold red]KasKas[/bold red] prompt. Enter 'q' to quit, Press ↑ and Enter to repeat last command");

        while (input := Prompt.ask("$")) != "q":
            process_request(input)

    @app.command("daemon")
    def start_daemon(remote: Annotated[bool, typer.Option(help=".")] = False,
                     remote_host: Annotated[str, typer.Option(help=".")] = None, ):
        """[blue]Set[/blue] a value for a key."""

        p = progress.add_task(description="Launching API...", total=None)
        daemon.launch_api(remote=remote, remote_host=remote_host)
        progress.remove_task(p)

        p = progress.add_task(description="Launching collector...", total=None)
        daemon.launch_collector()
        progress.remove_task(p)

        p = progress.add_task(description="Launching web frontend...", total=None)
        daemon.launch_webapp()
        progress.remove_task(p)

        p = progress.add_task(description="KasKas is [bold green]running[/bold green]...", total=None)
        daemon.wait()

    @app.command("user-directory", help="Prints user directory")
    def user_directory():
        print(daemon.root_dir)


class Application(metaclass=Singleton):
    _daemon: Daemon

    _progress: Progress

    def __init__(self, root: Path = app_userdir(), loglevel: str = "WARNING"):
        self.setup_logging(loglevel)

        if not root.exists() or not root.is_dir():
            os.makedirs(root, exist_ok=True)

        self._daemon = Daemon(root=root)

        self._progress = Progress(SpinnerColumn(),
                                  TextColumn("[progress.description]{task.description}"),
                                  transient=True)
        self._progress.start()

        import signal
        import sys

        def signal_handler(sig, frame):
            for t in self._progress.tasks:
                self._progress.remove_task(t.id)

            p = self._progress.add_task(description="KasKas is [bold red]shutting down[/bold red]...", total=None)
            self._daemon.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl-C signal
        signal.signal(signal.SIGTERM, signal_handler)  # Handle termination signal

    @staticmethod
    def setup_logging(loglevel: str):
        pass
        # import logging
        # import os
        # from rich.logging import RichHandler
        #
        # fmt = "%(message)s"
        # loglevel = os.environ.get('LOGLEVEL', loglevel).upper()
        # logging.basicConfig(
        #     level=loglevel, format=fmt, datefmt="[%X]", handlers=[RichHandler()]
        # )

    @property
    def _typer_app(self) -> Typer:
        app = Typer(no_args_is_help=True, help=app_header(), rich_markup_mode="rich")
        inject_kaskas(app=app, daemon=self._daemon, progress=self._progress)
        return app

    def run(self):
        """Run the application"""

        import logging

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
