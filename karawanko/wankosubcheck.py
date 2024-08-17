#!/usr/bin/env python3
import logging
import pathlib

import typer

from karawanko import wankoparse
from karawanko.wankomigrate import find_files

logger = logging.getLogger(__name__)


def subcheck(dir: pathlib.Path):
    remaining_subtitles: set[pathlib.Path] = set([*dir.glob("**/*.ass"), *dir.glob("**/*.ssa")])
    karas = wankoparse.parse_dir(dir)
    for filename in karas:
        files = find_files(filename)
        if files.sub is not None:
            try:
                remaining_subtitles.remove(files.sub)
            except KeyError:
                logger.warn(f"failed to find corresponding subs for {filename}")

    for rem in remaining_subtitles:
        print(rem)


def main():
    typer.run(subcheck)


if __name__ == "__main__":
    main()
