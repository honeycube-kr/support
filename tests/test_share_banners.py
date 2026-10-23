from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1] / "images/share"


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
    def test_single_common_banner_for_all_modes_and_languages(self):
        current = ROOT / "v2"
        self.assertEqual({p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.jpg")}, {"v2/common.jpg"})
        data = (current / "common.jpg").read_bytes()
        self.assertEqual(jpeg_size(data), (1200, 630))
        self.assertLessEqual(len(data), 200000)
        self.assertTrue(data.endswith(b"\xff\xd9"))



if __name__ == "__main__":
    unittest.main()
