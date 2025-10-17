# Domain Layer Documentation

## Overview

The domain layer contains pure business logic for the Starshot medical physics analyzer. All functions in this layer are:

- **Pure**: No side effects, no file I/O, no external state
- **Testable**: Can be tested without UI, hardware, or camera dependencies
- **Stateless**: Functions only depend on their parameters
- **Type-safe**: Full type hints for all parameters and return values

## Module Structure

### src/domain/isocenter_detection.py

Core image processing algorithms for detecting laser and DR isocenters.

#### Key Functions

##### `detect_laser_isocenter(image_array, roi_size=200) -> Tuple[float, float]`

Detects the laser crosshair isocenter position using line detection and RANSAC regression.

**Parameters:**
- `image_array` (np.ndarray): Grayscale image with laser crosshair pattern
- `roi_size` (int): Region of interest size in pixels around image center

**Returns:**
- Tuple[float, float]: (x, y) coordinates of detected laser isocenter

**Algorithm:**
1. Extract ROI centered on image middle
2. Apply Gaussian blur for noise reduction
3. Apply Otsu threshold to create binary image
4. Analyze multiple cross-sections of the image
5. Fit lines to detected pixels using RANSAC regression
6. Calculate intersection point of horizontal and vertical lines

**Example:**
```python
import numpy as np
from src.domain.isocenter_detection import detect_laser_isocenter

# Create grayscale image with laser lines
image = np.zeros((400, 400), dtype=np.uint8)
image[200, 150:250] = 255  # Horizontal line
image[150:250, 200] = 255  # Vertical line

# Detect center
x, y = detect_laser_isocenter(image)
print(f"Laser isocenter: ({x}, {y})")
```

##### `detect_dr_center(image_array, roi_size=200, min_area=10, max_area=500) -> Tuple[int, int]`

Detects the DR (Digital Radiography) center marker position using contour analysis.

**Parameters:**
- `image_array` (np.ndarray): Grayscale image with DR marker
- `roi_size` (int): Region of interest size in pixels
- `min_area` (int): Minimum contour area filter (pixels²)
- `max_area` (int): Maximum contour area filter (pixels²)

**Returns:**
- Tuple[int, int]: (x, y) coordinates of detected DR center

**Algorithm:**
1. Extract ROI centered on image middle
2. Apply Gaussian blur for noise reduction
3. Apply Otsu threshold to create binary image
4. Find all contours in binary image
5. Filter contours by area to remove noise
6. Calculate center of mass for largest contour

**Example:**
```python
import numpy as np
from src.domain.isocenter_detection import detect_dr_center

# Create grayscale image with circular DR marker
image = np.zeros((400, 400), dtype=np.uint8)
y, x = np.ogrid[:400, :400]
mask = (x - 200) ** 2 + (y - 200) ** 2 <= 20 ** 2
image[mask] = 255

# Detect center
x, y = detect_dr_center(image)
print(f"DR center: ({x}, {y})")
```

#### Constants

All magic numbers have been extracted to module-level constants:

| Constant | Value | Purpose |
|----------|-------|---------|
| LASER_ROI_SIZE | 200 | Default ROI size for laser detection |
| LASER_GAUSSIAN_KERNEL | (5, 5) | Kernel size for Gaussian blur |
| LASER_GAUSSIAN_SIGMA | 0 | Sigma for Gaussian blur |
| LASER_LINE_ITERATIONS | 10 | Number of cross-sections to analyze |
| LASER_LINE_THRESHOLD | 10 | Pixel value threshold for line detection |
| LASER_RANSAC_THRESHOLD | 2.0 | RANSAC outlier threshold (pixels) |
| LASER_SLOPE_TOLERANCE | 1/100 | Tolerance for line parallelism check |
| LASER_CENTER_BOX_SIZE | 4 | Size of visualization box around center |
| DR_ROI_SIZE | 200 | Default ROI size for DR detection |
| DR_GAUSSIAN_KERNEL | (5, 5) | Kernel size for Gaussian blur |
| DR_GAUSSIAN_SIGMA | 0 | Sigma for Gaussian blur |
| DR_MIN_CONTOUR_AREA | 10 | Default minimum contour area |
| DR_MAX_CONTOUR_AREA | 500 | Default maximum contour area |
| DR_CENTER_BOX_SIZE | 4 | Size of visualization box around center |
| DR_MOMENT_THRESHOLD | 1e-10 | Threshold for moment calculation |

### src/domain/image_operations.py

Image manipulation and merging operations.

#### Key Functions

##### `merge_images(image_list) -> Optional[Image.Image]`

Merges multiple PIL images using additive blending (pixel value addition).

**Parameters:**
- `image_list` (List[Image.Image]): List of PIL Image objects to merge

**Returns:**
- Optional[Image.Image]: Merged image, or None if input list is empty

**Raises:**
- `ValueError`: If images have different sizes or modes
- `TypeError`: If input is not a list or contains non-Image objects

**Algorithm:**
1. Validate input is list of PIL Images
2. Check all images have same size and mode
3. Use PIL's ImageChops.add() for additive blending
4. Apply additive blending sequentially to all images

**Example:**
```python
from PIL import Image
from src.domain.image_operations import merge_images

# Load images
img1 = Image.open("starshot_angle1.jpg")
img2 = Image.open("starshot_angle2.jpg")
img3 = Image.open("starshot_angle3.jpg")

# Merge images
merged = merge_images([img1, img2, img3])

# Save result
merged.save("starshot_merged.jpg")
```

## Error Handling

All functions include comprehensive error handling:

- **Type validation**: Checks parameter types before processing
- **Dimension validation**: Ensures arrays/images have correct dimensions
- **Value validation**: Validates parameter ranges and relationships
- **Graceful degradation**: Returns sensible defaults when detection fails

Example error cases:

```python
import numpy as np
from src.domain.isocenter_detection import detect_laser_isocenter

# TypeError: image_array must be a numpy array
try:
    detect_laser_isocenter([1, 2, 3])
except TypeError as e:
    print(f"Error: {e}")

# ValueError: image_array must be 2-dimensional
try:
    detect_laser_isocenter(np.zeros((10, 10, 3)))
except ValueError as e:
    print(f"Error: {e}")
```

## Testing

Comprehensive test suite with 29 test cases covering:

### Image Operations Tests (13 tests)
- Empty list handling
- Single and multiple image merging
- Different image sizes and modes
- Pixel value preservation and addition
- Input immutability
- Edge cases (black/white images)

### Isocenter Detection Tests (16 tests)
- Laser center detection (centered, offset, various ROI sizes)
- DR center detection (circles, multiple markers, area filtering)
- Edge cases (empty images, small images, no markers)
- Type and return value validation
- Custom parameter handling

**Test Execution:**
```bash
# Run all domain tests
python3 -m pytest tests/domain/ -v

# Run with coverage report
python3 -m pytest tests/domain/ --cov=src/domain --cov-report=html

# Run specific test file
python3 -m pytest tests/domain/test_isocenter_detection.py -v
```

**Current Coverage:** 87% (134 statements, 18 uncovered)

## Usage in Applications

### Example: Medical Physics Analysis Pipeline

```python
import cv2
import numpy as np
from PIL import Image
from src.domain.isocenter_detection import detect_laser_isocenter, detect_dr_center
from src.domain.image_operations import merge_images

# 1. Load and merge Starshot images
starshot_images = [Image.open(f) for f in starshot_files]
merged_image = merge_images(starshot_images)

# 2. Detect laser isocenter
laser_image = np.array(Image.open("laser_image.jpg").convert("L"))
laser_x, laser_y = detect_laser_isocenter(laser_image)

# 3. Detect DR center
dr_image = np.array(Image.open("dr_image.jpg").convert("L"))
dr_x, dr_y = detect_dr_center(dr_image)

# 4. Results ready for analysis
print(f"Laser isocenter: ({laser_x}, {laser_y})")
print(f"DR center: ({dr_x}, {dr_y})")
```

## Dependencies

- **numpy**: Array operations and numerical computing
- **opencv-python**: Image processing (Gaussian blur, thresholding, contours)
- **scikit-learn**: RANSAC regression for line fitting
- **Pillow**: Image I/O and manipulation

## Design Principles

1. **Separation of Concerns**: Domain logic separated from UI and I/O
2. **Pure Functions**: No side effects make testing straightforward
3. **Type Safety**: Full type hints enable static analysis and IDE support
4. **Testability**: All functions testable without external dependencies
5. **Documentation**: Comprehensive docstrings with examples
6. **Maintainability**: Clear naming, magic number constants, single responsibility

## Future Extensions

Potential areas for expansion:

1. **Advanced Edge Detection**: Sobel, Canny operators for improved line detection
2. **Multi-Modal Analysis**: Support for different image types and modalities
3. **Batch Processing**: Optimize for processing multiple images efficiently
4. **Validation Functions**: Add pre/post-condition validators
5. **Performance Metrics**: Return confidence scores with detections

## Related Documentation

- See `../README.md` for project overview
- See `REFACTORING_NOTES.md` for architectural decisions
- See `../Starshot_250303.py` for UI layer implementation
