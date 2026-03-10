"""
Unit tests for isocenter detection functions.

Tests cover laser and DR center detection algorithms with synthetic test data.
Follows TDD principles with comprehensive coverage of happy paths and edge cases.
"""

import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from src.domain.isocenter_detection import (
    detect_laser_isocenter,
    detect_dr_center
)


class TestDetectLaserIsocenter(unittest.TestCase):
    """Test suite for laser isocenter detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.image_size = 400
        self.roi_size = 200

    def create_synthetic_laser_image(self, center_x, center_y, thickness=10):
        """
        Create a synthetic laser crosshair image.

        Args:
            center_x: X coordinate of the crosshair center
            center_y: Y coordinate of the crosshair center
            thickness: Thickness of the crosshair lines

        Returns:
            Grayscale numpy array with laser lines
        """
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        # Draw vertical line
        image[max(0, center_y - 150):min(self.image_size, center_y + 150),
              max(0, center_x - thickness):max(0, center_x + thickness)] = 255

        # Draw horizontal line
        image[max(0, center_y - thickness):max(0, center_y + thickness),
              max(0, center_x - 150):min(self.image_size, center_x + 150)] = 255

        return image

    def create_synthetic_green_laser_image(self, center_x, center_y, thickness=6):
        """Create an RGB image with green laser lines on a dark background."""
        image = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        image[max(0, center_y - 150):min(self.image_size, center_y + 150),
              max(0, center_x - thickness):min(self.image_size, center_x + thickness), 1] = 255
        image[max(0, center_y - thickness):min(self.image_size, center_y + thickness),
              max(0, center_x - 150):min(self.image_size, center_x + 150), 1] = 255
        return image

    def test_detect_laser_isocenter_centered(self):
        """Test detection of laser isocenter at image center."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_green_laser_image(center_x, center_y)

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        # Should detect center with some tolerance (within 5 pixels)
        self.assertAlmostEqual(detected_x, center_x, delta=10)
        self.assertAlmostEqual(detected_y, center_y, delta=10)

    def test_detect_laser_isocenter_offset(self):
        """Test detection of laser isocenter with offset position."""
        center_x, center_y = 180, 220
        image = self.create_synthetic_green_laser_image(center_x, center_y)

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        # Should detect offset center with reasonable tolerance
        self.assertAlmostEqual(detected_x, center_x, delta=15)
        self.assertAlmostEqual(detected_y, center_y, delta=15)

    def test_detect_laser_isocenter_returns_floats(self):
        """Test that function returns float coordinates."""
        image = self.create_synthetic_green_laser_image(200, 200)
        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        self.assertIsInstance(detected_x, (float, np.floating))
        self.assertIsInstance(detected_y, (float, np.floating))

    def test_detect_laser_isocenter_empty_image_raises(self):
        """Laser detection should fail explicitly when no signal is present."""
        image = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)

        with self.assertRaises(ValueError):
            detect_laser_isocenter(image, roi_size=self.roi_size)

    def test_detect_laser_isocenter_custom_roi_size(self):
        """Test detection with custom ROI size."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_green_laser_image(center_x, center_y)

        # Test with different ROI sizes
        for roi_size in [100, 150, 200]:
            detected_x, detected_y = detect_laser_isocenter(image, roi_size=roi_size)
            self.assertGreater(detected_x, 0)
            self.assertGreater(detected_y, 0)

    def test_detect_laser_isocenter_small_image(self):
        """Test detection with small image dimensions."""
        small_image = np.zeros((100, 100, 3), dtype=np.uint8)
        small_image[50, 45:55, 1] = 255
        small_image[45:55, 50, 1] = 255

        detected_x, detected_y = detect_laser_isocenter(small_image, roi_size=50)

        self.assertIsInstance(detected_x, (float, np.floating))
        self.assertIsInstance(detected_y, (float, np.floating))

    def test_detect_laser_isocenter_high_contrast(self):
        """Test detection with high contrast crosshair."""
        center_x, center_y = 200, 200
        image = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        image[center_y - 150:center_y + 150, center_x - 2:center_x + 2, 1] = 255
        image[center_y - 2:center_y + 2, center_x - 150:center_x + 150, 1] = 255

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        self.assertAlmostEqual(detected_x, center_x, delta=10)
        self.assertAlmostEqual(detected_y, center_y, delta=10)

    def test_detect_laser_isocenter_real_image(self):
        """Regression check on the provided laser sample."""
        image_path = Path(__file__).resolve().parents[2] / "data" / "LA.jpg"
        image = np.array(Image.open(image_path).convert("RGB"))

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=250)

        self.assertAlmostEqual(detected_x, 891.0, delta=3.0)
        self.assertAlmostEqual(detected_y, 891.0, delta=3.0)


class TestDetectDRCenter(unittest.TestCase):
    """Test suite for DR center detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.image_size = 400
        self.roi_size = 200

    def create_synthetic_dr_image(self, center_x, center_y, radius=20):
        """
        Create a synthetic DR image with a dark ball on a bright background.

        Args:
            center_x: X coordinate of circle center
            center_y: Y coordinate of circle center
            radius: Radius of the circle

        Returns:
            Grayscale numpy array with DR marker
        """
        image = np.full((self.image_size, self.image_size), 220, dtype=np.uint8)
        y, x = np.ogrid[:self.image_size, :self.image_size]

        # Create dark circular marker
        mask = (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
        image[mask] = 40

        return image

    def test_detect_dr_center_centered_circle(self):
        """Test detection of DR center with centered circle."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_dr_image(center_x, center_y, radius=10)

        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=20, max_area=500
        )

        # Should detect center with reasonable tolerance
        self.assertAlmostEqual(detected_x, center_x, delta=15)
        self.assertAlmostEqual(detected_y, center_y, delta=15)

    def test_detect_dr_center_offset_circle(self):
        """Test detection of DR center with offset circle."""
        center_x, center_y = 190, 210
        image = self.create_synthetic_dr_image(center_x, center_y, radius=10)

        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=20, max_area=500
        )

        # Should detect offset center
        self.assertAlmostEqual(detected_x, center_x, delta=20)
        self.assertAlmostEqual(detected_y, center_y, delta=20)

    def test_detect_dr_center_returns_tuple(self):
        """Test that function returns tuple of coordinates."""
        image = self.create_synthetic_dr_image(200, 200, radius=10)

        result = detect_dr_center(image, roi_size=self.roi_size, min_area=20, max_area=500)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_detect_dr_center_empty_image_raises(self):
        """DR detection should fail explicitly when no marker is present."""
        image = np.full((self.image_size, self.image_size), 220, dtype=np.uint8)

        with self.assertRaises(ValueError):
            detect_dr_center(image, roi_size=self.roi_size)

    def test_detect_dr_center_custom_roi_size(self):
        """Test detection with custom ROI size."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_dr_image(center_x, center_y, radius=10)

        for roi_size in [100, 150, 200]:
            detected_x, detected_y = detect_dr_center(
                image, roi_size=roi_size, min_area=5, max_area=1000
            )
            self.assertGreater(detected_x, 0)
            self.assertGreater(detected_y, 0)

    def test_detect_dr_center_area_filtering(self):
        """Test area filtering for DR detection."""
        image = self.create_synthetic_dr_image(200, 200, radius=10)

        # With area constraints that match the circle
        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=100, max_area=2000
        )

        self.assertAlmostEqual(detected_x, 200, delta=20)
        self.assertAlmostEqual(detected_y, 200, delta=20)

    def test_detect_dr_center_small_circles_filtered(self):
        """Test that very small contours are filtered."""
        image = np.full((self.image_size, self.image_size), 220, dtype=np.uint8)
        # Add tiny noise
        image[190:192, 190:192] = 40

        with self.assertRaises(ValueError):
            detect_dr_center(image, roi_size=self.roi_size, min_area=50, max_area=500)

    def test_detect_dr_center_multiple_circles(self):
        """Test detection with multiple circles (should find largest in area)."""
        image = self.create_synthetic_dr_image(200, 200, radius=10)
        # Add smaller circle closer to center
        y, x = np.ogrid[:self.image_size, :self.image_size]
        mask_small = (x - 220) ** 2 + (y - 220) ** 2 <= 6 ** 2
        image[mask_small] = 40

        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=20, max_area=500
        )

        # Should detect the larger circle at original center
        self.assertLess(abs(detected_x - 200), 30)
        self.assertLess(abs(detected_y - 200), 30)

    def test_detect_dr_center_small_image(self):
        """Test detection with small image dimensions."""
        small_image = np.full((100, 100), 220, dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask = (x - 50) ** 2 + (y - 50) ** 2 <= 8 ** 2
        small_image[mask] = 40

        detected_x, detected_y = detect_dr_center(small_image, roi_size=40, min_area=20, max_area=500)

        self.assertIsInstance(detected_x, (int, float, np.integer, np.floating))
        self.assertIsInstance(detected_y, (int, float, np.integer, np.floating))

    def test_detect_dr_center_real_image(self):
        """Regression check on the provided DR sample."""
        image_path = Path(__file__).resolve().parents[2] / "data" / "DR.jpg"
        image = np.array(Image.open(image_path).convert("L"))

        detected_x, detected_y = detect_dr_center(image, roi_size=300, min_area=20, max_area=500)

        self.assertAlmostEqual(detected_x, 918, delta=4)
        self.assertAlmostEqual(detected_y, 891, delta=4)


if __name__ == '__main__':
    unittest.main()
