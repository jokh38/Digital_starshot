"""
Isocenter detection module for medical physics analysis.

This module contains pure functions for detecting laser and DR isocenters
from medical imaging data. All functions are stateless and have no side effects.

Constants are imported from the centralized constants module.
"""

import numpy as np
import cv2
from typing import Tuple

from .constants import (
    LASER_ROI_SIZE,
    LASER_GAUSSIAN_KERNEL,
    LASER_GAUSSIAN_SIGMA,
    LASER_LINE_ITERATIONS,
    LASER_LINE_THRESHOLD,
    LASER_RANSAC_THRESHOLD,
    LASER_SLOPE_TOLERANCE,
    DR_ROI_SIZE,
    DR_GAUSSIAN_KERNEL,
    DR_GAUSSIAN_SIGMA,
    DR_MIN_CONTOUR_AREA,
    DR_MAX_CONTOUR_AREA,
    DR_MOMENT_THRESHOLD,
)


def _fit_line_robustly(
    x_values: np.ndarray,
    y_values: np.ndarray,
    residual_threshold: float,
) -> Tuple[float, float]:
    """Fit y = mx + b with iterative outlier trimming."""
    if len(x_values) < 2:
        return 0.0, float(np.mean(y_values))

    inlier_mask = np.ones(len(x_values), dtype=bool)

    for _ in range(4):
        active_x = x_values[inlier_mask]
        active_y = y_values[inlier_mask]
        if len(active_x) < 2:
            break

        slope, intercept = np.polyfit(active_x, active_y, 1)
        residuals = np.abs(y_values - (slope * x_values + intercept))
        updated_mask = residuals <= residual_threshold

        if updated_mask.sum() < 2:
            break
        if np.array_equal(updated_mask, inlier_mask):
            return float(slope), float(intercept)
        inlier_mask = updated_mask

    active_x = x_values[inlier_mask]
    active_y = y_values[inlier_mask]
    if len(active_x) < 2:
        return 0.0, float(np.mean(y_values))

    slope, intercept = np.polyfit(active_x, active_y, 1)
    return float(slope), float(intercept)


def detect_laser_isocenter(
    image_array: np.ndarray,
    roi_size: int = LASER_ROI_SIZE
) -> Tuple[float, float]:
    """
    Detect laser isocenter position from a grayscale image.

    This function analyzes a laser crosshair pattern to find the precise center
    position using line detection and RANSAC regression. The function expects
    a grayscale image with a laser crosshair pattern (vertical and horizontal lines).

    Args:
        image_array: Grayscale numpy array (height, width) representing the image.
                    Values should be in range [0, 255].
        roi_size: Region of interest size in pixels around image center (default: 200).

    Returns:
        Tuple[float, float]: (x, y) coordinates of detected laser isocenter.
                            Coordinates are relative to the full image, not ROI.

    Raises:
        ValueError: If image_array is not 2D or is empty.
        TypeError: If image_array is not a numpy array.

    Example:
        >>> import numpy as np
        >>> image = np.zeros((400, 400), dtype=np.uint8)
        >>> image[200, 150:250] = 255  # Horizontal line
        >>> image[150:250, 200] = 255  # Vertical line
        >>> x, y = detect_laser_isocenter(image)
    """
    # Input validation
    if not isinstance(image_array, np.ndarray):
        raise TypeError("image_array must be a numpy array")

    if image_array.ndim != 2:
        raise ValueError("image_array must be 2-dimensional")

    if image_array.size == 0:
        raise ValueError("image_array cannot be empty")

    h, w = image_array.shape

    # Extract ROI centered on image center
    roi_start_y = max(0, int(h / 2) - roi_size)
    roi_end_y = min(h, int(h / 2) + roi_size)
    roi_start_x = max(0, int(w / 2) - roi_size)
    roi_end_x = min(w, int(w / 2) + roi_size)

    crop_roi = image_array[roi_start_y:roi_end_y, roi_start_x:roi_end_x]

    # Apply Gaussian blur to smooth the image
    blurred = cv2.GaussianBlur(crop_roi, LASER_GAUSSIAN_KERNEL, LASER_GAUSSIAN_SIGMA)

    # Apply threshold to create binary image
    _, tmp_thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    thresh = ~tmp_thresh  # Invert threshold

    size_v, _ = crop_roi.shape

    # Analyze multiple cross-sections
    pos_vert = []
    pos_horz = []
    xy_pos = np.zeros(LASER_LINE_ITERATIONS - 1)

    for i in range(LASER_LINE_ITERATIONS - 1):
        idx = int((size_v / LASER_LINE_ITERATIONS) * (i + 1))
        line_vert = thresh[:, idx]
        line_horz = thresh[idx, :]

        xy_pos[i] = idx

        # Find center of lines
        vert_pixels = np.where(line_vert < LASER_LINE_THRESHOLD)[0]
        horz_pixels = np.where(line_horz < LASER_LINE_THRESHOLD)[0]

        pos_vert.append(np.mean(vert_pixels) if len(vert_pixels) > 0 else idx)
        pos_horz.append(np.mean(horz_pixels) if len(horz_pixels) > 0 else idx)

    pos_vert = np.array(pos_vert)
    pos_horz = np.array(pos_horz)

    hor_x = xy_pos
    hor_y = pos_horz
    ver_x = xy_pos
    ver_y = pos_vert

    hor_slope, hor_intercept = _fit_line_robustly(
        hor_x, hor_y, LASER_RANSAC_THRESHOLD
    )
    ver_slope, ver_intercept = _fit_line_robustly(
        ver_x, ver_y, LASER_RANSAC_THRESHOLD
    )

    # Horizontal slices estimate x as a function of y; vertical slices estimate
    # y as a function of x. Solve the two fitted lines for their intersection.
    determinant = 1.0 - (hor_slope * ver_slope)
    if abs(determinant) > LASER_SLOPE_TOLERANCE:
        laser_x = roi_start_x + (
            (hor_slope * ver_intercept + hor_intercept) / determinant
        )
        laser_y = roi_start_y + (ver_slope * (laser_x - roi_start_x) + ver_intercept)
    else:
        laser_x = roi_start_x + float(np.mean(pos_horz))
        laser_y = roi_start_y + float(np.mean(pos_vert))

    return float(laser_x), float(laser_y)


def detect_dr_center(
    image_array: np.ndarray,
    roi_size: int = DR_ROI_SIZE,
    min_area: int = DR_MIN_CONTOUR_AREA,
    max_area: int = DR_MAX_CONTOUR_AREA
) -> Tuple[int, int]:
    """
    Detect DR (Digital Radiography) center from an image.

    This function identifies circular markers in a digital radiography image
    by finding contours within a specified area range and calculating their
    center of mass. The function uses Gaussian blur and Otsu thresholding
    to enhance the marker detection.

    Args:
        image_array: Grayscale numpy array (height, width) representing the image.
                    Values should be in range [0, 255].
        roi_size: Region of interest size in pixels around image center (default: 200).
        min_area: Minimum contour area in pixels² to consider (default: 10).
        max_area: Maximum contour area in pixels² to consider (default: 500).

    Returns:
        Tuple[int, int]: (x, y) coordinates of detected DR center.
                        Coordinates are relative to the full image, not ROI.

    Raises:
        ValueError: If image_array is not 2D, is empty, or max_area < min_area.
        TypeError: If image_array is not a numpy array.

    Example:
        >>> import numpy as np
        >>> image = np.zeros((400, 400), dtype=np.uint8)
        >>> # Create circular marker at center
        >>> y, x = np.ogrid[:400, :400]
        >>> mask = (x - 200) ** 2 + (y - 200) ** 2 <= 20 ** 2
        >>> image[mask] = 255
        >>> cx, cy = detect_dr_center(image)
    """
    # Input validation
    if not isinstance(image_array, np.ndarray):
        raise TypeError("image_array must be a numpy array")

    if image_array.ndim != 2:
        raise ValueError("image_array must be 2-dimensional")

    if image_array.size == 0:
        raise ValueError("image_array cannot be empty")

    if max_area < min_area:
        raise ValueError("max_area must be greater than or equal to min_area")

    h, w = image_array.shape

    # Extract ROI centered on image center
    roi_start_y = max(0, int(h / 2) - roi_size)
    roi_end_y = min(h, int(h / 2) + roi_size)
    roi_start_x = max(0, int(w / 2) - roi_size)
    roi_end_x = min(w, int(w / 2) + roi_size)

    crop_roi = image_array[roi_start_y:roi_end_y, roi_start_x:roi_end_x]

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(crop_roi, DR_GAUSSIAN_KERNEL, DR_GAUSSIAN_SIGMA)

    # Apply Otsu threshold
    _, tmp_thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    thresh = ~tmp_thresh  # Invert threshold

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by area
    filtered_contours = [
        cnt for cnt in contours
        if min_area < cv2.contourArea(cnt) < max_area
    ]

    # Default: return ROI center if no contours found
    dr_x = roi_start_x + int(w / 2) - roi_start_x
    dr_y = roi_start_y + int(h / 2) - roi_start_y

    if filtered_contours:
        # Find largest contour
        largest_contour = max(filtered_contours, key=cv2.contourArea)

        # Calculate moments (center of mass)
        M = cv2.moments(largest_contour)

        if M["m00"] > DR_MOMENT_THRESHOLD:
            dr_x = roi_start_x + int(M["m10"] / M["m00"])
            dr_y = roi_start_y + int(M["m01"] / M["m00"])

    return int(dr_x), int(dr_y)
