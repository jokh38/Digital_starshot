"""
Unit tests for isocenter detection functions.

Tests cover laser and DR center detection algorithms with synthetic test data.
Follows TDD principles with comprehensive coverage of happy paths and edge cases.
"""

import unittest
import numpy as np
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

    def test_detect_laser_isocenter_centered(self):
        """Test detection of laser isocenter at image center."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_laser_image(center_x, center_y)

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        # Should detect center with some tolerance (within 5 pixels)
        self.assertAlmostEqual(detected_x, center_x, delta=10)
        self.assertAlmostEqual(detected_y, center_y, delta=10)

    def test_detect_laser_isocenter_offset(self):
        """Test detection of laser isocenter with offset position."""
        center_x, center_y = 180, 220
        image = self.create_synthetic_laser_image(center_x, center_y)

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        # Should detect offset center with reasonable tolerance
        self.assertAlmostEqual(detected_x, center_x, delta=15)
        self.assertAlmostEqual(detected_y, center_y, delta=15)

    def test_detect_laser_isocenter_returns_floats(self):
        """Test that function returns float coordinates."""
        image = self.create_synthetic_laser_image(200, 200)
        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        self.assertIsInstance(detected_x, (float, np.floating))
        self.assertIsInstance(detected_y, (float, np.floating))

    def test_detect_laser_isocenter_empty_image(self):
        """Test detection with empty (all black) image."""
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        # Should not raise exception
        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        self.assertIsInstance(detected_x, (float, np.floating))
        self.assertIsInstance(detected_y, (float, np.floating))

    def test_detect_laser_isocenter_custom_roi_size(self):
        """Test detection with custom ROI size."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_laser_image(center_x, center_y)

        # Test with different ROI sizes
        for roi_size in [100, 150, 200]:
            detected_x, detected_y = detect_laser_isocenter(image, roi_size=roi_size)
            self.assertGreater(detected_x, 0)
            self.assertGreater(detected_y, 0)

    def test_detect_laser_isocenter_small_image(self):
        """Test detection with small image dimensions."""
        small_image = np.zeros((100, 100), dtype=np.uint8)
        small_image[50, 45:55] = 255
        small_image[45:55, 50] = 255

        detected_x, detected_y = detect_laser_isocenter(small_image, roi_size=50)

        self.assertIsInstance(detected_x, (float, np.floating))
        self.assertIsInstance(detected_y, (float, np.floating))

    def test_detect_laser_isocenter_high_contrast(self):
        """Test detection with high contrast crosshair."""
        center_x, center_y = 200, 200
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
        image[center_y - 150:center_y + 150, center_x - 2:center_x + 2] = 255
        image[center_y - 2:center_y + 2, center_x - 150:center_x + 150] = 255

        detected_x, detected_y = detect_laser_isocenter(image, roi_size=self.roi_size)

        self.assertAlmostEqual(detected_x, center_x, delta=10)
        self.assertAlmostEqual(detected_y, center_y, delta=10)


class TestDetectDRCenter(unittest.TestCase):
    """Test suite for DR center detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.image_size = 400
        self.roi_size = 200

    def create_synthetic_dr_image(self, center_x, center_y, radius=20):
        """
        Create a synthetic DR center image (circle).

        Args:
            center_x: X coordinate of circle center
            center_y: Y coordinate of circle center
            radius: Radius of the circle

        Returns:
            Grayscale numpy array with DR marker
        """
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
        y, x = np.ogrid[:self.image_size, :self.image_size]

        # Create circular marker
        mask = (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
        image[mask] = 255

        return image

    def test_detect_dr_center_centered_circle(self):
        """Test detection of DR center with centered circle."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_dr_image(center_x, center_y, radius=20)

        detected_x, detected_y = detect_dr_center(image, roi_size=self.roi_size)

        # Should detect center with reasonable tolerance
        self.assertAlmostEqual(detected_x, center_x, delta=15)
        self.assertAlmostEqual(detected_y, center_y, delta=15)

    def test_detect_dr_center_offset_circle(self):
        """Test detection of DR center with offset circle."""
        center_x, center_y = 190, 210
        image = self.create_synthetic_dr_image(center_x, center_y, radius=25)

        detected_x, detected_y = detect_dr_center(image, roi_size=self.roi_size)

        # Should detect offset center
        self.assertAlmostEqual(detected_x, center_x, delta=20)
        self.assertAlmostEqual(detected_y, center_y, delta=20)

    def test_detect_dr_center_returns_tuple(self):
        """Test that function returns tuple of coordinates."""
        image = self.create_synthetic_dr_image(200, 200, radius=20)

        result = detect_dr_center(image, roi_size=self.roi_size)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_detect_dr_center_empty_image(self):
        """Test detection with empty image (no DR marker)."""
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        detected_x, detected_y = detect_dr_center(image, roi_size=self.roi_size)

        # Should return coordinates without raising exception
        self.assertIsInstance(detected_x, (int, float, np.integer, np.floating))
        self.assertIsInstance(detected_y, (int, float, np.integer, np.floating))

    def test_detect_dr_center_custom_roi_size(self):
        """Test detection with custom ROI size."""
        center_x, center_y = 200, 200
        image = self.create_synthetic_dr_image(center_x, center_y, radius=20)

        for roi_size in [100, 150, 200]:
            detected_x, detected_y = detect_dr_center(
                image, roi_size=roi_size, min_area=5, max_area=1000
            )
            self.assertGreater(detected_x, 0)
            self.assertGreater(detected_y, 0)

    def test_detect_dr_center_area_filtering(self):
        """Test area filtering for DR detection."""
        image = self.create_synthetic_dr_image(200, 200, radius=20)

        # With area constraints that match the circle
        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=100, max_area=2000
        )

        self.assertAlmostEqual(detected_x, 200, delta=20)
        self.assertAlmostEqual(detected_y, 200, delta=20)

    def test_detect_dr_center_small_circles_filtered(self):
        """Test that very small contours are filtered."""
        image = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
        # Add tiny noise
        image[190:192, 190:192] = 255

        # With strict area constraints
        detected_x, detected_y = detect_dr_center(
            image, roi_size=self.roi_size, min_area=50, max_area=500
        )

        # Should handle gracefully
        self.assertIsInstance(detected_x, (int, float, np.integer, np.floating))
        self.assertIsInstance(detected_y, (int, float, np.integer, np.floating))

    def test_detect_dr_center_multiple_circles(self):
        """Test detection with multiple circles (should find largest in area)."""
        image = self.create_synthetic_dr_image(200, 200, radius=25)
        # Add smaller circle closer to center
        y, x = np.ogrid[:self.image_size, :self.image_size]
        mask_small = (x - 220) ** 2 + (y - 220) ** 2 <= 10 ** 2
        image[mask_small] = 255

        detected_x, detected_y = detect_dr_center(image, roi_size=self.roi_size)

        # Should detect the larger circle at original center
        self.assertLess(abs(detected_x - 200), 30)
        self.assertLess(abs(detected_y - 200), 30)

    def test_detect_dr_center_small_image(self):
        """Test detection with small image dimensions."""
        small_image = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask = (x - 50) ** 2 + (y - 50) ** 2 <= 15 ** 2
        small_image[mask] = 255

        detected_x, detected_y = detect_dr_center(small_image, roi_size=40)

        self.assertIsInstance(detected_x, (int, float, np.integer, np.floating))
        self.assertIsInstance(detected_y, (int, float, np.integer, np.floating))


if __name__ == '__main__':
    unittest.main()
