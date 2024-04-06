import unittest
from pathlib import Path

from karawanko.wankoparse import KaraData, parse_file

file_tests: list[tuple[str, KaraData]] = [
    ("Wmusic/Electric Light Orchestra - AMV - Twilight (AMV Daicon Opening Animations).mp4",
     {"title": "Twilight",
      "tags": ["AMV"],
      "media": None,
      "details": [("AMV", "Daicon Opening Animations")],
      "artists": ["Electric Light Orchestra"]}),
    ("Nouveau/Xenoblade Chronicles - ED SPOIL - Beyond the sky (VERS Japanese - VIDEO Ending).mp4",
     {"title": "Beyond the sky",
      "tags": ["ED", "SPOIL"],
      "media": {"name": "Xenoblade Chronicles",
                "media_type": "game"},
      "artists": [],
      "details": [("VERS", "Japanese"),
                  ("VIDEO", "Ending")]
      }),
     ("CJKmusic/GUMI, IA, Luka Megurine - PV - Ifuudoudou.mp4",
      {"title": "Ifuudoudou",
       "tags": ["PV"],
       "media": None,
       "artists": ["GUMI", "IA", "Luka Megurine"],
       "details": []}),
      ("CJKmusic/Camellia, U.Z. INU feat. Houshou Marine - PV NSFW - I’m Your Treasure Box ＊Anata wa Marine Senchou Otakarabako Kara Mitsuketa..mp4",  # noqa: E501
       {"title": "I’m Your Treasure Box ＊Anata wa Marine Senchou Otakarabako Kara Mitsuketa.",
        "tags": ["PV", "NSFW"],
        "media": None,
        "artists": ["Camellia", "U.Z. INU feat. Houshou Marine"],
        "details": []}),
       ("base/Mugen/CJKmusic/Arai Yumi - PV - Hikoukigumo (AMV Kaze Tachinu - AMV Le Vent se lève).mp4",
        {"title": "Hikoukigumo",
         "tags": ["PV"],
         "media": None,
         "artists": ["Arai Yumi"],
         "details": [("AMV", "Kaze Tachinu"),
                     ("AMV", "Le Vent se lève")]}),
        ("Anime/Yamada-kun to 7-nin no Majo (TV) - OP - Kuchizuke Diamond.mkv",
         {"title": "Kuchizuke Diamond",
          "tags": ["OP"],
          "media": {"name": "Yamada-kun to 7-nin no Majo (TV)",
                    "media_type": "anime"},
          "artists": [],
          "details": []}),
         ("Nouveau/Mili - PV - world.execute(me);.mkv",
          {"title": "world.execute(me);",
           "artists": ["Mili"],
           "media": None,
           "tags": ["PV"],
           "details": []}),
         ("Nouveau/BIRDIE WING Golf Girls' Story - OP - Venus Line.mp4",
          {"title": "Venus Line",
           "artists": [],
           "media": {"name": "BIRDIE WING Golf Girls' Story",
                     "media_type": "anime"},
           "tags": ["OP"],
           "details": []}),
         ("base/Japan7/Nouveau/Aqours - LIVE - Kimi no Hitomi o Meguru Bouken (VIDEO Love Live! Sunshine!! Aqours 5th LoveLive! ～Next SPARKLING!!～ Day 1).mp4",  # noqa: E501
          {"title": "Kimi no Hitomi o Meguru Bouken",
           "tags": ["LIVE"],
           "artists": ["Aqours"],
           "media": None,
           "details": [("VIDEO", "Love Live! Sunshine!! Aqours 5th LoveLive! ～Next SPARKLING!!～ Day 1")]}),
         ("base/Japan7/Nouveau/Aimer, Lilas Ikuta, milet - PV LIVE - Omokage.mkv",
          {"title": "Omokage",
           "tags": ["PV", "LIVE"],
           "artists": ["Aimer", "Lilas Ikuta", "milet"],
           "media": None,
           "details": []}),
]


class ParserTestCase(unittest.TestCase):

    def test_parse(self):
        for filepath, expected in file_tests:
            file = Path(filepath)
            with self.subTest(file=file, expected=expected):
                parsed = parse_file(file)
                self.assertEqual(parsed, expected)


if __name__ == "__main__":
    unittest.main()

