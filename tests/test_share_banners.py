from pathlib import Path
import hashlib
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1] / "images/share/v1"


def jpeg_size(data):
    if data[:2] != b"\xff\xd8":
        raise ValueError("Not JPEG")
    offset = 2
    while offset < len(data):
        if data[offset] != 0xff:
            raise ValueError("Invalid JPEG segment")
        marker = data[offset + 1]
        offset += 2
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        if marker in (0xc0, 0xc1, 0xc2):
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        offset += length
    raise ValueError("Missing JPEG frame")


class ShareBannerTest(unittest.TestCase):
    def test_nine_versioned_jpeg_banners(self):
        expected = {f"{lang}/{mode}.jpg" for lang in ("ko", "en", "ja")
                    for mode in ("stage", "daily", "survival")}
        self.assertEqual({p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.jpg")}, expected)
        hashes = set()
        for relative in sorted(expected):
            with self.subTest(banner=relative):
                data = (ROOT / relative).read_bytes()
                self.assertEqual(jpeg_size(data), (1200, 630))
                self.assertLessEqual(len(data), 200000)
                self.assertTrue(data.endswith(b"\xff\xd9"))
                hashes.add(hashlib.sha256(data).hexdigest())
        self.assertEqual(len(hashes), 9)


if __name__ == "__main__":
    unittest.main()
