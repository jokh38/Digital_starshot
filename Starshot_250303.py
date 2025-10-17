import tkinter as tk
from tkinter import ttk, Label, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import logging
import numpy as np
import os
from typing import Optional

from src.services.video_stream_service import VideoStreamService
from src.services.config_service import ConfigService, StarshotConfig
from src.services.analysis_service import AnalysisService

# --- Configuration ---
logging.basicConfig(
    filename='star_shot_analyzer.log',
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%I:%M:%S'
)

class StarshotAnalyzer(tk.Tk):
    """Starshot analysis main application class."""

    def __init__(self, config_service: ConfigService, analysis_service: AnalysisService):
        super().__init__()
        self.title("Starshot Analyzer")
        self.geometry("1000x700")
        self.minsize(1000, 700)

        # Services
        self.config_service = config_service
        self.analysis_service = analysis_service
        self.config: StarshotConfig = self.config_service.load_config()

        # State variables
        self.video_stream: Optional[VideoStreamService] = None
        self.laser_coords: Optional[tuple] = None
        self.dr_coords: Optional[tuple] = None
        self.merged_image: Optional[Image.Image] = None

        self.init_ui()
        self.create_empty_image()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_empty_image(self):
        """Create an empty image placeholder."""
        data = np.zeros([self.config.crop.crop_h, self.config.crop.crop_w, 3], dtype=np.uint8)
        self.merged_image = Image.fromarray(data, 'RGB')

    def init_ui(self):
        """Initialize UI components."""
        # Menu bar
        self.menu_bar = tk.Menu(self)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Connect", command=self.connect_camera)
        file_menu.add_command(label="Edit Config", command=self.edit_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=self.menu_bar)

        # --- Layout ---
        self.grid_rowconfigure(1, weight=5)
        self.grid_columnconfigure(0, weight=1)

        # Control and Analyze frames
        control_analyze_frame = ttk.Frame(self)
        control_analyze_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.frame_control = ttk.LabelFrame(control_analyze_frame, text="Control")
        self.frame_control.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X)

        self.analyze_control = ttk.LabelFrame(control_analyze_frame, text="Analyze")
        self.analyze_control.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X)

        # Image frames
        self.frame_images = ttk.Frame(self)
        self.frame_images.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.frame_images.grid_columnconfigure((0, 1, 2), weight=1)
        self.frame_images.grid_rowconfigure(0, weight=1)

        self.frame_streaming = ttk.LabelFrame(self.frame_images, text="Streaming")
        self.frame_streaming.grid(row=0, column=0, sticky="nsew", padx=5)
        self.frame_starshot = ttk.LabelFrame(self.frame_images, text="Starshot")
        self.frame_starshot.grid(row=0, column=1, sticky="nsew", padx=5)
        self.frame_analyzed = ttk.LabelFrame(self.frame_images, text="Analyzed")
        self.frame_analyzed.grid(row=0, column=2, sticky="nsew", padx=5)

        # Result frame
        self.frame_result = ttk.LabelFrame(self, text="Result")
        self.frame_result.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # --- Widgets ---
        # Control
        self.btn_laser = ttk.Button(self.frame_control, text="Capture Laser", command=self.capture_laser)
        self.btn_laser.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_dr = ttk.Button(self.frame_control, text="Capture DR", command=self.capture_dr)
        self.btn_dr.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_capture = ttk.Button(self.frame_control, text="Capture Starline", command=self.toggle_starline_capture)
        self.btn_capture.pack(side=tk.LEFT, padx=5, pady=5)
        self.cmb_angle = ttk.Combobox(self.frame_control, values=["G000", "G030", "G090", "G150", "G240", "G300"], width=8)
        self.cmb_angle.current(0)
        self.cmb_angle.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Analyze
        self.btn_merge = ttk.Button(self.analyze_control, text="1. Merge Images", command=self.merge_images)
        self.btn_merge.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_analyze = ttk.Button(self.analyze_control, text="2. Analyze", command=self.analyze)
        self.btn_analyze.pack(side=tk.LEFT, padx=5, pady=5)

        # Image labels
        self.lbl_stream = Label(self.frame_streaming)
        self.lbl_stream.pack(fill=tk.BOTH, expand=True)
        self.lbl_starshot = Label(self.frame_starshot)
        self.lbl_starshot.pack(fill=tk.BOTH, expand=True)
        self.lbl_analyzed = Label(self.frame_analyzed)
        self.lbl_analyzed.pack(fill=tk.BOTH, expand=True)

        # Result display
        paned_window = tk.PanedWindow(self.frame_result, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        result_frame_left = ttk.Frame(paned_window)
        result_frame_right = ttk.Frame(paned_window)
        paned_window.add(result_frame_left, weight=3)
        paned_window.add(result_frame_right, weight=2)

        self.txt_log = ScrolledText(result_frame_right, height=6)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        columns = ('min_radius', 'vs_laser', 'vs_dr')
        self.tbl_result = ttk.Treeview(result_frame_left, columns=columns, show='headings', height=1)
        self.tbl_result.heading('min_radius', text='Min. Radius')
        self.tbl_result.heading('vs_laser', text='vs Laser (mm)')
        self.tbl_result.heading('vs_dr', text='vs DR (mm)')
        self.tbl_result.column('min_radius', width=150, anchor='center')
        self.tbl_result.column('vs_laser', width=200, anchor='center')
        self.tbl_result.column('vs_dr', width=200, anchor='center')
        self.tbl_result.pack(fill=tk.BOTH, expand=True)

    def update_image_label(self, label: Label, frame: ttk.LabelFrame, pil_img: Image.Image):
        """Updates a label with a resized image."""
        if pil_img is None:
            return
        
        width = frame.winfo_width()
        height = frame.winfo_height()
        if width <= 1 or height <= 1:
            width, height = 300, 300 # Default size

        resized_img = pil_img.copy()
        resized_img.thumbnail((width, height), Image.LANCZOS)
        
        img_tk = ImageTk.PhotoImage(image=resized_img)
        label.img_tk = img_tk
        label.config(image=img_tk)

    def on_frame_received(self, frame: np.ndarray):
        """Callback for the video stream service."""
        cfg = self.config.crop
        cropped_frame = frame[cfg.crop_y : cfg.crop_y + cfg.crop_h, cfg.crop_x : cfg.crop_x + cfg.crop_w]
        
        rgb_img = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        self.update_image_label(self.lbl_stream, self.frame_streaming, pil_img)

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

    def capture_image(self, image_type: str) -> Optional[str]:
        """Capture the current frame and save it to a file."""
        if not (self.video_stream and self.video_stream.is_camera_online()):
            self.log("Camera not connected.")
            return None

        frame = self.video_stream.get_current_frame()
        if frame is None:
            self.log("Failed to get frame.")
            return None

        filename = f"{image_type}_{self.cmb_angle.get()}.jpg"
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
            self.btn_capture.config(text="Stop Capture")
            self.log("Starline capture started...")
        else:
            self.video_stream.disable_calculation()
            self.btn_capture.config(text="Capture Starline")
            brightest_frame = self.video_stream.get_brightest_frame()

            if brightest_frame is not None:
                filename = f"Starline_{self.cmb_angle.get()}.jpg"
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
            self.update_image_label(self.lbl_starshot, self.frame_starshot, self.merged_image)
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
            
            # Display results
            self.tbl_result.delete(*self.tbl_result.get_children())
            self.tbl_result.insert('', 'end', values=(
                f"{results['circle_diameter_mm']:.2f}",
                f"({results['laser_offset_mm'][0]:.2f}, {results['laser_offset_mm'][1]:.2f})",
                f"({results['dr_offset_mm'][0]:.2f}, {results['dr_offset_mm'][1]:.2f})"
            ))

            self.log(f"Analysis complete. Passed: {results['passed']}")
            self.log(f"Min radius: {results['circle_diameter_mm']:.2f} mm")
            self.log(f"Rad center: ({results['radiation_center'][0]:.2f}, {results['radiation_center'][1]:.2f})")

            # Display analyzed image
            analyzed_img = Image.open(results['analyzed_image_path'])
            self.update_image_label(self.lbl_analyzed, self.frame_analyzed, analyzed_img)
            os.remove(results['analyzed_image_path']) # Clean up temp file

        except Exception as e:
            self.log(f"Analysis failed: {e}")
            logging.error(f"Analysis failed: {e}", exc_info=True)

    def log(self, message: str):
        """Log a message to the UI and the log file."""
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        logging.info(message)

    def edit_config(self):
        """Open the configuration editor window."""
        ConfigEditor(self, self.config_service, self.log)

    def show_about(self):
        """Show the about dialog."""
        about_text = "Starshot Analyzer v3.0\n\nA medical physics QA tool."
        messagebox.showinfo("About", about_text)

    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            if self.video_stream:
                self.video_stream.stop()
            self.destroy()

class ConfigEditor(tk.Toplevel):
    """Configuration editor window."""

    def __init__(self, parent: tk.Tk, config_service: ConfigService, logger: callable):
        super().__init__(parent)
        self.title("Edit Configuration")
        self.geometry("400x300")
        self.grab_set()

        self.config_service = config_service
        self.config = config_service.load_config()
        self.logger = logger

        # --- Widgets ---
        self.vars = {
            'ip_address_app': tk.StringVar(value=self.config.network.ip_address_app),
            'crop_x': tk.IntVar(value=self.config.crop.crop_x),
            'crop_y': tk.IntVar(value=self.config.crop.crop_y),
            'crop_w': tk.IntVar(value=self.config.crop.crop_w),
            'crop_h': tk.IntVar(value=self.config.crop.crop_h),
        }

        # Network
        net_frame = ttk.LabelFrame(self, text="Network")
        net_frame.pack(padx=10, pady=10, fill=tk.X)
        ttk.Label(net_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(net_frame, textvariable=self.vars['ip_address_app']).grid(row=0, column=1, padx=5, pady=5)

        # Crop
        crop_frame = ttk.LabelFrame(self, text="Crop")
        crop_frame.pack(padx=10, pady=10, fill=tk.X)
        ttk.Label(crop_frame, text="X:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(crop_frame, textvariable=self.vars['crop_x'], width=5).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(crop_frame, text="Y:").grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(crop_frame, textvariable=self.vars['crop_y'], width=5).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(crop_frame, text="W:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(crop_frame, textvariable=self.vars['crop_w'], width=5).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(crop_frame, text="H:").grid(row=1, column=2, padx=5, pady=5)
        ttk.Entry(crop_frame, textvariable=self.vars['crop_h'], width=5).grid(row=1, column=3, padx=5, pady=5)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=10, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        """Save the configuration."""
        try:
            self.config.network.ip_address_app = self.vars['ip_address_app'].get()
            self.config.crop.crop_x = self.vars['crop_x'].get()
            self.config.crop.crop_y = self.vars['crop_y'].get()
            self.config.crop.crop_w = self.vars['crop_w'].get()
            self.config.crop.crop_h = self.vars['crop_h'].get()

            self.config.validate()
            self.config_service.save_config(self.config)
            self.logger("Configuration saved.")

            # This is a bit of a hack, the main app should ideally listen for config changes
            self.master.config = self.config_service.load_config()
            self.master.log("Configuration reloaded.")
            
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

if __name__ == "__main__":
    import cv2 # Keep cv2 here as it's a heavy import for the main app loop
    
    # Initialize services
    config_service = ConfigService(config_file="config.ini")
    analysis_service = AnalysisService()

    # Create and run the application
    app = StarshotAnalyzer(config_service=config_service, analysis_service=analysis_service)
    app.mainloop()