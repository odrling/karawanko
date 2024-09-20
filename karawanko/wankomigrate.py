import datetime
import json
import logging
import re
from itertools import chain
from pathlib import Path
from typing import Annotated, Literal, NamedTuple, TypedDict

import backoff
import requests
import typer
import yaml

from karawanko.wankoexport import KaraData, Media, WankoExport

logger = logging.getLogger(__name__)


default_backoff = backoff.on_exception(
    backoff.expo,
    (ConnectionError, json.JSONDecodeError),
    max_time=30,
)


class KaraInfo(TypedDict):
    title: str
    title_aliases: list[str]
    authors: list[int]
    artists: list[int]
    source_media: int
    song_order: int
    medias: list[int]
    audio_tags: list[str]
    video_tags: list[str]
    comment: str
    version: str
    language: str


class KaraInfoPut(KaraInfo):
    is_hardsub: bool
    karaoke_creation_time: int


class KaraInfoDB(TypedDict):
    ID: int
    VideoUploaded: bool
    InstrumentalUploaded: bool
    SubtitlesUploaded: bool


class KaraberusClient:
    def __init__(self, server: str, token: str):
        self.server = server
        self.headers = {"Authorization": f"Bearer {token}"}
        self.artists: dict[str, int] = {}
        self.medias: dict[str, int] = {}
        self.authors: dict[str, int] = {}

    def endpoint(self, path: str):
        return f"{self.server}{path}"

    def create_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist")
        body = {"name": name, "additional_names": []}

        if name not in self.artists:
            with requests.post(endpoint, json=body, headers=self.headers) as resp:
                data = resp.json()
                try:
                    self.artists[name] = data["artist"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.artists[name] = self.find_artist(name)

        return self.artists[name]

    def find_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist/search")

        if name not in self.artists:
            with requests.get(endpoint, params={"name": name}, headers=self.headers) as resp:
                data = resp.json()
                self.artists[name] = data["artist"]["ID"]

        return self.artists[name]

    def create_author(self, name: str):
        endpoint = self.endpoint("/api/tags/author")
        body = {"name": name}

        if name not in self.authors:
            with requests.post(endpoint, json=body, headers=self.headers) as resp:
                data = resp.json()
                try:
                    self.authors[name] = data["author"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.authors[name] = self.find_author(name)

        return self.authors[name]

    def find_author(self, name: str):
        endpoint = self.endpoint("/api/tags/author/search")

        if name not in self.authors:
            with requests.get(endpoint, params={"name": name}, headers=self.headers) as resp:
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
            with requests.post(endpoint, json=body, headers=self.headers) as resp:
                data = resp.json()
                try:
                    self.medias[name] = data["media"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    self.medias[name] = self.find_media(name, karaberus_media_type)

        return self.medias[name]

    def find_media(self, name: str, media_type: str):
        endpoint = self.endpoint("/api/tags/media/search")

        if name not in self.medias:
            with requests.get(endpoint, params={"name": name}, headers=self.headers) as resp:
                data = resp.json()
                self.medias[name] = data["media"]["ID"]

        return self.medias[name]

    def to_karaberus_karainfo(self, kara: KaraData, authors_str: list[str]) -> KaraInfo:
        artists = [self.create_artist(a) for a in kara.artists]
        medias = [self.create_media(m) for m in kara.medias]
        source_media = 0 if kara.source_media is None else self.create_media(kara.source_media)
        authors = [self.create_author(a) for a in authors_str]

        audio_tags = kara.audio_tags

        # filter OP/ED/INS video tags
        video_tags = [tag for tag in kara.video_tags if tag not in ("OP", "ED", "INS")]

        if "REMIX" in video_tags:
            video_tags.remove("REMIX")
            audio_tags.append("REMIX")

        if "COVER" in audio_tags:
            audio_tags.remove("COVER")
            audio_tags.append("REMIX")

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
            "video_tags": video_tags,
            "source_media": source_media,
            "title_aliases": kara.title_aliases,
        }

    def create_kara(self, kara: KaraData, authors: list[str]):
        endpoint = self.endpoint("/api/kara")
        body = self.to_karaberus_karainfo(kara, authors)

        with requests.post(endpoint, json=body, headers=self.headers) as resp:
            resp.raise_for_status()
            data = resp.json()
            return data["kara"]["ID"]

    def update_kara_data(self, kara_id: int, kara: KaraData, authors: list[str], creation_time: int, is_hardsub: bool):
        endpoint = self.endpoint(f"/api/kara/{kara_id}")
        karainfo = self.to_karaberus_karainfo(kara, authors)
        body: KaraInfoPut = {"karaoke_creation_time": creation_time, "is_hardsub": is_hardsub, **karainfo}

        with requests.patch(endpoint, json=body, headers=self.headers) as resp:
            resp.raise_for_status()
            resp_data = resp.json()
            if resp_data["kara"]["Hardsubbed"] != is_hardsub:
                raise RuntimeError(f"{resp_data["kara"]["Hardsubbed"]=} != {is_hardsub=}")

            resp_creation_time = datetime.datetime.fromisoformat(resp_data["kara"]["KaraokeCreationTime"]).timestamp()
            if resp_creation_time != creation_time:
                raise RuntimeError(f"{resp_creation_time=} != {creation_time=}")

    @default_backoff
    def upload(self, kara_id, file: Path, file_type: Literal["video", "sub", "inst"]):
        endpoint = self.endpoint(f"/api/kara/{kara_id}/upload/{file_type}")
        logger.info(f"uploading {file}")

        with file.open("rb") as f:
            files = {"file": f}
            with requests.put(endpoint, files=files, headers=self.headers) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"{resp.json()}")

    def get_kara(self, kara_id) -> KaraInfoDB:
        endpoint = self.endpoint(f"/api/kara/{kara_id}")

        with requests.get(endpoint, headers=self.headers) as resp:
            resp.raise_for_status()
            return resp.json()["kara"]

    def get_karas(self) -> list[KaraInfoDB]:
        endpoint = self.endpoint("/api/kara")

        with requests.get(endpoint, headers=self.headers) as resp:
            resp.raise_for_status()
            return resp.json()["Karas"]

    def mugen_import(self, mugen_kid: str):
        endpoint = self.endpoint("/api/mugen")
        data = {"mugen_kid": mugen_kid}

        with requests.post(endpoint, headers=self.headers, json=data) as resp:
            if resp.status_code == 204:
                return
            if resp.status_code == 200:
                return resp.json()["import"]
            else:
                raise RuntimeError(f"{resp.json()}")


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


def migrate_db(export_data: WankoExport, client: KaraberusClient):
    kara_ids: dict[str, int] = {}
    all_karas = chain(export_data.exported.items(), export_data.pandora_box.items())

    for kara, kara_data in all_karas:
        logger.info(f"processing {kara}")
        kara_files = find_files(kara)
        authors: list[str] = []
        creation_time = 0
        is_hardsub = False
        if kara_files.sub is None:
            is_hardsub = True
        else:
            authors = find_authors(kara_files.sub)
            creation_time = int(kara_files.sub.stat().st_mtime)

        kara_id = client.create_kara(kara_data, authors)

        client.update_kara_data(kara_id, kara_data, authors, creation_time, is_hardsub)

        kara_ids[kara] = kara_id

    return kara_ids


def migrate_files(client: KaraberusClient, kara_ids: dict[str, int]):
    karas = {kara["ID"]: kara for kara in client.get_karas()}
    for kara, kara_id in kara_ids.items():
        kara_info = karas[kara_id]
        kara_id = kara_ids[kara]
        kara_files = find_files(kara)
        if not kara_info["VideoUploaded"]:
            client.upload(kara_id, kara_files.video, "video")
        if kara_files.sub is not None and not kara_info["SubtitlesUploaded"]:
            client.upload(kara_id, kara_files.sub, "sub")
        if kara_files.audio is not None and not kara_info["InstrumentalUploaded"]:
            client.upload(kara_id, kara_files.audio, "inst")


def migrate(export: Annotated[Path, typer.Argument(file_okay=True, dir_okay=False)], server: str, token: str):
    client = KaraberusClient(server, token)

    kara_id_dump_file = export.with_suffix(".iddump.json")

    if kara_id_dump_file.exists():
        with kara_id_dump_file.open() as f:
            kara_ids: dict[str, int] = json.load(f)
    else:
        with export.open() as f:
            export_data_obj = yaml.safe_load(f)
            export_data = WankoExport.model_validate(export_data_obj)

        kara_ids = migrate_db(export_data, client)
        with kara_id_dump_file.open("w") as f:
            json.dump(kara_ids, f)

    migrate_files(client, kara_ids)


def link(src: Path, dst: Path) -> None:
    logger.info(f"{src} → {dst}")
    dst.hardlink_to(src)


def migrate_local_files(id_dump: dict[str, int], karaberus_dir: Path):
    karaberus_dir.mkdir(parents=True, exist_ok=True)
    for kara, karaberus_id in id_dump.items():
        kara_files = find_files(kara)
        if kara_files.video.exists():
            link(kara_files.video, karaberus_dir / f"{karaberus_id}.mkv")
        else:
            logger.warning(f"{kara_files.video} not found")

        if kara_files.audio is not None:
            link(kara_files.audio, karaberus_dir / f"{karaberus_id}.mka")
        if kara_files.sub is not None:
            link(kara_files.sub, karaberus_dir / f"{karaberus_id}.ass")


def filemigrate(
    export: Annotated[Path, typer.Argument(file_okay=True, dir_okay=False)],
    karaberus_dir: Annotated[Path, typer.Argument(file_okay=False)],
):
    kara_id_dump_file = export.with_suffix(".iddump.json")

    with kara_id_dump_file.open() as f:
        id_dump: dict[str, int] = json.load(f)
        migrate_local_files(id_dump, karaberus_dir)


def main():
    typer.run(migrate)


def filemigratemain():
    typer.run(filemigrate)


if __name__ == "__main__":
    main()
