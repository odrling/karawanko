import logging
import re
from itertools import chain
from pathlib import Path
from typing import Annotated, Literal, NamedTuple, TypedDict

import requests
import typer
import yaml

from karawanko.wankoexport import KaraData, Media, WankoExport

logger = logging.getLogger(__name__)


class KaraInfo(TypedDict):
    title: str
    title_aliases: list[str]
    authors: list[int]
    artists: list[int]
    source_media: int | None
    song_order: int
    medias: list[int]
    audio_tags: list[str]
    video_tags: list[str]
    comment: str
    version: str
    language: str


class KaraberusClient:
    def __init__(self, server: str, token: str):
        self.server = server
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.artists: dict[str, int] = {}
        self.medias: dict[str, int] = {}
        self.authors: dict[str, int] = {}

    def endpoint(self, path: str):
        return f"{self.server}{path}"

    def create_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist")
        body = {"name": name, "additional_names": []}

        if name not in self.artists:
            with self.session.post(endpoint, json=body) as resp:
                data = resp.json()
                try:
                    self.artists[name] = data["artist"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.artists[name] = self.find_artist(name)

        return self.artists[name]

    def find_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist")

        if name not in self.artists:
            with self.session.get(endpoint, params={"name": name}) as resp:
                data = resp.json()
                self.artists[name] = data["artist"]["ID"]

        return self.artists[name]

    def create_author(self, name: str):
        endpoint = self.endpoint("/api/tags/author")
        body = {"name": name, "additional_names": []}

        if name not in self.authors:
            with self.session.post(endpoint, json=body) as resp:
                data = resp.json()
                try:
                    self.authors[name] = data["author"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.authors[name] = self.find_author(name)

        return self.authors[name]

    def find_author(self, name: str):
        endpoint = self.endpoint("/api/tags/author")

        if name not in self.authors:
            with self.session.get(endpoint, params={"name": name}) as resp:
                data = resp.json()
                self.authors[name] = data["author"]["ID"]

        return self.authors[name]

    def create_media(self, media: Media):
        endpoint = self.endpoint("/api/tags/media")
        karaberus_media_type = media.mtype
        name = media.name
        body = {
            "name": name,
            "media_type": karaberus_media_type,
            "additional_names": [],
        }

        if name not in self.medias:
            with self.session.post(endpoint, json=body) as resp:
                data = resp.json()
                try:
                    self.medias[name] = data["media"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.medias[name] = self.find_media(name, karaberus_media_type)

        return self.medias[name]

    def find_media(self, name: str, media_type: str):
        endpoint = self.endpoint("/api/tags/media")

        if name not in self.medias:
            with self.session.get(endpoint, params={"name": name}) as resp:
                data = resp.json()
                self.medias[name] = data["media"]["ID"]

        return self.medias[name]

    def to_karaberus_karainfo(self, kara: KaraData, authors_str: list[str]) -> KaraInfo:
        artists = [self.create_artist(a) for a in kara.artists]
        medias = [self.create_media(m) for m in kara.medias]
        source_media = None if kara.source_media is None else self.create_media(kara.source_media)
        authors = [self.create_author(a) for a in authors_str]

        return {
            "title": kara.title,
            "medias": medias,
            "artists": artists,
            "authors": authors,
            "comment": kara.comment,
            "version": kara.version,
            "language": kara.language,
            "song_order": kara.song_order,
            "audio_tags": kara.audio_tags,
            "video_tags": kara.video_tags,
            "source_media": source_media,
            "title_aliases": kara.title_aliases,
        }

    def create_kara(self, kara: KaraData, authors: list[str]):
        endpoint = self.endpoint("/api/kara")
        body = self.to_karaberus_karainfo(kara, authors)

        with self.session.post(endpoint, json=body) as resp:
            resp.raise_for_status()
            data = resp.json()
            return data["kara"]["id"]

    def set_creation_time(self, kara_id: int, creation_time: int):
        endpoint = self.endpoint(f"/api/kara/{kara_id}/creation_time")
        body = {"creation_time": creation_time}

        with self.session.post(endpoint, json=body) as resp:
            resp.raise_for_status()

    def upload(self, kara_id, file: Path, file_type: Literal["video", "sub", "inst"]):
        endpoint = self.endpoint(f"/api/kara/{kara_id}/upload/{file_type}")
        with file.open() as f:
            files = {"file": f}
            with self.session.post(endpoint, files=files) as resp:
                resp.raise_for_status()


class KaraFiles(NamedTuple):
    video: Path
    sub: Path | None
    audio: Path | None


def find_files(path_str: str):
    video_file = Path(path_str)
    subtitle_file = None
    audio_file = None

    # we don't seem to have odd casing for extensions
    tmp_subfile = video_file.with_suffix(".ass")
    if tmp_subfile.exists():
        subtitle_file = tmp_subfile
    tmp_subfile = video_file.with_suffix(".ssa")
    if tmp_subfile.exists():
        subtitle_file = tmp_subfile

    if subtitle_file is None:
        logger.info(f"could not find associated subtitle file for {video_file}")

    # afaik there's only the ones I made with mka extension
    tmp_audiofile = video_file.with_suffix(".mka")
    if tmp_audiofile.exists():
        audio_file = tmp_audiofile

    return KaraFiles(video_file, subtitle_file, audio_file)


timing_reg = re.compile(r"^(?:Original Timing|Script Updated By): ([^,\n]*)(?:,.*)?$", re.M)


def find_authors(sub_file: Path):
    with sub_file.open() as f:
        return list(set(timing_reg.findall(f.read(1024))))


def migrate(export: Annotated[Path, typer.Argument(file_okay=True, dir_okay=False)], server: str, token: str):
    client = KaraberusClient(server, token)

    with export.open() as f:
        export_data_obj = yaml.safe_load(f)
        export_data = WankoExport.model_validate(export_data_obj)

    all_karas = chain(export_data.exported.items(), export_data.pandora_box.items())

    for kara, kara_data in all_karas:
        kara_files = find_files(kara)
        authors: list[str] = []
        creation_time = None
        if kara_files.sub is not None:
            authors = find_authors(kara_files.sub)
            creation_time = int(kara_files.sub.stat().st_mtime)

        kara_id = client.create_kara(kara_data, authors)
        client.upload(kara_id, kara_files.video, "video")
        if kara_files.sub:
            client.upload(kara_id, kara_files.sub, "sub")
        if kara_files.audio:
            client.upload(kara_id, kara_files.audio, "inst")

        if creation_time is not None:
            client.set_creation_time(kara_id, creation_time)


def main():
    typer.run(migrate)