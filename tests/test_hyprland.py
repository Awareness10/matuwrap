"""Tests for wrappers.core.hyprland module."""

import unittest

from wrappers.core.hyprland import TRANSFORMS, is_rotated, swap_if_rotated


class TestTransforms(unittest.TestCase):
    """Tests for TRANSFORMS constant."""

    def test_transforms_has_all_values(self):
        """TRANSFORMS should have entries for 0-7."""
        for i in range(8):
            self.assertIn(i, TRANSFORMS)

    def test_transforms_normal_is_none(self):
        """Transform 0 (normal) should be None."""
        self.assertIsNone(TRANSFORMS[0])

    def test_transforms_rotations_have_degrees(self):
        """Rotation transforms should have degree labels."""
        self.assertEqual(TRANSFORMS[1], "90°")
        self.assertEqual(TRANSFORMS[2], "180°")
        self.assertEqual(TRANSFORMS[3], "270°")

    def test_transforms_flipped_values(self):
        """Flipped transforms should have 'flipped' prefix."""
        self.assertEqual(TRANSFORMS[4], "flipped")
        # These are known to be strings, not None
        val5, val6, val7 = TRANSFORMS[5], TRANSFORMS[6], TRANSFORMS[7]
        self.assertIsNotNone(val5)
        self.assertIsNotNone(val6)
        self.assertIsNotNone(val7)
        assert val5 is not None and val6 is not None and val7 is not None
        self.assertIn("flipped", val5)
        self.assertIn("flipped", val6)
        self.assertIn("flipped", val7)


class TestIsRotated(unittest.TestCase):
    """Tests for is_rotated function."""

    def test_normal_not_rotated(self):
        """Transform 0 (normal) is not rotated."""
        self.assertFalse(is_rotated(0))

    def test_90_is_rotated(self):
        """Transform 1 (90°) is rotated."""
        self.assertTrue(is_rotated(1))

    def test_180_not_rotated(self):
        """Transform 2 (180°) does not swap dimensions."""
        self.assertFalse(is_rotated(2))

    def test_270_is_rotated(self):
        """Transform 3 (270°) is rotated."""
        self.assertTrue(is_rotated(3))

    def test_flipped_not_rotated(self):
        """Transform 4 (flipped) does not swap dimensions."""
        self.assertFalse(is_rotated(4))

    def test_flipped_90_is_rotated(self):
        """Transform 5 (flipped 90°) is rotated."""
        self.assertTrue(is_rotated(5))

    def test_flipped_180_not_rotated(self):
        """Transform 6 (flipped 180°) does not swap dimensions."""
        self.assertFalse(is_rotated(6))

    def test_flipped_270_is_rotated(self):
        """Transform 7 (flipped 270°) is rotated."""
        self.assertTrue(is_rotated(7))

    def test_all_rotated_transforms(self):
        """All 90°/270° transforms (1, 3, 5, 7) should be rotated."""
        rotated = [1, 3, 5, 7]
        for t in rotated:
            self.assertTrue(is_rotated(t), f"Transform {t} should be rotated")

    def test_all_non_rotated_transforms(self):
        """Transforms 0, 2, 4, 6 should not be rotated."""
        non_rotated = [0, 2, 4, 6]
        for t in non_rotated:
            self.assertFalse(is_rotated(t), f"Transform {t} should not be rotated")


class TestSwapIfRotated(unittest.TestCase):
    """Tests for swap_if_rotated function."""

    def test_no_swap_normal(self):
        """No swap for normal (transform 0)."""
        w, h = swap_if_rotated(1920, 1080, 0)
        self.assertEqual((w, h), (1920, 1080))

    def test_swap_90(self):
        """Swap for 90° rotation (transform 1)."""
        w, h = swap_if_rotated(1920, 1080, 1)
        self.assertEqual((w, h), (1080, 1920))

    def test_no_swap_180(self):
        """No swap for 180° rotation (transform 2)."""
        w, h = swap_if_rotated(1920, 1080, 2)
        self.assertEqual((w, h), (1920, 1080))

    def test_swap_270(self):
        """Swap for 270° rotation (transform 3)."""
        w, h = swap_if_rotated(1920, 1080, 3)
        self.assertEqual((w, h), (1080, 1920))

    def test_no_swap_flipped(self):
        """No swap for flipped (transform 4)."""
        w, h = swap_if_rotated(1920, 1080, 4)
        self.assertEqual((w, h), (1920, 1080))

    def test_swap_flipped_90(self):
        """Swap for flipped 90° (transform 5)."""
        w, h = swap_if_rotated(1920, 1080, 5)
        self.assertEqual((w, h), (1080, 1920))

    def test_no_swap_flipped_180(self):
        """No swap for flipped 180° (transform 6)."""
        w, h = swap_if_rotated(1920, 1080, 6)
        self.assertEqual((w, h), (1920, 1080))

    def test_swap_flipped_270(self):
        """Swap for flipped 270° (transform 7)."""
        w, h = swap_if_rotated(1920, 1080, 7)
        self.assertEqual((w, h), (1080, 1920))

    def test_swap_square_dimensions(self):
        """Swapping square dimensions returns same values."""
        w, h = swap_if_rotated(1000, 1000, 1)
        self.assertEqual((w, h), (1000, 1000))

    def test_swap_ultrawide(self):
        """Test with ultrawide monitor dimensions."""
        w, h = swap_if_rotated(3440, 1440, 1)
        self.assertEqual((w, h), (1440, 3440))

    def test_swap_4k(self):
        """Test with 4K monitor dimensions."""
        w, h = swap_if_rotated(3840, 2160, 3)
        self.assertEqual((w, h), (2160, 3840))


if __name__ == "__main__":
    unittest.main()
