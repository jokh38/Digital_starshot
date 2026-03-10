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
    DR_ROI_SIZE,
    DR_MIN_CONTOUR_AREA,
    DR_MAX_CONTOUR_AREA,
    LASER_ROI_SIZE,
)


MIN_PROFILE_SIGNAL = 1e-6
LASER_PEAK_RADIUS = 15
LASER_MIN_PEAK_PROMINENCE = 0.15
DR_BACKGROUND_SIGMA = 9.0
DR_RESPONSE_SIGMA = 1.5
DR_MIN_CIRCULARITY = 0.45
DR_MIN_ASPECT_RATIO = 0.55
DR_MAX_CENTER_DISTANCE = 160.0
DR_MIN_DARK_RESPONSE = 5.0


def _extract_center_roi(image_array: np.ndarray, roi_size: int) -> Tuple[np.ndarray, int, int]:
    """Extract a centered ROI and its origin in full-image coordinates."""
    h, w = image_array.shape[:2]
    center_y = h // 2
    center_x = w // 2
    roi_start_y = max(0, center_y - roi_size)
    roi_end_y = min(h, center_y + roi_size)
    roi_start_x = max(0, center_x - roi_size)
    roi_end_x = min(w, center_x + roi_size)
    return image_array[roi_start_y:roi_end_y, roi_start_x:roi_end_x], roi_start_x, roi_start_y


def _refine_profile_peak(
    profile: np.ndarray,
    peak_index: int,
    radius: int = LASER_PEAK_RADIUS,
) -> Tuple[float, float]:
    """Return a subpixel centroid and normalized prominence around a 1D peak."""
    lo = max(0, peak_index - radius)
    hi = min(len(profile), peak_index + radius + 1)
    window = profile[lo:hi]
    weight_sum = float(window.sum())
    if weight_sum <= MIN_PROFILE_SIGNAL:
        raise ValueError("Insufficient signal to refine peak")

    coords = np.arange(lo, hi, dtype=np.float64)
    centroid = float(np.dot(coords, window) / weight_sum)
    baseline = float(np.median(profile))
    prominence = float(profile[peak_index] - baseline)
    normalized_prominence = prominence / max(float(profile[peak_index]), 1.0)
    return centroid, normalized_prominence


def _component_score(
    *,
    area: int,
    aspect_ratio: float,
    circularity: float,
    darkness: float,
    distance: float,
) -> float:
    """Score a DR-ball candidate with shape, contrast, and center proximity."""
    return (
        area
        * max(aspect_ratio, 1e-6)
        * max(circularity, 1e-6)
        * max(darkness, 1e-6)
        / (1.0 + distance / 50.0)
    )


def detect_laser_isocenter(
    image_array: np.ndarray,
    roi_size: int = LASER_ROI_SIZE
) -> Tuple[float, float]:
    """
    Detect laser isocenter position from a laser cross image.

    This function analyzes the bright green vertical and horizontal laser lines
    in a centered ROI. It isolates green-dominant pixels, sums the signal along
    rows and columns, and refines the brightest row/column peaks to subpixel
    precision. The crossing of those peaks is the estimated laser isocenter.

    Args:
        image_array: Numpy array representing the image. Accepted shapes are
                    grayscale (height, width) or RGB/BGR-like (height, width, 3).
        roi_size: Region of interest size in pixels around image center (default: 200).

    Returns:
        Tuple[float, float]: (x, y) coordinates of detected laser isocenter.
                            Coordinates are relative to the full image, not ROI.

    Raises:
        ValueError: If image_array shape is unsupported, empty, or the laser
                    signal is too weak to locate confidently.
        TypeError: If image_array is not a numpy array.
    """
    # Input validation
    if not isinstance(image_array, np.ndarray):
        raise TypeError("image_array must be a numpy array")

    if image_array.size == 0:
        raise ValueError("image_array cannot be empty")

    if image_array.ndim == 2:
        green_signal = image_array.astype(np.float32)
    elif image_array.ndim == 3 and image_array.shape[2] >= 3:
        image_float = image_array.astype(np.float32)
        green_signal = np.clip(
            image_float[:, :, 1] - np.maximum(image_float[:, :, 0], image_float[:, :, 2]),
            0,
            None,
        )
    else:
        raise ValueError("image_array must be 2D grayscale or 3-channel color")

    crop_roi, roi_start_x, roi_start_y = _extract_center_roi(green_signal, roi_size)
    if crop_roi.size == 0:
        raise ValueError("ROI is empty")

    crop_roi = cv2.GaussianBlur(crop_roi, (0, 0), 2.0)
    column_profile = crop_roi.sum(axis=0)
    row_profile = crop_roi.sum(axis=1)

    if float(column_profile.max()) <= MIN_PROFILE_SIGNAL or float(row_profile.max()) <= MIN_PROFILE_SIGNAL:
        raise ValueError("Laser signal too weak to detect")

    peak_x = int(np.argmax(column_profile))
    peak_y = int(np.argmax(row_profile))
    refined_x, x_prominence = _refine_profile_peak(column_profile, peak_x)
    refined_y, y_prominence = _refine_profile_peak(row_profile, peak_y)

    if min(x_prominence, y_prominence) < LASER_MIN_PEAK_PROMINENCE:
        raise ValueError("Laser signal is ambiguous")

    return float(roi_start_x + refined_x), float(roi_start_y + refined_y)


def detect_dr_center(
    image_array: np.ndarray,
    roi_size: int = DR_ROI_SIZE,
    min_area: int = DR_MIN_CONTOUR_AREA,
    max_area: int = DR_MAX_CONTOUR_AREA
) -> Tuple[int, int]:
    """
    Detect DR (Digital Radiography) ball center from an image.

    This function identifies the small dark lead ball in a DR image with bright
    and potentially reflective background. It estimates a smooth local background,
    subtracts it to emphasize dark localized objects, and scores connected
    components by size, circularity, compactness, darkness, and distance from
    the image center.

    Args:
        image_array: Grayscale numpy array (height, width) representing the image.
        roi_size: Region of interest size in pixels around image center (default: 200).
        min_area: Minimum contour area in pixels² to consider (default: 10).
        max_area: Maximum contour area in pixels² to consider (default: 500).

    Returns:
        Tuple[int, int]: (x, y) coordinates of detected DR center.
                        Coordinates are relative to the full image, not ROI.

    Raises:
        ValueError: If image_array is not 2D, is empty, max_area < min_area, or
                    no plausible lead-ball candidate is detected.
        TypeError: If image_array is not a numpy array.
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

    crop_roi, roi_start_x, roi_start_y = _extract_center_roi(image_array, roi_size)
    if crop_roi.size == 0:
        raise ValueError("ROI is empty")

    blurred = cv2.GaussianBlur(crop_roi, (0, 0), DR_BACKGROUND_SIGMA)
    dark_response = np.clip(blurred.astype(np.float32) - crop_roi.astype(np.float32), 0, None)
    dark_response = cv2.GaussianBlur(dark_response, (0, 0), DR_RESPONSE_SIGMA)

    if float(dark_response.max()) < DR_MIN_DARK_RESPONSE:
        raise ValueError("No dark lead-ball candidate detected")

    scaled = np.uint8(np.clip(255 * dark_response / float(dark_response.max()), 0, 255))
    _, thresholded = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresholded = cv2.morphologyEx(
        thresholded,
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
    )

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresholded, connectivity=8)
    roi_center = np.array([crop_roi.shape[1] / 2.0, crop_roi.shape[0] / 2.0], dtype=np.float64)

    best_candidate: Tuple[float, float, float] | None = None

    for label_index in range(1, num_labels):
        area = int(stats[label_index, cv2.CC_STAT_AREA])
        if area < min_area or area > max_area:
            continue

        width = int(stats[label_index, cv2.CC_STAT_WIDTH])
        height = int(stats[label_index, cv2.CC_STAT_HEIGHT])
        aspect_ratio = min(width, height) / max(width, height)
        if aspect_ratio < DR_MIN_ASPECT_RATIO:
            continue

        component_mask = np.uint8(labels == label_index) * 255
        contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        contour = max(contours, key=cv2.contourArea)
        perimeter = cv2.arcLength(contour, closed=True)
        if perimeter <= 0:
            continue

        circularity = float(4.0 * np.pi * area / (perimeter * perimeter))
        if circularity < DR_MIN_CIRCULARITY:
            continue

        candidate_center = centroids[label_index]
        distance = float(np.linalg.norm(candidate_center - roi_center))
        if distance > DR_MAX_CENTER_DISTANCE:
            continue

        darkness = float(dark_response[labels == label_index].mean())
        score = _component_score(
            area=area,
            aspect_ratio=aspect_ratio,
            circularity=circularity,
            darkness=darkness,
            distance=distance,
        )

        if best_candidate is None or score > best_candidate[2]:
            best_candidate = (float(candidate_center[0]), float(candidate_center[1]), score)

    if best_candidate is None:
        raise ValueError("No plausible lead-ball candidate detected")

    return int(round(roi_start_x + best_candidate[0])), int(round(roi_start_y + best_candidate[1]))
