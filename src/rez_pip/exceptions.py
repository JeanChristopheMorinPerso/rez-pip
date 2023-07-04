import rich
import rich.console


class RezPipError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    def __rich_console__(
        self, console: rich.console.Console, options: rich.console.ConsoleOptions
    ) -> rich.console.RenderResult:
        yield console.render_str(
            f"[bold]{self.__class__.__module__}.{self.__class__.__name__}[/]: {self.message}"
        )


class PipError(RezPipError):
    pass
