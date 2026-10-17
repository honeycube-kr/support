from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PolicyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.links = []
        self.anchors = []
        self.text = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "link":
            self.links.append(attrs)
        elif tag == "a":
            self.anchors.append(attrs.get("href"))
        elif tag == "h2":
            self.headings += 1

    def handle_data(self, data):
        self.text.append(data)


class PrivacyPolicyTest(unittest.TestCase):
    def policies(self):
        for variant in ("", "toss/"):
            for locale in ("ko", "en", "ja"):
                path = f"/bricksquare/{variant}privacy_policy_{locale}.html"
                source = (ROOT / path.lstrip("/")).read_text(encoding="utf-8")
                parser = PolicyParser()
                parser.feed(source)
                markdown = (ROOT / path.lstrip("/")).with_suffix(".md").read_text(encoding="utf-8")
                yield variant, locale, path, source, parser, markdown

    def test_all_languages_and_variants_keep_the_full_policy(self):
        for variant, locale, path, source, parser, markdown in self.policies():
            with self.subTest(path=path):
                self.assertEqual(parser.lang, locale)
                self.assertEqual(parser.headings, 11)
                self.assertEqual(len(re.findall(r"^## ", markdown, re.M)), 11)
                for identifier in ("brick_id", "install_id", "PostHog", "Supabase"):
                    self.assertIn(identifier, source)
                    self.assertIn(identifier, markdown)
                self.assertIn("12", markdown)
                self.assertIn("mailto:honeycube.kr@gmail.com", parser.anchors)
                self.assertNotIn("&lt;li&gt;", source)

    def test_canonical_and_counterpart_links_match_each_variant(self):
        for variant, locale, path, source, parser, markdown in self.policies():
            with self.subTest(path=path):
                canonicals = [link.get("href") for link in parser.links if link.get("rel") == "canonical"]
                self.assertEqual(canonicals, [f"https://www.honeycube.net{path}"])
                counterpart = "" if variant else "toss/"
                target = f"/bricksquare/{counterpart}privacy_policy_{locale}.html"
                self.assertIn(target, parser.anchors)
                self.assertIn(target, markdown)
                self.assertTrue((ROOT / target.lstrip("/")).is_file())

    def test_toss_disclosures_are_scoped_to_the_toss_policy(self):
        for variant, locale, path, source, parser, markdown in self.policies():
            with self.subTest(path=path):
                self.assertEqual(bool(re.search(r"^### 3. (?:토스|Toss|トス)", markdown, re.M)), bool(variant))
                self.assertEqual("SDK" in source, bool(variant))
                self.assertEqual("SDK" in markdown, bool(variant))
                if variant:
                    for value in ("Toss", "Apps-in-Toss") if locale == "en" else ("Apps-in-Toss",) if locale == "ja" else ("토스 앱인토스",):
                        self.assertIn(value, source)
                        self.assertIn(value, markdown)


if __name__ == "__main__":
    unittest.main()
