from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLAY_URL = (
    "https://play.google.com/store/apps/details?id=net.honeycube.bricksquare"
    "&utm_source=honeycube&utm_medium=website&utm_campaign=brick_square"
)
ITCH_URL = "https://honeycubekr.itch.io/brick-square"
ITCH_BADGE_URL = "/images/itch-io-badge-en.svg"
YOUTUBE_URL = "https://youtu.be/6POI0gqNSKI"
PRIVACY_URL = "/bricksquare/privacy_policy_en.html"
CANONICAL_ORIGIN = "https://www.honeycube.net"
CANONICAL_URLS = {
    "/": f"{CANONICAL_ORIGIN}/",
    "/bricksquare/privacy_policy_en.html": (
        f"{CANONICAL_ORIGIN}/bricksquare/privacy_policy_en.html"
    ),
    "/bricksquare/privacy_policy_ko.html": (
        f"{CANONICAL_ORIGIN}/bricksquare/privacy_policy_ko.html"
    ),
    "/bricksquare/privacy_policy_ja.html": (
        f"{CANONICAL_ORIGIN}/bricksquare/privacy_policy_ja.html"
    ),
}


class LandingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_attributes = {}
        self.anchors = []
        self.iframes = []
        self.images = []
        self.links = []
        self.metas = []
        self.elements = []
        self.interactive_order = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "html":
            self.html_attributes = attributes
        elif tag == "a":
            self.anchors.append(attributes)
            self.interactive_order.append((tag, attributes))
        elif tag == "iframe":
            self.iframes.append(attributes)
            self.interactive_order.append((tag, attributes))
        elif tag == "img":
            self.images.append(attributes)
        elif tag == "link":
            self.links.append(attributes)
        elif tag == "meta":
            self.metas.append(attributes)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class LandingPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

        with urlopen(f"{cls.base_url}/", timeout=5) as response:
            cls.status = response.status
            cls.html = response.read().decode("utf-8")

        cls.parser = LandingParser()
        cls.parser.feed(cls.html)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path):
        try:
            with urlopen(f"{self.base_url}{path}", timeout=5) as response:
                return response.status, response.read().decode("utf-8")
        except HTTPError as error:
            return error.code, error.read().decode("utf-8")

    def test_serves_an_english_landing_page(self):
        self.assertEqual(self.status, 200)
        self.assertEqual(self.parser.html_attributes.get("lang"), "en")
        self.assertIn("Brick Square", self.html)
        self.assertIn("HoneyCube", self.html)

    def test_does_not_show_a_company_label_above_the_game_logo(self):
        company_labels = [
            (tag, attributes)
            for tag, attributes in self.parser.elements
            if "company" in attributes.get("class", "").split()
        ]

        self.assertEqual(company_labels, [])

    def test_places_store_links_after_video(self):
        video_index = next(
            (
                index
                for index, (tag, _) in enumerate(self.parser.interactive_order)
                if tag == "iframe"
            ),
            None,
        )
        store_indexes = [
            index
            for index, (tag, attrs) in enumerate(self.parser.interactive_order)
            if tag == "a" and attrs.get("href") in {PLAY_URL, ITCH_URL}
        ]

        self.assertIsNotNone(video_index)
        self.assertEqual(len(store_indexes), 2)
        self.assertTrue(all(video_index < index for index in store_indexes))

    def test_embeds_the_uploaded_video_without_autoplay(self):
        self.assertEqual(len(self.parser.iframes), 1)
        iframe = self.parser.iframes[0]
        self.assertEqual(
            iframe.get("src"),
            "https://www.youtube.com/embed/6POI0gqNSKI?playsinline=1&rel=0",
        )
        self.assertEqual(iframe.get("loading"), "lazy")
        self.assertNotIn("autoplay=1", iframe.get("src", ""))

    def test_exposes_privacy_without_a_youtube_fallback_link(self):
        hrefs = {anchor.get("href") for anchor in self.parser.anchors}
        self.assertIn(PRIVACY_URL, hrefs)
        self.assertNotIn(YOUTUBE_URL, hrefs)

    def test_exposes_google_play_with_campaign_tracking_and_itch_badge(self):
        anchors_by_href = {
            anchor.get("href"): anchor for anchor in self.parser.anchors
        }
        self.assertIn(PLAY_URL, anchors_by_href)
        self.assertIn(ITCH_URL, anchors_by_href)

        itch_badges = [
            image
            for image in self.parser.images
            if image.get("src") == ITCH_BADGE_URL
        ]
        self.assertEqual(len(itch_badges), 1)
        self.assertEqual(itch_badges[0].get("alt"), "Download on itch.io")

    def test_root_is_the_landing_page_without_a_redirect(self):
        self.assertNotIn("http-equiv=\"refresh\"", self.html.lower())
        self.assertIn("Rotate. Clear. Keep Going.", self.html)

    def test_play_landing_path_is_removed(self):
        status, _ = self.get("/play/")
        self.assertEqual(status, 404)

    def test_declares_self_canonical_urls(self):
        for path, expected_canonical in CANONICAL_URLS.items():
            status, html = self.get(path)
            parser = LandingParser()
            parser.feed(html)
            canonical_urls = [
                link.get("href")
                for link in parser.links
                if link.get("rel") == "canonical"
            ]

            self.assertEqual(status, 200, path)
            self.assertEqual(canonical_urls, [expected_canonical], path)

    def test_sitemap_lists_only_canonical_urls(self):
        status, sitemap = self.get("/sitemap.xml")
        self.assertEqual(status, 200)

        root = ET.fromstring(sitemap)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {
            element.text for element in root.findall("sitemap:url/sitemap:loc", namespace)
        }
        self.assertEqual(locations, set(CANONICAL_URLS.values()))

    def test_robots_points_to_the_canonical_sitemap(self):
        status, robots = self.get("/robots.txt")
        self.assertEqual(status, 200)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertIn(
            f"Sitemap: {CANONICAL_ORIGIN}/sitemap.xml",
            robots,
        )

    def test_version_metadata_uses_the_canonical_store_url(self):
        status, version_json = self.get("/bricksquare/version.json")
        self.assertEqual(status, 200)
        version = json.loads(version_json)
        self.assertEqual(
            version["android"]["web_store_url"],
            f"{CANONICAL_ORIGIN}/",
        )

    def test_every_local_image_is_served(self):
        sources = [
            image.get("src")
            for image in self.parser.images
            if image.get("src", "").startswith("/images/")
        ]
        self.assertGreaterEqual(len(sources), 6)

        for source in sources:
            with urlopen(f"{self.base_url}{source}", timeout=5) as response:
                self.assertEqual(response.status, 200, source)
                self.assertGreater(int(response.headers["Content-Length"]), 0, source)


if __name__ == "__main__":
    unittest.main()
