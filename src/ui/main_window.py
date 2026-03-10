import tkinter as tk
from tkinter import ttk, Label, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import numpy as np

class MainWindow(tk.Tk):
    """The main window of the Starshot Analyzer application."""

    def __init__(self):
        super().__init__()
        self.controller = None
        self.title("Starshot Analyzer")
        self.geometry("1000x700")
        self.minsize(1000, 700)

    def set_controller(self, controller):
        """Set the controller and initialize UI components that need it."""
        self.controller = controller
        self.apply_styles()
        self.init_ui()
        self.create_empty_image()
        self.protocol("WM_DELETE_WINDOW", self.controller.on_closing)
        self.update_ui_state()

    def apply_styles(self):
        """Apply a cleaner, modern look using only standard ttk."""
        self.style = ttk.Style(self)
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
        
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TLabelframe', background='#f5f5f5', font=('Segoe UI', 10, 'bold'))
        self.style.configure('TLabelframe.Label', background='#f5f5f5', font=('Segoe UI', 10, 'bold'))
        self.style.configure('TButton', font=('Segoe UI', 10), padding=4)
        self.style.configure('Header.TLabel', font=('Segoe UI', 22, 'bold'), foreground='#333333', background='#f5f5f5')
        self.style.configure('Value.TLabel', font=('Segoe UI', 16), foreground='#0052cc', background='#f5f5f5')
        self.style.configure('SubHeader.TLabel', font=('Segoe UI', 10), foreground='#666666', background='#f5f5f5')
        self.configure(bg='#f5f5f5')

    def update_ui_state(self):
        """Poll the controller state and enable/disable UI elements accordingly."""
        if self.controller:
            camera_online = self.controller.video_stream is not None and self.controller.video_stream.is_alive()
            
            cam_state = tk.NORMAL if camera_online else tk.DISABLED
            self.btn_laser.config(state=cam_state)
            self.btn_dr.config(state=cam_state)
            self.btn_capture.config(state=cam_state)
            self.cmb_angle.config(state="readonly" if camera_online else tk.DISABLED)
            
            self.btn_connect.config(text="Camera Connected" if camera_online else "Connect Camera")
            self.btn_connect.config(state=tk.DISABLED if camera_online else tk.NORMAL)

            can_analyze = (self.controller.merged_image is not None and 
                           self.controller.laser_coords is not None and 
                           self.controller.dr_coords is not None)
            self.btn_analyze.config(state=tk.NORMAL if can_analyze else tk.DISABLED)

        self.after(500, self.update_ui_state)

    def create_empty_image(self):
        """Create an empty image placeholder for the merged image view."""
        # This will be replaced by the actual merged image later.
        empty_image_data = np.zeros((480, 640, 3), dtype=np.uint8)
        self.merged_image = Image.fromarray(empty_image_data, 'RGB')

    def init_ui(self):
        """Initialize all UI components."""
        # --- Menu Bar ---
        self.menu_bar = tk.Menu(self)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Connect", command=self.controller.connect_camera)
        file_menu.add_command(label="Edit Config", command=self.controller.edit_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.controller.on_closing)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=self.menu_bar)

        # --- Layout ---
        self.grid_rowconfigure(1, weight=5)
        self.grid_columnconfigure(0, weight=1)

        # Control and Analyze frames (Workflow)
        control_analyze_frame = ttk.Frame(self)
        control_analyze_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.frame_connection = ttk.LabelFrame(control_analyze_frame, text="1. Setup")
        self.frame_connection.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

        self.frame_calibration = ttk.LabelFrame(control_analyze_frame, text="2. Calibration")
        self.frame_calibration.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

        self.frame_acquisition = ttk.LabelFrame(control_analyze_frame, text="3. Acquisition")
        self.frame_acquisition.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

        self.analyze_control = ttk.LabelFrame(control_analyze_frame, text="4. Analysis")
        self.analyze_control.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

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
        # 1. Setup
        self.btn_connect = ttk.Button(self.frame_connection, text="Connect Camera", command=self.controller.connect_camera)
        self.btn_connect.pack(side=tk.TOP, padx=5, pady=2)
        
        self.btn_close = ttk.Button(self.frame_connection, text="Close App", command=self.controller.on_closing)
        self.btn_close.pack(side=tk.TOP, padx=5, pady=2)

        # 2. Calibration
        self.btn_laser = ttk.Button(self.frame_calibration, text="Capture Laser", command=self.controller.capture_laser)
        self.btn_laser.pack(side=tk.TOP, padx=5, pady=2)
        self.btn_dr = ttk.Button(self.frame_calibration, text="Capture DR", command=self.controller.capture_dr)
        self.btn_dr.pack(side=tk.TOP, padx=5, pady=2)

        # 3. Acquisition
        self.btn_capture = ttk.Button(self.frame_acquisition, text="Capture Starline", command=self.controller.toggle_starline_capture)
        self.btn_capture.pack(side=tk.TOP, padx=5, pady=2)
        self.cmb_angle = ttk.Combobox(self.frame_acquisition, values=["G000", "G030", "G090", "G150", "G240", "G300"], width=6, state="readonly")
        self.cmb_angle.current(0)
        self.cmb_angle.pack(side=tk.TOP, padx=5, pady=2)

        # 4. Analyze
        analyze_load_frame = ttk.Frame(self.analyze_control)
        analyze_load_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        self.btn_load_laser = ttk.Button(analyze_load_frame, text="Load Laser", command=self.controller.load_laser_file)
        self.btn_load_laser.pack(side=tk.TOP, pady=2)
        self.btn_load_dr = ttk.Button(analyze_load_frame, text="Load DR", command=self.controller.load_dr_file)
        self.btn_load_dr.pack(side=tk.TOP, pady=2)

        ttk.Separator(self.analyze_control, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        analyze_run_frame = ttk.Frame(self.analyze_control)
        analyze_run_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        self.btn_merge = ttk.Button(analyze_run_frame, text="Merge Images", command=self.controller.merge_images)
        self.btn_merge.pack(side=tk.TOP, pady=2)
        self.btn_analyze = ttk.Button(analyze_run_frame, text="Analyze Results", command=self.controller.analyze)
        self.btn_analyze.pack(side=tk.TOP, pady=2)

        # Image labels
        self.lbl_stream = Label(self.frame_streaming)
        self.lbl_stream.pack(fill=tk.BOTH, expand=True)
        self.lbl_starshot = Label(self.frame_starshot)
        self.lbl_starshot.pack(fill=tk.BOTH, expand=True)
        self.lbl_analyzed = Label(self.frame_analyzed)
        self.lbl_analyzed.pack(fill=tk.BOTH, expand=True)

        # Result display
        paned_window = ttk.PanedWindow(self.frame_result, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        result_frame_left = ttk.Frame(paned_window, style='TFrame')
        result_frame_right = ttk.Frame(paned_window, style='TFrame')
        paned_window.add(result_frame_left, weight=3)
        paned_window.add(result_frame_right, weight=2)

        self.txt_log = ScrolledText(result_frame_right, height=6, font=('Consolas', 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Replacing Treeview with styled labels for clearer UX
        self.lbl_rad_val = ttk.Label(result_frame_left, text="--", style='Header.TLabel')
        self.lbl_rad_val.grid(row=0, column=0, padx=20, pady=(15, 0), sticky='w')
        ttk.Label(result_frame_left, text="Min. Radius", style='SubHeader.TLabel').grid(row=1, column=0, padx=20, pady=(0, 10), sticky='w')

        self.lbl_laser_val = ttk.Label(result_frame_left, text="--", style='Value.TLabel')
        self.lbl_laser_val.grid(row=0, column=1, padx=20, pady=(22, 0), sticky='w')
        ttk.Label(result_frame_left, text="vs Laser Offset", style='SubHeader.TLabel').grid(row=1, column=1, padx=20, pady=(0, 10), sticky='w')

        self.lbl_dr_val = ttk.Label(result_frame_left, text="--", style='Value.TLabel')
        self.lbl_dr_val.grid(row=0, column=2, padx=20, pady=(22, 0), sticky='w')
        ttk.Label(result_frame_left, text="vs DR Offset", style='SubHeader.TLabel').grid(row=1, column=2, padx=20, pady=(0, 10), sticky='w')

        result_frame_left.grid_columnconfigure((0, 1, 2), weight=1)

    def update_results(self, min_radius, vs_laser, vs_dr):
        """Update the result labels with analysis data."""
        self.lbl_rad_val.config(text=min_radius)
        self.lbl_laser_val.config(text=vs_laser)
        self.lbl_dr_val.config(text=vs_dr)

    def update_image_label(self, label: Label, frame: ttk.LabelFrame, pil_img: Image.Image):
        """Updates a label with a resized image."""
        if pil_img is None:
            return

        # Use a default size if the frame hasn't been rendered yet
        width = frame.winfo_width()
        height = frame.winfo_height()
        if width <= 1 or height <= 1:
            width, height = 300, 300

        resized_img = pil_img.copy()
        resized_img.thumbnail((width, height), Image.LANCZOS)

        img_tk = ImageTk.PhotoImage(image=resized_img)
        label.img_tk = img_tk  # Keep a reference to avoid garbage collection
        label.config(image=img_tk)

    def log(self, message: str):
        """Log a message to the UI's log widget."""
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def show_about(self):
        """Show the about dialog."""
        about_text = "Starshot Analyzer v3.0\n\nRefactored for your pleasure."
        messagebox.showinfo("About", about_text)