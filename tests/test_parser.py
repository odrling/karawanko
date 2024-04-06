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
                "media_type": "magic"},
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
        "details": []})
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

