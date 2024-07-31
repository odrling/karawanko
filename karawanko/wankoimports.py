#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Annotated, TypedDict

import typer

from karawanko.wankomigrate import KaraberusClient


class ImportData(TypedDict):
    kid: str


def imports(imports_file: Annotated[Path, typer.Argument(file_okay=True, dir_okay=False)], server: str, token: str):
    with imports_file.open() as f:
        mugen_imports: list[ImportData] = json.load(f)

    client = KaraberusClient(server, token)

    for kara in mugen_imports:
        client.mugen_import(kara["kid"])


def main():
    typer.run(imports)


if __name__ == "__main__":
    main()
