"""
Image operations module for medical physics applications.

This module provides pure functions for image manipulation and merging.
All functions are stateless with no side effects or external dependencies.
"""

from typing import List, Optional
from PIL import Image, ImageChops


def merge_images(image_list: List[Image.Image]) -> Optional[Image.Image]:
    """
    Merge multiple PIL images using additive blending.

    This function combines multiple images by adding their pixel values together.
    This is useful for combining multiple exposures or acquisitions of the same
    scene in medical physics applications (e.g., Starshot analysis).

    The function assumes all images have the same mode and dimensions. If no images
    are provided, returns None.

    Args:
        image_list: List of PIL Image objects to merge. All images must be in
                   RGB or L (grayscale) mode and have identical dimensions.

    Returns:
        Optional[Image.Image]: Merged PIL Image object, or None if input list is empty.
                              Result has the same mode and size as input images.

    Raises:
        ValueError: If images have different sizes or incompatible modes.
        TypeError: If input is not a list or contains non-Image objects.

    Example:
        >>> from PIL import Image
        >>> img1 = Image.new('RGB', (400, 400), (100, 100, 100))
        >>> img2 = Image.new('RGB', (400, 400), (50, 50, 50))
        >>> result = merge_images([img1, img2])
        >>> result.size
        (400, 400)

    Note:
        PIL's ImageChops.add() operation can cause clipping at 255. For images
        that combine to values exceeding 255, pixel values will be clipped to 255.
    """
    # Input validation
    if not isinstance(image_list, list):
        raise TypeError("image_list must be a list of PIL Image objects")

    if len(image_list) == 0:
        return None

    # Validate all items are PIL Images
    for img in image_list:
        if not isinstance(img, Image.Image):
            raise TypeError("All items in image_list must be PIL Image objects")

    # Handle single image
    if len(image_list) == 1:
        return image_list[0].copy()

    # Validate all images have same size and mode
    reference_size = image_list[0].size
    reference_mode = image_list[0].mode

    for i, img in enumerate(image_list[1:], start=1):
        if img.size != reference_size:
            raise ValueError(
                f"Image {i} has size {img.size}, expected {reference_size}"
            )
        if img.mode != reference_mode:
            raise ValueError(
                f"Image {i} has mode {img.mode}, expected {reference_mode}"
            )

    # Merge images using additive blending
    merged = image_list[0].copy()

    for img in image_list[1:]:
        merged = ImageChops.add(merged, img)

    return merged
