import tkinter as tk
from tkinter import filedialog, messagebox
import logging
import cv2
import os
from PIL import Image
import numpy as np
from typing import Optional

from src.services.video_stream_service import VideoStreamService
from src.services.config_service import ConfigService, StarshotConfig
from src.services.analysis_service import AnalysisService
from src.ui.main_window import MainWindow
from src.ui.config_editor import ConfigEditor

class ApplicationController:
    """The main controller for the Starshot Analyzer application."""

    def __init__(self, root: MainWindow):
        self.root = root
        self.config_service = ConfigService(config_file="config.ini")
        self.analysis_service = AnalysisService()
        self.config: StarshotConfig = self.config_service.load_config()

        self.video_stream: Optional[VideoStreamService] = None
        self.laser_coords: Optional[tuple] = None
        self.dr_coords: Optional[tuple] = None
        self.merged_image: Optional[Image.Image] = None

    def run(self):
        """Run the application's main loop."""
        self.root.mainloop()

    def log(self, message: str):
        """Log a message to the UI and the log file."""
        self.root.log(message)
        logging.info(message)

    def on_closing(self):
        """Handle the window closing event."""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            if self.video_stream:
                self.video_stream.stop()
            self.root.destroy()

    def connect_camera(self):
        """Connect to the video stream."""
        if self.video_stream and self.video_stream.is_alive():
            self.log("Already connected.")
            return

        stream_url = f'http://{self.config.network.ip_address_app}:8000/stream.mjpg'
        self.video_stream = VideoStreamService(video_source=stream_url, callback=self.on_frame_received)
        self.video_stream.start()

        if self.video_stream.is_alive():
            self.log(f"Connected to {self.config.network.ip_address_app}")
        else:
            self.log(f"Failed to connect to {self.config.network.ip_address_app}")

    def on_frame_received(self, frame: np.ndarray):
        """Callback for the video stream service."""
        cfg = self.config.crop
        cropped_frame = frame[cfg.crop_y : cfg.crop_y + cfg.crop_h, cfg.crop_x : cfg.crop_x + cfg.crop_w]

        rgb_img = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        self.root.update_image_label(self.root.lbl_stream, self.root.frame_streaming, pil_img)

    def capture_image(self, image_type: str) -> Optional[str]:
        """Capture the current frame and save it to a file."""
        if not (self.video_stream and self.video_stream.is_camera_online()):
            self.log("Camera not connected.")
            return None

        frame = self.video_stream.get_current_frame()
        if frame is None:
            self.log("Failed to get frame.")
            return None

        filename = f"{image_type}_{self.root.cmb_angle.get()}.jpg"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=filename,
            filetypes=[("JPEG files", "*.jpg")],
        )
        if filepath:
            try:
                cv2.imwrite(filepath, frame)
                self.log(f"Saved {image_type} image to {filepath}")
                return filepath
            except Exception as e:
                self.log(f"Error saving image: {e}")
        return None

    def capture_laser(self):
        """Capture and process the laser image."""
        filepath = self.capture_image("Laser")
        if filepath:
            try:
                self.laser_coords = self.analysis_service.detect_laser_isocenter(filepath)
                self.log(f"Laser isocenter detected at: {self.laser_coords[0]:.2f}, {self.laser_coords[1]:.2f}")
            except Exception as e:
                self.log(f"Laser detection failed: {e}")

    def capture_dr(self):
        """Capture and process the DR image."""
        filepath = self.capture_image("DR")
        if filepath:
            try:
                self.dr_coords = self.analysis_service.detect_dr_center(filepath)
                self.log(f"DR center detected at: {self.dr_coords}")
            except Exception as e:
                self.log(f"DR detection failed: {e}")

    def toggle_starline_capture(self):
        """Toggle the starline capture mode."""
        if not (self.video_stream and self.video_stream.is_camera_online()):
            self.log("Camera not connected.")
            return

        if not self.video_stream.is_calculation_enabled():
            self.video_stream.enable_calculation()
            self.video_stream.reset_calculation()
            self.root.btn_capture.config(text="Stop Capture")
            self.log("Starline capture started...")
        else:
            self.video_stream.disable_calculation()
            self.root.btn_capture.config(text="Capture Starline")
            brightest_frame = self.video_stream.get_brightest_frame()

            if brightest_frame is not None:
                filename = f"Starline_{self.root.cmb_angle.get()}.jpg"
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".jpg",
                    initialfile=filename,
                    filetypes=[("JPEG files", "*.jpg")],
                )
                if filepath:
                    try:
                        cv2.imwrite(filepath, brightest_frame)
                        self.log(f"Saved starline image to {filepath}")
                    except Exception as e:
                        self.log(f"Error saving starline image: {e}")
            else:
                self.log("No brightest frame captured.")

    def merge_images(self):
        """Merge selected starline images."""
        filepaths = filedialog.askopenfilenames(
            title="Select Starline Images",
            filetypes=[("JPEG files", "*.jpg"), ("All files", "*.*")],
        )
        if not filepaths:
            return

        try:
            self.merged_image = self.analysis_service.merge_images(list(filepaths))
            self.root.update_image_label(self.root.lbl_starshot, self.root.frame_starshot, self.merged_image)
            self.log(f"Merged {len(filepaths)} images.")
        except Exception as e:
            self.log(f"Failed to merge images: {e}")

    def analyze(self):
        """Run the final Starshot analysis."""
        if self.merged_image is None:
            self.log("No merged image available for analysis.")
            return
        if self.laser_coords is None:
            self.log("Laser isocenter has not been determined.")
            return
        if self.dr_coords is None:
            self.log("DR center has not been determined.")
            return

        try:
            results = self.analysis_service.analyze_starshot(
                self.merged_image, self.laser_coords, self.dr_coords
            )

            self.root.tbl_result.delete(*self.root.tbl_result.get_children())
            self.root.tbl_result.insert('', 'end', values=(
                f"{results['circle_diameter_mm']:.2f}",
                f"({results['laser_offset_mm'][0]:.2f}, {results['laser_offset_mm'][1]:.2f})",
                f"({results['dr_offset_mm'][0]:.2f}, {results['dr_offset_mm'][1]:.2f})"
            ))

            self.log(f"Analysis complete. Passed: {results['passed']}")
            self.log(f"Min radius: {results['circle_diameter_mm']:.2f} mm")
            self.log(f"Rad center: ({results['radiation_center'][0]:.2f}, {results['radiation_center'][1]:.2f})")

            analyzed_img = Image.open(results['analyzed_image_path'])
            self.root.update_image_label(self.root.lbl_analyzed, self.root.frame_analyzed, analyzed_img)
            os.remove(results['analyzed_image_path'])

        except Exception as e:
            self.log(f"Analysis failed: {e}")
            logging.error(f"Analysis failed: {e}", exc_info=True)

    def edit_config(self):
        """Open the configuration editor window."""
        ConfigEditor(self.root, self, self.config_service, self.log)

    def on_config_saved(self):
        """Callback for when the configuration is saved."""
        self.config = self.config_service.load_config()
        self.log("Configuration reloaded.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("starshot_analyzer.log"),
            logging.StreamHandler()
        ]
    )

    # Create the main window and controller, then link them
    root = MainWindow()
    app = ApplicationController(root)
    root.set_controller(app)
    app.run()