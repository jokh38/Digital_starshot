"""
Analysis service for Starshot Analyzer.

This service encapsulates the business logic for Starshot analysis, including
image merging, isocenter detection, and running the final analysis. It acts
as a facade over the pure functions in the domain layer, providing a simple
interface for the UI or other clients.
"""

import logging
import tempfile
import os
from typing import List, Tuple
from PIL import Image
import numpy as np
from pylinac import Starshot

from src.domain.image_operations import merge_images
from src.domain.isocenter_detection import (
    detect_laser_isocenter,
    detect_dr_center,
)


class AnalysisService:
    """
    Service for performing Starshot analysis.

    This service orchestrates the domain logic for the entire analysis workflow,
    from merging images to detecting isocenters and running the final pylinac
    analysis. It is designed to be used by the UI layer, decoupling it from the
    underlying domain logic.

    Example:
        >>> service = AnalysisService()
        >>> images = [Image.open("g0.jpg"), Image.open("g90.jpg")]
        >>> merged_image = service.merge_images(images)
        >>> laser_image = np.array(Image.open("laser.jpg").convert("L"))
        >>> laser_x, laser_y = service.detect_laser_isocenter(laser_image)
        >>> # ... and so on
    """

    def __init__(self):
        """Initialize the AnalysisService."""
        self._logger = logging.getLogger(__name__)

    def merge_images(self, image_paths: List[str]) -> Image.Image:
        """
        Load and merge images from a list of file paths.

        Args:
            image_paths: List of file paths to the images to merge.

        Returns:
            A PIL Image object representing the merged image.

        Raises:
            FileNotFoundError: If any of the image paths do not exist.
            ValueError: If the image list is empty or images are invalid.
        """
        if not image_paths:
            raise ValueError("Image paths list cannot be empty.")

        try:
            images = [Image.open(p) for p in image_paths]
            merged = merge_images(images)
            self._logger.info(f"Successfully merged {len(images)} images.")
            return merged
        except FileNotFoundError as e:
            self._logger.error(f"Image not found: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Error merging images: {e}")
            raise ValueError(f"Failed to merge images: {e}")

    def detect_laser_isocenter(self, image_path: str) -> Tuple[float, float]:
        """
        Detect the laser isocenter from an image file.

        Args:
            image_path: Path to the laser image file.

        Returns:
            A tuple (x, y) with the coordinates of the laser isocenter.
        """
        try:
            with Image.open(image_path) as img:
                grayscale_img = img.convert("L")
                image_array = np.array(grayscale_img)
                x, y = detect_laser_isocenter(image_array)
                self._logger.info(f"Detected laser isocenter at ({x:.2f}, {y:.2f})")
                return x, y
        except Exception as e:
            self._logger.error(f"Failed to detect laser isocenter: {e}")
            raise

    def detect_dr_center(self, image_path: str) -> Tuple[int, int]:
        """
        Detect the DR center from an image file.

        Args:
            image_path: Path to the DR image file.

        Returns:
            A tuple (x, y) with the coordinates of the DR center.
        """
        try:
            with Image.open(image_path) as img:
                grayscale_img = img.convert("L")
                image_array = np.array(grayscale_img)
                x, y = detect_dr_center(image_array)
                self._logger.info(f"Detected DR center at ({x}, {y})")
                return x, y
        except Exception as e:
            self._logger.error(f"Failed to detect DR center: {e}")
            raise

    def analyze_starshot(
        self,
        merged_image: Image.Image,
        laser_coords: Tuple[float, float],
        dr_coords: Tuple[int, int],
    ) -> dict:
        """
        Run the full Starshot analysis using pylinac.

        Args:
            merged_image: The merged Starshot image.
            laser_coords: The (x, y) coordinates of the laser isocenter.
            dr_coords: The (x, y) coordinates of the DR center.

        Returns:
            A dictionary containing the analysis results.
        """
        dpmm = 231.5 / 30  # pixels per mm
        dpi = dpmm * 25.4

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            merged_image.save(tmp_file.name)
            tmp_path = tmp_file.name

        try:
            star = Starshot(tmp_path, dpi=dpi, sid=1000)
            star.analyze()

            results_data = star.results_data()
            star_center = results_data.circle_center_x_y

            # Calculate offsets
            laser_offset = (
                (laser_coords[0] - star_center[0]) / dpmm,
                (laser_coords[1] - star_center[1]) / dpmm,
            )
            dr_offset = (
                (dr_coords[0] - star_center[0]) / dpmm,
                (dr_coords[1] - star_center[1]) / dpmm,
            )

            # Save analyzed image to a temporary path
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as analyzed_file:
                analyzed_path = analyzed_file.name

            star.save_analyzed_subimage(analyzed_path)


            results = {
                "passed": results_data.passed,
                "tolerance": results_data.tolerance_mm,
                "circle_diameter_mm": results_data.circle_diameter_mm,
                "radiation_center": star_center,
                "laser_offset_mm": laser_offset,
                "dr_offset_mm": dr_offset,
                "analyzed_image_path": analyzed_path,
            }

            self._logger.info("Starshot analysis complete.")
            return results
        finally:
            os.unlink(tmp_path)