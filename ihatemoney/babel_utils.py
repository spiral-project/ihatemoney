from pathlib import Path

from babel.messages.frontend import compile_catalog


def compile_catalogs():
    cmd = compile_catalog()
    cmd.directory = Path(__file__).parent / "translations"
    cmd.statistics = True
    cmd.finalize_options()
    cmd.run()
