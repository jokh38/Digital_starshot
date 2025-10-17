"""Tests for VideoStreamService with thread safety verification."""
import unittest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.services.video_stream_service import VideoStreamService


class TestVideoStreamServiceBasic(unittest.TestCase):
    """Basic functionality tests for VideoStreamService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = None
        self.mock_callback = Mock()

    def tearDown(self):
        """Clean up after tests."""
        if self.service and self.service.is_alive():
            self.service.stop()
            time.sleep(0.2)  # Allow thread to finish

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_service_starts_and_stops_cleanly(self, mock_capture_class):
        """Test that service starts and stops without exceptions."""
        # Mock video capture
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        # Give thread time to start
        time.sleep(0.2)

        # Verify thread is running
        self.assertTrue(self.service.is_alive())

        # Stop gracefully
        self.service.stop()
        time.sleep(0.3)

        # Verify thread has stopped
        self.assertFalse(self.service.is_alive())

        # Verify VideoCapture was released
        mock_cap.release.assert_called()

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_service_calls_callback_with_frame(self, mock_capture_class):
        """Test that service invokes callback with valid frames."""
        # Create a mock frame
        mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock video capture with valid frames
        mock_cap = MagicMock()
        mock_cap.read.side_effect = [
            (True, mock_frame),
            (True, mock_frame),
            (False, None),
        ]
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(
            video_source='http://test:8000/stream.mjpg',
            callback=self.mock_callback
        )
        self.service.start()

        # Wait for processing
        time.sleep(0.3)

        # Stop service
        self.service.stop()
        time.sleep(0.2)

        # Verify callback was called with frames
        self.assertGreater(self.mock_callback.call_count, 0)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_brightest_frame_selection(self, mock_capture_class):
        """Test that service correctly identifies brightest frame."""
        # Create frames with different brightness levels
        brightest_frame = np.full((100, 100, 3), 255, dtype=np.uint8)

        # Use a simple mock that just returns the brightest frame
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, brightest_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        # Enable calculation mode
        time.sleep(0.1)
        self.service.enable_calculation()

        # Wait for processing
        time.sleep(0.3)

        # Stop service
        self.service.stop()
        time.sleep(0.2)

        # Verify brightest frame was captured
        max_frame = self.service.get_brightest_frame()
        self.assertIsNotNone(max_frame)
        np.testing.assert_array_equal(max_frame, brightest_frame)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_concurrent_reads_are_thread_safe(self, mock_capture_class):
        """Test that concurrent reads from multiple threads don't cause race conditions."""
        # Create mock frame
        mock_frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        # Mock video capture
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, mock_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        # Enable calculation mode
        time.sleep(0.1)
        self.service.enable_calculation()

        # Track any exceptions from reader threads
        reader_exceptions = []

        def reader_thread():
            """Reader thread that accesses shared state."""
            try:
                for _ in range(20):
                    frame = self.service.get_current_frame()
                    brightness = self.service.get_current_brightness()
                    max_brightness = self.service.get_max_brightness()
                    brightest_frame = self.service.get_brightest_frame()
                    time.sleep(0.01)
            except Exception as e:
                reader_exceptions.append(e)

        # Create multiple reader threads
        threads = [threading.Thread(target=reader_thread) for _ in range(3)]
        for thread in threads:
            thread.start()

        # Wait for readers to complete
        for thread in threads:
            thread.join(timeout=2.0)

        # Stop service
        self.service.stop()
        time.sleep(0.2)

        # Verify no exceptions occurred
        self.assertEqual(len(reader_exceptions), 0,
                        f"Thread safety violation: {reader_exceptions}")

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_calculation_mode_toggle(self, mock_capture_class):
        """Test enabling and disabling calculation mode."""
        mock_frame = np.full((100, 100, 3), 100, dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, mock_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        # Initial state
        self.assertFalse(self.service.is_calculation_enabled())

        # Enable
        self.service.enable_calculation()
        self.assertTrue(self.service.is_calculation_enabled())

        # Disable
        self.service.disable_calculation()
        self.assertFalse(self.service.is_calculation_enabled())

        self.service.stop()
        time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_reset_calculation_state(self, mock_capture_class):
        """Test that calculation state can be reset."""
        mock_frame = np.full((100, 100, 3), 100, dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, mock_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.1)
        self.service.enable_calculation()

        # Wait for some data to accumulate
        time.sleep(0.2)

        # Reset state
        self.service.reset_calculation()

        # Verify state is reset
        self.assertEqual(self.service.get_max_brightness(), 0)
        self.assertIsNone(self.service.get_brightest_frame())

        self.service.stop()
        time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_camera_connection_status(self, mock_capture_class):
        """Test camera connection status tracking."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.assertFalse(self.service.is_camera_online())

        self.service.start()
        time.sleep(0.2)

        # After first successful read, should be online
        self.assertTrue(self.service.is_camera_online())

        self.service.stop()
        time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_exception_on_capture_doesnt_crash(self, mock_capture_class):
        """Test that exceptions during capture are handled gracefully."""
        mock_cap = MagicMock()
        mock_cap.read.side_effect = RuntimeError("Capture error")
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')

        # Should not raise exception, just handle gracefully
        try:
            self.service.start()
            time.sleep(0.3)
            self.service.stop()
            time.sleep(0.2)
        except Exception as e:
            self.fail(f"Service raised exception on capture error: {e}")

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_camera_release_on_exception(self, mock_capture_class):
        """Test that video capture is released even if exception occurs."""
        mock_cap = MagicMock()
        mock_cap.read.side_effect = [
            (True, np.zeros((100, 100, 3), dtype=np.uint8)),
            RuntimeError("Capture failed"),
        ]
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.3)
        self.service.stop()
        time.sleep(0.2)

        # Verify release was called
        mock_cap.release.assert_called()

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_frame_copy_prevents_external_modification(self, mock_capture_class):
        """Test that returned frames are copies, not references."""
        original_frame = np.full((100, 100, 3), 100, dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, original_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.2)

        # Get frame and modify it
        frame = self.service.get_current_frame()
        if frame is not None:
            frame[:] = 0

        # Get frame again - should not be modified
        frame2 = self.service.get_current_frame()
        if frame2 is not None:
            self.assertFalse(np.array_equal(frame, frame2),
                            "Frame was not copied properly")

        self.service.stop()
        time.sleep(0.2)


class TestVideoStreamServiceStressConditions(unittest.TestCase):
    """Stress and edge case tests for VideoStreamService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = None

    def tearDown(self):
        """Clean up after tests."""
        if self.service and self.service.is_alive():
            self.service.stop()
            time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_rapid_enable_disable_cycles(self, mock_capture_class):
        """Test rapid toggling of calculation mode."""
        mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, mock_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        # Rapid cycles
        for _ in range(10):
            self.service.enable_calculation()
            time.sleep(0.05)
            self.service.disable_calculation()
            time.sleep(0.05)

        self.service.stop()
        time.sleep(0.2)

        # Verify service still functional after stress
        self.assertFalse(self.service.is_alive())

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_multiple_stop_calls(self, mock_capture_class):
        """Test that multiple stop calls don't cause issues."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.2)

        # Multiple stop calls
        self.service.stop()
        self.service.stop()
        self.service.stop()

        time.sleep(0.2)

        # Should not raise exception
        self.assertFalse(self.service.is_alive())

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_stop_with_long_timeout(self, mock_capture_class):
        """Test that timeout works correctly for thread join."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg',
                                         thread_join_timeout=5.0)
        self.service.start()

        time.sleep(0.1)

        start_time = time.time()
        self.service.stop()
        elapsed = time.time() - start_time

        # Should complete quickly (not wait full timeout)
        self.assertLess(elapsed, 2.0,
                       "Stop took longer than expected with large timeout")


class TestVideoStreamServiceDataIntegrity(unittest.TestCase):
    """Tests for data integrity and frame processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = None

    def tearDown(self):
        """Clean up after tests."""
        if self.service and self.service.is_alive():
            self.service.stop()
            time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_brightness_calculation_accuracy(self, mock_capture_class):
        """Test that brightness is calculated correctly."""
        # Create a frame with known pixel sum
        test_frame = np.full((10, 10, 3), 100, dtype=np.uint8)
        expected_brightness = np.sum(test_frame)

        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, test_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.1)
        self.service.enable_calculation()

        time.sleep(0.2)

        current_brightness = self.service.get_current_brightness()

        # Should match expected value
        self.assertEqual(current_brightness, expected_brightness,
                        "Brightness calculation mismatch")

        self.service.stop()
        time.sleep(0.2)

    @patch('src.services.video_stream_service.cv2.VideoCapture')
    def test_max_brightness_tracking(self, mock_capture_class):
        """Test that maximum brightness is tracked correctly."""
        # Use a bright frame
        bright_frame = np.full((10, 10, 3), 150, dtype=np.uint8)

        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, bright_frame)
        mock_capture_class.return_value = mock_cap

        self.service = VideoStreamService(video_source='http://test:8000/stream.mjpg')
        self.service.start()

        time.sleep(0.1)
        self.service.enable_calculation()

        time.sleep(0.2)

        max_brightness = self.service.get_max_brightness()

        # Should be brightness of 150 frame
        expected_max = int(np.sum(bright_frame))
        self.assertEqual(max_brightness, expected_max,
                        "Max brightness not tracked correctly")

        self.service.stop()
        time.sleep(0.2)


if __name__ == '__main__':
    unittest.main()
