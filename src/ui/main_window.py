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
        self.init_ui()
        self.create_empty_image()
        self.protocol("WM_DELETE_WINDOW", self.controller.on_closing)

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
        self.btn_laser = ttk.Button(self.frame_control, text="Capture Laser", command=self.controller.capture_laser)
        self.btn_laser.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_dr = ttk.Button(self.frame_control, text="Capture DR", command=self.controller.capture_dr)
        self.btn_dr.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_capture = ttk.Button(self.frame_control, text="Capture Starline", command=self.controller.toggle_starline_capture)
        self.btn_capture.pack(side=tk.LEFT, padx=5, pady=5)
        self.cmb_angle = ttk.Combobox(self.frame_control, values=["G000", "G030", "G090", "G150", "G240", "G300"], width=8)
        self.cmb_angle.current(0)
        self.cmb_angle.pack(side=tk.LEFT, padx=5, pady=5)

        # Analyze
        self.btn_merge = ttk.Button(self.analyze_control, text="1. Merge Images", command=self.controller.merge_images)
        self.btn_merge.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_analyze = ttk.Button(self.analyze_control, text="2. Analyze", command=self.controller.analyze)
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