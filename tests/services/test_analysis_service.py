import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
import os

from src.services.analysis_service import AnalysisService

class TestAnalysisService(unittest.TestCase):
    """Unit tests for the AnalysisService."""

    def setUp(self):
        """Set up the test case."""
        self.service = AnalysisService()
        # Create a dummy image for testing
        self.test_image = Image.new("L", (100, 100), color=128)
        self.test_image_path = "test_image.jpg"
        self.test_image.save(self.test_image_path)

    def tearDown(self):
        """Tear down the test case."""
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)

    @patch("src.services.analysis_service.merge_images")
    def test_merge_images_success(self, mock_merge_images):
        """Test successful image merging."""
        mock_merge_images.return_value = self.test_image

        with patch("PIL.Image.open", MagicMock(return_value=self.test_image)):
            result = self.service.merge_images([self.test_image_path, self.test_image_path])

        self.assertEqual(result, self.test_image)
        self.assertEqual(mock_merge_images.call_count, 1)

    def test_merge_images_empty_list(self):
        """Test merging with an empty list of paths."""
        with self.assertRaises(ValueError):
            self.service.merge_images([])

    def test_merge_images_file_not_found(self):
        """Test merging with a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.service.merge_images(["non_existent_file.jpg"])

    @patch("src.services.analysis_service.detect_laser_isocenter")
    def test_detect_laser_isocenter_success(self, mock_detect):
        """Test successful laser isocenter detection."""
        mock_detect.return_value = (50.0, 50.0)

        x, y = self.service.detect_laser_isocenter(self.test_image_path)

        self.assertEqual((x, y), (50.0, 50.0))
        mock_detect.assert_called_once()

    @patch("src.services.analysis_service.detect_dr_center")
    def test_detect_dr_center_success(self, mock_detect):
        """Test successful DR center detection."""
        mock_detect.return_value = (50, 50)

        x, y = self.service.detect_dr_center(self.test_image_path)

        self.assertEqual((x, y), (50, 50))
        mock_detect.assert_called_once()

    @patch("src.services.analysis_service.Starshot")
    def test_analyze_starshot_success(self, mock_starshot):
        """Test the full Starshot analysis workflow."""
        # Mocking pylinac's Starshot class and its methods
        mock_results_data = MagicMock()
        mock_results_data.passed = True
        mock_results_data.tolerance_mm = 0.5
        mock_results_data.circle_diameter_mm = 0.8
        mock_results_data.circle_center_x_y = (50, 50)

        mock_star_instance = MagicMock()
        mock_star_instance.results_data.return_value = mock_results_data
        mock_starshot.return_value = mock_star_instance

        merged_image = Image.new("RGB", (100, 100))
        laser_coords = (51.0, 51.0)
        dr_coords = (49, 49)

        results = self.service.analyze_starshot(merged_image, laser_coords, dr_coords)

        self.assertTrue(results["passed"])
        self.assertIn("analyzed_image_path", results)

        # Clean up the temporary file created by the service
        if os.path.exists(results["analyzed_image_path"]):
            os.remove(results["analyzed_image_path"])

if __name__ == "__main__":
    unittest.main()