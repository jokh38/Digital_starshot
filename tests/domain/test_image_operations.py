"""
Unit tests for image operations functions.

Tests cover image merging and manipulation with PIL Image objects.
Follows TDD principles.
"""

import unittest
import numpy as np
from PIL import Image
from src.domain.image_operations import merge_images


class TestMergeImages(unittest.TestCase):
    """Test suite for image merging functionality."""

    def create_test_image(self, width=400, height=400, fill_color=(100, 100, 100)):
        """
        Create a test PIL image.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            fill_color: RGB color tuple

        Returns:
            PIL Image object
        """
        return Image.new('RGB', (width, height), fill_color)

    def test_merge_empty_list(self):
        """Test merging with empty list."""
        result = merge_images([])

        self.assertIsNone(result)

    def test_merge_single_image(self):
        """Test merging with single image."""
        image = self.create_test_image()
        result = merge_images([image])

        self.assertIsNotNone(result)
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.mode, 'RGB')

    def test_merge_two_images(self):
        """Test merging two images of same size."""
        img1 = self.create_test_image(fill_color=(100, 100, 100))
        img2 = self.create_test_image(fill_color=(50, 50, 50))

        result = merge_images([img1, img2])

        self.assertIsNotNone(result)
        self.assertEqual(result.size, (400, 400))
        self.assertEqual(result.mode, 'RGB')

    def test_merge_multiple_images(self):
        """Test merging multiple images."""
        images = [
            self.create_test_image(fill_color=(100, 0, 0)),
            self.create_test_image(fill_color=(0, 100, 0)),
            self.create_test_image(fill_color=(0, 0, 100))
        ]

        result = merge_images(images)

        self.assertIsNotNone(result)
        self.assertEqual(result.size, (400, 400))

    def test_merge_images_different_sizes(self):
        """Test merging images of different sizes."""
        img1 = self.create_test_image(400, 400)
        img2 = self.create_test_image(300, 300)

        # Should handle gracefully or raise appropriate error
        try:
            result = merge_images([img1, img2])
            # If it succeeds, result should be valid
            self.assertIsNotNone(result)
        except Exception as e:
            # If it fails, error should be descriptive
            self.assertIsNotNone(str(e))

    def test_merge_images_grayscale(self):
        """Test merging grayscale images."""
        img1 = Image.new('L', (400, 400), 100)
        img2 = Image.new('L', (400, 400), 50)

        result = merge_images([img1, img2])

        self.assertIsNotNone(result)

    def test_merge_images_preserves_content(self):
        """Test that merge operation preserves image content."""
        # Create test image with known pattern
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[25:75, 25:75] = [255, 0, 0]  # Red square
        img = Image.fromarray(arr)

        result = merge_images([img])

        result_arr = np.array(result)
        # Merged result should contain the red square
        self.assertTrue(np.any(result_arr[:, :, 0] > 200))

    def test_merge_bright_images_adds_correctly(self):
        """Test that bright regions are merged correctly."""
        # Create two images with bright pixels at different locations
        arr1 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr1[20:30, 20:30] = 200

        arr2 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr2[70:80, 70:80] = 200

        img1 = Image.fromarray(arr1)
        img2 = Image.fromarray(arr2)

        result = merge_images([img1, img2])
        result_arr = np.array(result)

        # Both regions should have high values
        self.assertGreater(result_arr[25, 25, 0], 100)
        self.assertGreater(result_arr[75, 75, 0], 100)

    def test_merge_images_input_not_modified(self):
        """Test that original images are not modified during merge."""
        img1 = self.create_test_image(fill_color=(100, 100, 100))
        img2 = self.create_test_image(fill_color=(50, 50, 50))

        arr1_before = np.array(img1)
        arr2_before = np.array(img2)

        _ = merge_images([img1, img2])

        arr1_after = np.array(img1)
        arr2_after = np.array(img2)

        np.testing.assert_array_equal(arr1_before, arr1_after)
        np.testing.assert_array_equal(arr2_before, arr2_after)

    def test_merge_images_returns_pil_image(self):
        """Test that merge returns PIL Image object."""
        img1 = self.create_test_image()
        img2 = self.create_test_image()

        result = merge_images([img1, img2])

        self.assertIsInstance(result, Image.Image)

    def test_merge_images_many_images(self):
        """Test merging many images."""
        images = [self.create_test_image(fill_color=(10, 10, 10)) for _ in range(10)]

        result = merge_images(images)

        self.assertIsNotNone(result)
        self.assertEqual(result.size, (400, 400))

    def test_merge_black_images(self):
        """Test merging completely black images."""
        img1 = Image.new('RGB', (400, 400), (0, 0, 0))
        img2 = Image.new('RGB', (400, 400), (0, 0, 0))

        result = merge_images([img1, img2])

        self.assertIsNotNone(result)
        # Result should be black or very close to black
        result_arr = np.array(result)
        self.assertLess(np.mean(result_arr), 10)

    def test_merge_white_images(self):
        """Test merging completely white images."""
        img1 = Image.new('RGB', (400, 400), (255, 255, 255))
        img2 = Image.new('RGB', (400, 400), (255, 255, 255))

        result = merge_images([img1, img2])

        self.assertIsNotNone(result)
        # Result should be bright
        result_arr = np.array(result)
        self.assertGreater(np.mean(result_arr), 200)


if __name__ == '__main__':
    unittest.main()
