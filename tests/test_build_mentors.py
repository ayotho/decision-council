import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import build_mentors as bm  # noqa: E402

AUTO_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.160 --> 00:00:02.869 align:start position:0%

so<00:00:00.480><c> the</c><00:00:00.640><c> first</c><00:00:00.880><c> thing</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
so the first thing


00:00:02.879 --> 00:00:05.110 align:start position:0%
so the first thing
you<00:00:03.120><c> need</c><00:00:03.360><c> is</c><00:00:03.600><c> an</c><00:00:03.840><c> offer</c>

00:00:05.110 --> 00:00:05.120 align:start position:0%
you need is an offer


00:01:05.120 --> 00:01:07.000 align:start position:0%
you need is an offer
that&#39;s<00:01:05.500><c> too</c><c> good</c>
"""

MANUAL_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:03.000
Hello <i>there</i>.

2
01:02:03.500 --> 01:02:05.000
Second line &amp; more.
"""


class ParseVtt(unittest.TestCase):
    def test_auto_captions_are_deduplicated(self):
        segs = bm.parse_vtt(AUTO_VTT)
        texts = [t for _, t in segs]
        self.assertEqual(texts, ["so the first thing", "you need is an offer", "that's too good"])
        self.assertAlmostEqual(segs[0][0], 0.16, places=2)
        self.assertAlmostEqual(segs[2][0], 65.12, places=2)

    def test_manual_captions_strip_tags_and_entities(self):
        segs = bm.parse_vtt(MANUAL_VTT)
        self.assertEqual(segs, [(1.0, "Hello there."), (3723.5, "Second line & more.")])


class Paragraphs(unittest.TestCase):
    def test_groups_by_window_and_keeps_start(self):
        segs = [(0.0, "a"), (30.0, "b"), (61.0, "c"), (95.0, "d"), (130.0, "e")]
        paras = bm.to_paragraphs(segs, window=60)
        self.assertEqual(paras, [(0, "a b"), (61, "c d"), (130, "e")])

    def test_stamp_format(self):
        self.assertEqual(bm.stamp(5), "0:05")
        self.assertEqual(bm.stamp(754), "12:34")
        self.assertEqual(bm.stamp(3723), "1:02:03")


class Urls(unittest.TestCase):
    def test_handle_becomes_videos_tab(self):
        self.assertEqual(bm.normalise_url("@AlexHormozi"), ("list", "https://www.youtube.com/@AlexHormozi/videos"))
        self.assertEqual(bm.normalise_url("youtube.com/@AlexHormozi"), ("list", "https://www.youtube.com/@AlexHormozi/videos"))
        self.assertEqual(bm.normalise_url("https://www.youtube.com/@AlexHormozi/"), ("list", "https://www.youtube.com/@AlexHormozi/videos"))

    def test_channel_tabs_and_ids(self):
        self.assertEqual(bm.normalise_url("https://www.youtube.com/@x/streams"), ("list", "https://www.youtube.com/@x/streams"))
        self.assertEqual(bm.normalise_url("https://youtube.com/channel/UC123"), ("list", "https://www.youtube.com/channel/UC123/videos"))
        self.assertEqual(bm.normalise_url("https://m.youtube.com/c/Old"), ("list", "https://www.youtube.com/c/Old/videos"))

    def test_playlist_and_single_videos(self):
        self.assertEqual(bm.normalise_url("https://www.youtube.com/playlist?list=PL1"), ("list", "https://www.youtube.com/playlist?list=PL1"))
        self.assertEqual(bm.normalise_url("https://youtu.be/abcDEF12345?si=x"), ("video", "https://www.youtube.com/watch?v=abcDEF12345"))
        self.assertEqual(bm.normalise_url("https://www.youtube.com/watch?v=abcDEF12345&t=30"), ("video", "https://www.youtube.com/watch?v=abcDEF12345"))
        self.assertEqual(bm.normalise_url("https://www.youtube.com/shorts/abcDEF12345"), ("video", "https://www.youtube.com/watch?v=abcDEF12345"))

    def test_rejects_non_youtube(self):
        with self.assertRaises(ValueError):
            bm.normalise_url("https://vimeo.com/123")


class MentorSpec(unittest.TestCase):
    def test_full_spec(self):
        m = bm.parse_mentor("Alex Hormozi | @AlexHormozi, https://youtu.be/abcDEF12345 | 30 | offer, pricing | Offers and pricing")
        self.assertEqual(m["name"], "Alex Hormozi")
        self.assertEqual(m["slug"], "alex-hormozi")
        self.assertEqual(len(m["sources"]), 2)
        self.assertEqual(m["max"], 30)
        self.assertEqual(m["keywords"], ["offer", "pricing"])
        self.assertEqual(m["lens"], "Offers and pricing")

    def test_defaults(self):
        m = bm.parse_mentor("Ali Abdaal|@aliabdaal")
        self.assertEqual(m["max"], bm.DEFAULT_MAX)
        self.assertEqual(m["keywords"], [])
        self.assertEqual(m["lens"], "")

    def test_spec_written_by_setup_page(self):
        m = bm.parse_mentor("Alex Hormozi | @AlexHormozi | 25 |  | Offers, pricing")
        self.assertEqual((m["max"], m["keywords"], m["lens"]), (25, [], "Offers, pricing"))
        m = bm.parse_mentor("Ali Abdaal | https://www.youtube.com/@aliabdaal | 25 |  | ")
        self.assertEqual((m["keywords"], m["lens"]), ([], ""))

    def test_needs_name_and_link(self):
        with self.assertRaises(ValueError):
            bm.parse_mentor("JustAName")

    def test_slug_handles_symbols(self):
        self.assertEqual(bm.slugify("Dr. Jordan B. Peterson!"), "dr-jordan-b-peterson")


class Picking(unittest.TestCase):
    ENTRIES = [
        {"id": "a" * 11, "title": "Pricing 101", "duration": 900, "view_count": 10},
        {"id": "b" * 11, "title": "My morning", "duration": 40, "view_count": 999},
        {"id": "c" * 11, "title": "How to price", "duration": 1200, "view_count": 500},
        {"id": "d" * 11, "title": "Offer secrets", "duration": None, "view_count": None},
    ]

    def test_popular_skips_shorts(self):
        got = bm.pick_videos(self.ENTRIES, max_videos=2, sort="popular", keywords=[], min_seconds=180)
        self.assertEqual([e["id"][0] for e in got], ["c", "a"])

    def test_keywords_and_recent_order(self):
        got = bm.pick_videos(self.ENTRIES, max_videos=5, sort="recent", keywords=["price", "offer"], min_seconds=180)
        self.assertEqual([e["id"][0] for e in got], ["c", "d"])


if __name__ == "__main__":
    unittest.main()
