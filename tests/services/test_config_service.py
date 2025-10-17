import unittest
import os
import configparser
from pathlib import Path

from src.services.config_service import ConfigService, StarshotConfig, NetworkConfig, CropConfig

class TestConfigService(unittest.TestCase):
    """Unit tests for the ConfigService."""

    def setUp(self):
        """Set up the test case."""
        self.config_file = "test_config.ini"
        self.service = ConfigService(config_file=self.config_file)

    def tearDown(self):
        """Tear down the test case."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    def test_load_config_creates_default_if_not_exists(self):
        """Test that a default config is created if one doesn't exist."""
        config = self.service.load_config()
        self.assertTrue(os.path.exists(self.config_file))
        self.assertIsInstance(config, StarshotConfig)
        self.assertEqual(config.network.ip_address_app, "192.168.1.100")

    def test_load_config_loads_existing(self):
        """Test that an existing config file is loaded correctly."""
        parser = configparser.ConfigParser()
        parser["network"] = {"ip_address_app": "10.0.0.1"}
        parser["crop"] = {"crop_x": "10", "crop_y": "20", "crop_w": "30", "crop_h": "40"}
        with open(self.config_file, "w") as f:
            parser.write(f)

        config = self.service.load_config()
        self.assertEqual(config.network.ip_address_app, "10.0.0.1")
        self.assertEqual(config.crop.crop_x, 10)

    def test_save_config_writes_to_file(self):
        """Test that saving a config writes it to the file."""
        config = StarshotConfig(
            network=NetworkConfig(ip_address_app="1.2.3.4"),
            crop=CropConfig(crop_x=1, crop_y=2, crop_w=3, crop_h=4)
        )
        self.service.save_config(config)

        parser = configparser.ConfigParser()
        parser.read(self.config_file)
        self.assertEqual(parser.get("network", "ip_address_app"), "1.2.3.4")
        self.assertEqual(parser.getint("crop", "crop_x"), 1)

    def test_crop_config_validation(self):
        """Test the validation logic in the CropConfig."""
        with self.assertRaises(ValueError):
            CropConfig(crop_w=-10).validate()
        with self.assertRaises(ValueError):
            CropConfig(crop_x=-10).validate()

if __name__ == '__main__':
    unittest.main()