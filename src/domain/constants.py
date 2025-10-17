"""
Medical physics constants for Starshot analysis.

This module centralizes all magic numbers extracted from the original
monolithic implementation. All constants represent medical physics parameters
used in laser and DR isocenter detection algorithms.

Constants are organized by detection method and can be easily tuned for
different imaging conditions or equipment configurations.
"""

# =============================================================================
# LASER ISOCENTER DETECTION CONSTANTS
# =============================================================================

# Image Processing Parameters
LASER_ROI_SIZE = 200
"""Region of interest size in pixels around image center for laser detection."""

LASER_GAUSSIAN_KERNEL = (5, 5)
"""Gaussian blur kernel size (width, height) for noise reduction."""

LASER_GAUSSIAN_SIGMA = 0
"""Gaussian blur sigma parameter. 0 means auto-calculate from kernel size."""

# Line Detection Parameters
LASER_LINE_ITERATIONS = 10
"""Number of cross-sections to analyze for line detection."""

LASER_LINE_THRESHOLD = 10
"""Pixel intensity threshold for line detection (0-255)."""

# RANSAC Regression Parameters
LASER_RANSAC_THRESHOLD = 2.0
"""Outlier threshold in pixels for RANSAC line fitting."""

LASER_SLOPE_TOLERANCE = 1 / 100
"""Tolerance for checking if lines are parallel (slope difference)."""

# Visualization Parameters
LASER_CENTER_BOX_SIZE = 4
"""Size in pixels of center marker box for visualization."""

# =============================================================================
# DR CENTER DETECTION CONSTANTS
# =============================================================================

# Image Processing Parameters
DR_ROI_SIZE = 200
"""Region of interest size in pixels around image center for DR detection."""

DR_GAUSSIAN_KERNEL = (5, 5)
"""Gaussian blur kernel size (width, height) for noise reduction."""

DR_GAUSSIAN_SIGMA = 0
"""Gaussian blur sigma parameter. 0 means auto-calculate from kernel size."""

# Contour Detection Parameters
DR_MIN_CONTOUR_AREA = 10
"""Minimum contour area in pixels² to consider as valid marker."""

DR_MAX_CONTOUR_AREA = 500
"""Maximum contour area in pixels² to consider as valid marker."""

DR_MOMENT_THRESHOLD = 1e-10
"""Threshold for image moment calculation to avoid division by zero."""

# Visualization Parameters
DR_CENTER_BOX_SIZE = 4
"""Size in pixels of center marker box for visualization."""

# =============================================================================
# VALIDATION RANGES
# =============================================================================

# Reasonable ranges for parameter validation
MIN_ROI_SIZE = 50
"""Minimum allowed ROI size in pixels."""

MAX_ROI_SIZE = 1000
"""Maximum allowed ROI size in pixels."""

MIN_KERNEL_SIZE = 3
"""Minimum allowed Gaussian kernel size."""

MAX_KERNEL_SIZE = 15
"""Maximum allowed Gaussian kernel size."""

MIN_CONTOUR_AREA = 1
"""Minimum allowed contour area."""

MAX_CONTOUR_AREA = 10000
"""Maximum allowed contour area."""
