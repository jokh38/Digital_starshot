"""Thread-safe video streaming service for real-time frame capture and analysis.

This service provides thread-safe video capture from a streaming source with
support for real-time brightness analysis and brightest frame detection.
All shared state is protected by locks to prevent race conditions.
"""
import threading
import time
import logging
import cv2
import numpy as np
from typing import Optional, Callable


class VideoStreamService(threading.Thread):
    """Thread-safe video streaming service.

    This service manages video capture in a separate thread while providing
    thread-safe access to current and maximum brightness frames. All shared
    state is protected by locks to ensure no race conditions occur.

    Attributes:
        video_source: URL or path to video source (e.g., HTTP stream)
        thread_join_timeout: Maximum seconds to wait for thread to finish
        callback: Optional callback function called on each frame
    """

    def __init__(self, video_source: str, thread_join_timeout: float = 5.0,
                 callback: Optional[Callable] = None):
        """Initialize VideoStreamService.

        Args:
            video_source: URL or device path for video capture
            thread_join_timeout: Timeout in seconds for thread.join()
            callback: Optional callback function(frame) called for each frame
        """
        super().__init__(daemon=False)

        self.video_source = video_source
        self.thread_join_timeout = thread_join_timeout
        self.callback = callback

        # Thread control
        self._stop_event = threading.Event()

        # Thread safety: Locks for all shared state
        self._state_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._brightness_lock = threading.Lock()

        # Shared state - camera connection
        self._camera_is_online = False

        # Shared state - current frame and brightness
        self._current_frame = None
        self._current_brightness = 0

        # Shared state - calculation mode
        self._calculation_enabled = False

        # Shared state - maximum brightness and brightest frame
        self._max_brightness = 0
        self._brightest_frame = None

    def run(self) -> None:
        """Main thread execution loop.

        Continuously captures frames from the video source and processes them.
        All shared state updates are protected by appropriate locks.
        """
        cap = None
        try:
            # Open video capture
            cap = cv2.VideoCapture(self.video_source)
            if not cap.isOpened():
                logging.warning(f"Failed to open video source: {self.video_source}")
                return

            # Main capture loop
            while not self._stop_event.is_set():
                ret, frame = cap.read()

                if ret and frame is not None:
                    # Mark camera as online
                    with self._state_lock:
                        self._camera_is_online = True

                    # Update current frame (thread-safe)
                    with self._frame_lock:
                        self._current_frame = frame.copy()

                    # Invoke callback if provided
                    if self.callback:
                        try:
                            self.callback(frame)
                        except Exception as e:
                            logging.error(f"Callback error: {e}")

                    # Process brightness analysis if enabled
                    if self._is_calculation_enabled():
                        self._process_brightness_analysis(frame)
                else:
                    # Frame read failed
                    with self._state_lock:
                        self._camera_is_online = False

                    logging.warning("No frame received from video source")
                    time.sleep(0.5)  # Wait before retrying

        except Exception as e:
            logging.error(f"VideoStreamService error: {e}")

        finally:
            # Ensure video capture is released
            if cap is not None:
                try:
                    cap.release()
                    logging.info("Video capture released successfully")
                except Exception as e:
                    logging.error(f"Error releasing video capture: {e}")

    def _is_calculation_enabled(self) -> bool:
        """Check if calculation mode is enabled (thread-safe).

        Returns:
            True if brightness calculation is enabled, False otherwise
        """
        with self._state_lock:
            return self._calculation_enabled

    def _process_brightness_analysis(self, frame: np.ndarray) -> None:
        """Process brightness analysis on the given frame.

        Calculates current brightness and updates max brightness/brightest frame
        if current brightness exceeds maximum.

        Args:
            frame: OpenCV frame to analyze
        """
        try:
            # Calculate brightness (sum of all pixel values)
            current_brightness = int(np.sum(frame))

            # Update current brightness (thread-safe)
            with self._brightness_lock:
                self._current_brightness = current_brightness

                # Check if this is the brightest frame so far
                if current_brightness > self._max_brightness:
                    logging.info("Found brightest frame")
                    self._max_brightness = current_brightness
                    self._brightest_frame = frame.copy()

        except Exception as e:
            logging.error(f"Brightness analysis error: {e}")

    def enable_calculation(self) -> None:
        """Enable brightness calculation mode (thread-safe)."""
        with self._state_lock:
            self._calculation_enabled = True

    def disable_calculation(self) -> None:
        """Disable brightness calculation mode (thread-safe)."""
        with self._state_lock:
            self._calculation_enabled = False

    def is_calculation_enabled(self) -> bool:
        """Check if brightness calculation is enabled (thread-safe).

        Returns:
            True if calculation mode is active
        """
        with self._state_lock:
            return self._calculation_enabled

    def reset_calculation(self) -> None:
        """Reset brightness calculation state (thread-safe).

        Clears max brightness and brightest frame tracking.
        """
        with self._brightness_lock:
            self._max_brightness = 0
            self._brightest_frame = None

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get a copy of the current frame (thread-safe).

        Returns:
            Copy of the current frame, or None if no frame available
        """
        with self._frame_lock:
            if self._current_frame is None:
                return None
            return self._current_frame.copy()

    def get_current_brightness(self) -> int:
        """Get current frame brightness (thread-safe).

        Returns:
            Sum of all pixel values in current frame
        """
        with self._brightness_lock:
            return self._current_brightness

    def get_max_brightness(self) -> int:
        """Get maximum brightness seen so far (thread-safe).

        Returns:
            Maximum brightness value
        """
        with self._brightness_lock:
            return self._max_brightness

    def get_brightest_frame(self) -> Optional[np.ndarray]:
        """Get a copy of the brightest frame (thread-safe).

        Returns:
            Copy of the brightest frame seen, or None if none captured
        """
        with self._brightness_lock:
            if self._brightest_frame is None:
                return None
            return self._brightest_frame.copy()

    def is_camera_online(self) -> bool:
        """Check if camera is currently online (thread-safe).

        Returns:
            True if camera is successfully providing frames
        """
        with self._state_lock:
            return self._camera_is_online

    def stop(self) -> None:
        """Stop the video streaming service.

        Signals the thread to stop and waits for it to finish.
        Safe to call multiple times.
        """
        if not self._stop_event.is_set():
            self._stop_event.set()

        # Wait for thread to finish
        if self.is_alive():
            self.join(timeout=self.thread_join_timeout)
            if self.is_alive():
                logging.warning(f"Video thread did not stop within "
                              f"{self.thread_join_timeout}s timeout")
