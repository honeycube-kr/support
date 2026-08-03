from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PLAY_URL = (
    "https://play.google.com/store/apps/details?id=net.honeycube.bricksquare"
)
YOUTUBE_URL = "https://youtu.be/6POI0gqNSKI"
PRIVACY_URL = (
    "https://honeycube-kr.github.io/support/bricksquare/privacy_policy_en.html"
)


class LandingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_attributes = {}
        self.anchors = []
        self.iframes = []
        self.images = []
        self.interactive_order = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
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

    def test_serves_an_english_landing_page(self):
        self.assertEqual(self.status, 200)
        self.assertEqual(self.parser.html_attributes.get("lang"), "en")
        self.assertIn("Brick Square", self.html)
        self.assertIn("HoneyCube", self.html)

    def test_prioritizes_the_google_play_link_before_video(self):
        play_index = next(
            (
                index
                for index, (tag, attrs) in enumerate(self.parser.interactive_order)
                if tag == "a" and attrs.get("href") == PLAY_URL
            ),
            None,
        )
        video_index = next(
            (
                index
                for index, (tag, _) in enumerate(self.parser.interactive_order)
                if tag == "iframe"
            ),
            None,
        )

        self.assertIsNotNone(play_index)
        self.assertIsNotNone(video_index)
        self.assertLess(play_index, video_index)

    def test_embeds_the_uploaded_video_without_autoplay(self):
        self.assertEqual(len(self.parser.iframes), 1)
        iframe = self.parser.iframes[0]
        self.assertEqual(
            iframe.get("src"),
            "https://www.youtube.com/embed/6POI0gqNSKI?playsinline=1&rel=0",
        )
        self.assertEqual(iframe.get("loading"), "lazy")
        self.assertNotIn("autoplay=1", iframe.get("src", ""))

    def test_exposes_youtube_and_privacy_fallback_links(self):
        hrefs = {anchor.get("href") for anchor in self.parser.anchors}
        self.assertIn(YOUTUBE_URL, hrefs)
        self.assertIn(PRIVACY_URL, hrefs)

    def test_every_local_image_is_served(self):
        sources = [image.get("src") for image in self.parser.images]
        self.assertGreaterEqual(len(sources), 6)

        for source in sources:
            self.assertTrue(source.startswith("images/"), source)
            with urlopen(f"{self.base_url}/{source}", timeout=5) as response:
                self.assertEqual(response.status, 200, source)
                self.assertGreater(int(response.headers["Content-Length"]), 0, source)


if __name__ == "__main__":
    unittest.main()
