import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import render_prompt as rp  # noqa: E402


class SetupChat(unittest.TestCase):
    def test_readme_box_is_up_to_date(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        box = readme.split(rp.SETUP_START, 1)[1].split(rp.SETUP_END, 1)[0]
        self.assertEqual(box, "\n```text\n" + rp.render_setup() + "```\n",
                         "run: python3 tools/render_prompt.py --setup")

    def test_setup_carries_the_whole_template(self):
        tpl = (ROOT / "templates/instructions.md").read_text(encoding="utf-8").strip()
        self.assertIn("TEMPLATE START\n" + tpl + "\nTEMPLATE END", rp.render_setup())

    def test_setup_has_no_triple_backticks(self):
        self.assertNotIn("```", rp.render_setup())

    def test_largest_council_fits_chatgpt_limit(self):
        mentors = [(f"Mentor Number {i}", "x" * 110) for i in range(10)]
        text = rp.render(name="A Long Council Name", about="y" * 400, focus=["Career", "Business", "Money"],
                         mentors=mentors, style="brutal", length="long", language="Portuguese")
        self.assertLess(len(text), rp.LIMIT)


if __name__ == "__main__":
    unittest.main()
