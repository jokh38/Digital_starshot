import tkinter as tk
from tkinter import ttk, messagebox
from src.services.config_service import ConfigService, StarshotConfig

class ConfigEditor(tk.Toplevel):
    """Configuration editor window."""

    def __init__(self, parent, controller, config_service: ConfigService, logger: callable):
        super().__init__(parent)
        self.controller = controller
        self.config_service = config_service
        self.logger = logger
        self.config = config_service.load_config()

        self.title("Edit Configuration")
        self.geometry("400x300")
        self.grab_set()

        self.init_widgets()

    def init_widgets(self):
        """Initialize all widgets in the window."""
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
            new_config = StarshotConfig(
                network=self.config.network,
                crop=self.config.crop
            )
            new_config.network.ip_address_app = self.vars['ip_address_app'].get()
            new_config.crop.crop_x = self.vars['crop_x'].get()
            new_config.crop.crop_y = self.vars['crop_y'].get()
            new_config.crop.crop_w = self.vars['crop_w'].get()
            new_config.crop.crop_h = self.vars['crop_h'].get()

            new_config.validate()
            self.config_service.save_config(new_config)
            self.logger("Configuration saved.")

            # Notify the controller that the config has changed
            self.controller.on_config_saved()

            self.destroy()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")