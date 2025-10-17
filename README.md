# Digital Starshot Analyzer

A medical physics quality assurance application for Starshot beam geometry analysis with clean architecture. This project implements a complete separation of concerns with domain logic, service layer, and UI layer following Clean Architecture principles.

## Project Structure

```
Digital_starshot/
├── src/
│   ├── domain/                     # Pure business logic (no dependencies)
│   │   ├── isocenter_detection.py # Laser/DR center detection algorithms
│   │   ├── image_operations.py    # Image merging and manipulation
│   │   └── constants.py           # Configuration constants
│   ├── services/                   # Application services
│   │   ├── analysis_service.py    # Starshot analysis orchestration
│   │   ├── video_stream_service.py # Video streaming and frame capture
│   │   └── config_service.py      # Configuration management
│   ├── ui/                         # User interface layer
│   │   ├── main_window.py         # Main Tkinter window
│   │   └── config_editor.py       # Configuration editor dialog
│   └── app.py                      # Application entry point and controller
├── tests/
│   ├── domain/                     # Unit tests for domain logic
│   │   ├── test_isocenter_detection.py
│   │   └── test_image_operations.py
│   └── services/                   # Service layer tests
│       ├── test_analysis_service.py
│       ├── test_video_stream_service.py
│       └── test_config_service.py
├── docs/
│   └── DOMAIN_LAYER.md             # Detailed API documentation
├── requirements.txt                # Python dependencies
├── config.ini                      # Application configuration
└── README.md                       # This file
```

## Quick Start

### Installation

```bash
# Clone or download the repository
cd Digital_starshot

# Install dependencies
python3 -m pip install -r requirements.txt
```

### Running the Application

```bash
# Run the Starshot Analyzer GUI application
python3 -m src.app

# Or run directly
python3 src/app.py
```

### Running Tests

```bash
# Run all domain tests
python3 -m pytest tests/domain/ -v

# Run with coverage report
python3 -m pytest tests/domain/ --cov=src/domain --cov-report=html

# Run specific test file
python3 -m pytest tests/domain/test_isocenter_detection.py -v
```

### Configuration

Edit `config.ini` to configure:
- Network settings (IP address, port)
- Image crop parameters
- Starshot analysis parameters
- File paths

Or use the built-in Configuration Editor in the GUI application (Settings > Edit Configuration).

## Application Features

### Video Streaming
- Connect to network camera via MJPEG stream
- Real-time video display with configurable cropping
- Frame capture for analysis

### Image Capture and Analysis
- **Laser Isocenter Detection**: Automatically detect laser crosshair center using line fitting and RANSAC regression
- **DR Center Detection**: Detect Digital Radiography center marker using contour analysis
- **Starline Capture**: Capture brightest frame during gantry rotation
- **Image Merging**: Merge multiple Starshot images using additive blending

### Starshot Analysis
- Complete Starshot analysis using pylinac library
- Calculate minimum circle diameter
- Compute offsets between radiation center, laser isocenter, and DR center
- Visual analysis results with overlaid measurements
- Pass/fail determination based on tolerance

### Configuration Management
- INI-based configuration file
- GUI configuration editor
- Network, crop, and analysis parameter settings

## Architecture Overview

### Clean Architecture Layers

The application follows Clean Architecture principles with clear separation of concerns:

1. **Domain Layer** (`src/domain/`): Pure business logic
   - No external dependencies
   - Pure functions with no side effects
   - Fully testable in isolation
   - Core algorithms for detection and image processing

2. **Service Layer** (`src/services/`): Application orchestration
   - Bridges domain logic and external systems
   - Manages I/O operations (files, network, configuration)
   - Coordinates workflows between domain functions
   - Handles logging and error recovery

3. **UI Layer** (`src/ui/`): User interface
   - Tkinter-based GUI components
   - Event handling and user interactions
   - Display logic only

4. **Application Controller** (`src/app.py`): Main coordinator
   - Wires together all layers
   - Manages application lifecycle
   - Handles user events and delegates to services

## Test Results

```
============================== test session starts ==============================
Platform: Linux Python 3.10.12

tests/domain/test_image_operations.py::TestMergeImages                 13 PASSED
tests/domain/test_isocenter_detection.py::TestDetectLaserIsocenter      7 PASSED
tests/domain/test_isocenter_detection.py::TestDetectDRCenter            9 PASSED

============================= 29 passed in 0.68s ==============================

Coverage: 87% (domain layer fully tested)
```

## Key Features

### Clean Architecture
- **Separation of Concerns**: Domain, Service, and UI layers clearly separated
- **Testability**: Domain layer has 87% test coverage with 29 unit tests
- **Maintainability**: Single Responsibility Principle applied throughout
- **Extensibility**: Easy to add new features or swap implementations

### Pure Domain Logic
- No side effects in core business logic
- Stateless operations
- Easy to test and reason about
- Reusable in any context (CLI, API, GUI)

### Type Safety
- Complete type hints for all functions
- Static type checking support
- IDE autocomplete support

### Comprehensive Documentation
- Detailed docstrings with examples
- API reference with parameter descriptions
- Algorithm explanations (see `docs/DOMAIN_LAYER.md`)

### Robust Error Handling
- Input validation for all parameters
- Graceful degradation on failures
- Comprehensive logging throughout application
- Informative error messages

### High Test Coverage
- 29 unit tests for domain layer
- Tests for edge cases and error conditions
- 87% code coverage for domain layer
- No test dependencies on UI or hardware

## Algorithm Details

### Laser Isocenter Detection

Detects the center of a laser crosshair pattern using:

1. **ROI Extraction:** Extract centered region of interest
2. **Preprocessing:** Gaussian blur to reduce noise
3. **Thresholding:** Otsu automatic threshold to create binary image
4. **Line Analysis:** Analyze multiple horizontal/vertical cross-sections
5. **Fitting:** Use RANSAC regression for robust line fitting
6. **Intersection:** Calculate intersection of fitted lines

Returns: Isocenter coordinates as (x, y) floats

### DR Center Detection

Detects DR marker center using:

1. **ROI Extraction:** Extract centered region of interest
2. **Preprocessing:** Gaussian blur to reduce noise
3. **Thresholding:** Otsu automatic threshold to create binary image
4. **Contour Detection:** Find all contours in binary image
5. **Filtering:** Filter contours by area (remove noise)
6. **Center of Mass:** Calculate centroid of largest remaining contour

Returns: Center coordinates as (x, y) integers

### Image Merging

Combines multiple images through additive blending:

1. **Validation:** Verify all images same size and mode
2. **Merging:** Apply additive blending (pixel-by-pixel addition)
3. **Clipping:** Values exceeding 255 are clipped

Returns: Merged PIL Image object

## Configuration Constants

All magic numbers have been extracted to module-level constants for easy tuning:

### Laser Detection Parameters
- `LASER_ROI_SIZE`: Window size for center region (default: 200px)
- `LASER_GAUSSIAN_KERNEL`: Blur kernel size (default: 5x5)
- `LASER_LINE_ITERATIONS`: Number of cross-sections to analyze (default: 10)
- `LASER_RANSAC_THRESHOLD`: Outlier threshold for line fitting (default: 2.0px)
- `LASER_SLOPE_TOLERANCE`: Tolerance for checking line parallelism (default: 1/100)

### DR Detection Parameters
- `DR_ROI_SIZE`: Window size for center region (default: 200px)
- `DR_MIN_CONTOUR_AREA`: Minimum contour size to consider (default: 10px²)
- `DR_MAX_CONTOUR_AREA`: Maximum contour size to consider (default: 500px²)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | >=1.19 | Array operations |
| opencv-python | >=4.5 | Image processing and video streaming |
| scikit-learn | >=0.24 | RANSAC regression |
| Pillow | >=8.0 | Image I/O and manipulation |
| pylinac | >=2.8 | Starshot analysis algorithms |
| pytest | >=6.0 | Testing framework |
| pytest-cov | >=2.12 | Coverage reporting |
| black | >=21.0 | Code formatting (optional) |
| flake8 | >=3.9 | Linting (optional) |
| mypy | >=0.910 | Static type checking (optional) |

## Performance

### Computational Complexity
- Laser detection: O(n·m) where n,m are image dimensions
- DR detection: O(n·m) for contour finding
- Image merging: O(n·m·c) where c is color channels

### Typical Execution Times (400x400 image)
- Laser detection: ~50-100ms
- DR detection: ~30-80ms
- Image merging: ~20-50ms

## Benefits of Clean Architecture

1. **Testability:** 87% code coverage with comprehensive domain unit tests
2. **Reusability:** Domain functions work in any context (CLI, API, batch processing)
3. **Maintainability:** Clear module boundaries and responsibilities
4. **Extensibility:** Easy to add new features, swap implementations, or integrate with other systems
5. **Independence:** Domain logic independent of frameworks, UI, database, or external systems
6. **Performance:** Optimizations possible without UI constraints

## Development Roadmap

### Phase 1: Domain Extraction (COMPLETE ✓)
- ✓ Extract pure functions from monolithic UI
- ✓ Create comprehensive test suite (29 tests, 87% coverage)
- ✓ Document API and algorithms

### Phase 2: Service Layer (COMPLETE ✓)
- ✓ Create application services (AnalysisService, VideoStreamService, ConfigService)
- ✓ Add configuration management with INI files
- ✓ Add comprehensive logging and error recovery

### Phase 3: UI Refactoring (COMPLETE ✓)
- ✓ Refactor Tkinter UI to use Clean Architecture
- ✓ Separate UI components (MainWindow, ConfigEditor)
- ✓ Create ApplicationController to coordinate layers
- ✓ Add result visualization with analysis overlays

### Phase 4: Future Enhancements
- [ ] Add service layer unit tests
- [ ] CLI tool for batch processing
- [ ] REST API service
- [ ] Batch processor for high-volume analysis
- [ ] Export results to PDF/CSV formats
- [ ] Historical trend analysis

## Documentation

- **docs/DOMAIN_LAYER.md:** Complete API reference with examples and algorithm details
- **Source Code:** Comprehensive docstrings in all modules with type hints
- **Configuration:** Example `config.ini` with inline comments

## Usage Workflow

1. **Connect to Camera**: Click "Connect Camera" to establish video stream connection
2. **Capture Laser Image**: Capture and detect laser isocenter position
3. **Capture DR Image**: Capture and detect DR center marker position
4. **Capture Starlines**: Use "Capture Starline" for each gantry angle, capturing the brightest frame
5. **Merge Images**: Select and merge all captured starline images
6. **Analyze**: Run complete Starshot analysis with automatic result visualization

## Contributing

When extending this project:

1. **Follow TDD**: Write tests first, then implementation
2. **Maintain Clean Architecture**: Keep domain layer pure (no I/O, no side effects)
3. **Add Type Hints**: Use comprehensive type hints for all functions
4. **Document Code**: Add detailed docstrings with examples
5. **Run Tests**: Maintain >85% coverage with `pytest --cov=src/domain`
6. **Follow Style**: Use black for formatting, flake8 for linting
7. **Keep Layers Separate**: Domain → Service → UI/Controller

## License

See LICENSE file (if applicable)

## Summary

Digital Starshot Analyzer is a complete medical physics QA application built with Clean Architecture principles. The project successfully implements:

- **Clean Architecture**: Clear separation of Domain, Service, and UI layers
- **High Test Coverage**: 87% test coverage with 29 comprehensive unit tests
- **Pure Domain Logic**: Business logic independent of frameworks and external systems
- **Full Application**: Complete Tkinter GUI with video streaming, image capture, and analysis
- **Extensibility**: Ready for CLI, REST API, or batch processing extensions
- **Production Ready**: Robust error handling, logging, and configuration management

The architecture enables testing without hardware dependencies, supports multiple interface types, and maintains algorithm correctness and performance while being highly maintainable and extensible.
