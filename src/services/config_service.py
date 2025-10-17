"""
Configuration management service for Starshot Analyzer.

This service provides a clean interface for loading, saving, and accessing
configuration values from INI files. It follows the pragmatic hybrid approach
with dataclasses for type-safe configuration.
"""

import configparser
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class NetworkConfig:
    """Network configuration settings."""

    ip_address_app: str = "192.168.1.100"
    """IP address of the streaming application."""


@dataclass
class CropConfig:
    """Image cropping configuration settings."""

    crop_x: int = 0
    """X-coordinate of crop region top-left corner (pixels)."""

    crop_y: int = 0
    """Y-coordinate of crop region top-left corner (pixels)."""

    crop_w: int = 640
    """Width of crop region (pixels)."""

    crop_h: int = 480
    """Height of crop region (pixels)."""

    def validate(self) -> None:
        """
        Validate crop configuration values.

        Raises:
            ValueError: If configuration values are invalid.
        """
        if self.crop_w <= 0:
            raise ValueError(f"crop_w must be positive, got {self.crop_w}")
        if self.crop_h <= 0:
            raise ValueError(f"crop_h must be positive, got {self.crop_h}")
        if self.crop_x < 0:
            raise ValueError(f"crop_x must be non-negative, got {self.crop_x}")
        if self.crop_y < 0:
            raise ValueError(f"crop_y must be non-negative, got {self.crop_y}")


@dataclass
class StarshotConfig:
    """Complete Starshot Analyzer configuration."""

    network: NetworkConfig
    """Network settings."""

    crop: CropConfig
    """Image cropping settings."""

    def validate(self) -> None:
        """
        Validate all configuration sections.

        Raises:
            ValueError: If any configuration values are invalid.
        """
        self.crop.validate()


class ConfigService:
    """
    Service for managing Starshot Analyzer configuration.

    This service provides methods to load, save, and access configuration
    from INI files. It uses dataclasses for type-safe configuration management.

    Example:
        >>> service = ConfigService("config.ini")
        >>> config = service.load_config()
        >>> print(config.network.ip_address_app)
        '192.168.1.100'
        >>> config.crop.crop_w = 800
        >>> service.save_config(config)
    """

    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize the configuration service.

        Args:
            config_file: Path to the INI configuration file.
        """
        self.config_file = Path(config_file)
        self._parser = configparser.ConfigParser()
        self._logger = logging.getLogger(__name__)

    def load_config(self) -> StarshotConfig:
        """
        Load configuration from INI file.

        Returns:
            StarshotConfig: Loaded configuration with all settings.

        Raises:
            FileNotFoundError: If configuration file does not exist.
            ValueError: If configuration contains invalid values.

        Example:
            >>> service = ConfigService()
            >>> config = service.load_config()
            >>> config.network.ip_address_app
            '192.168.1.100'
        """
        if not self.config_file.exists():
            self._logger.warning(
                f"Config file {self.config_file} not found, creating default"
            )
            return self._create_default_config()

        try:
            self._parser.read(self.config_file)

            # Load network configuration
            network = NetworkConfig(
                ip_address_app=self._parser.get(
                    'network', 'ip_address_app', fallback="192.168.1.100"
                )
            )

            # Load crop configuration
            crop = CropConfig(
                crop_x=self._parser.getint('crop', 'crop_x', fallback=0),
                crop_y=self._parser.getint('crop', 'crop_y', fallback=0),
                crop_w=self._parser.getint('crop', 'crop_w', fallback=640),
                crop_h=self._parser.getint('crop', 'crop_h', fallback=480),
            )

            config = StarshotConfig(network=network, crop=crop)
            config.validate()

            self._logger.info(f"Configuration loaded from {self.config_file}")
            return config

        except (configparser.Error, ValueError) as e:
            self._logger.error(f"Error loading config: {e}")
            raise ValueError(f"Invalid configuration file: {e}") from e

    def save_config(self, config: StarshotConfig) -> None:
        """
        Save configuration to INI file.

        Args:
            config: Configuration to save.

        Raises:
            ValueError: If configuration contains invalid values.
            IOError: If unable to write to configuration file.

        Example:
            >>> config = StarshotConfig(
            ...     network=NetworkConfig(ip_address_app="192.168.1.200"),
            ...     crop=CropConfig(crop_w=800, crop_h=600)
            ... )
            >>> service = ConfigService()
            >>> service.save_config(config)
        """
        # Validate before saving
        config.validate()

        # Create new parser for saving
        parser = configparser.ConfigParser()

        # Network section
        parser.add_section('network')
        parser.set('network', 'ip_address_app', config.network.ip_address_app)

        # Crop section
        parser.add_section('crop')
        parser.set('crop', 'crop_x', str(config.crop.crop_x))
        parser.set('crop', 'crop_y', str(config.crop.crop_y))
        parser.set('crop', 'crop_w', str(config.crop.crop_w))
        parser.set('crop', 'crop_h', str(config.crop.crop_h))

        try:
            with open(self.config_file, 'w') as f:
                parser.write(f)
            self._logger.info(f"Configuration saved to {self.config_file}")
        except IOError as e:
            self._logger.error(f"Error saving config: {e}")
            raise IOError(f"Unable to save configuration: {e}") from e

    def _create_default_config(self) -> StarshotConfig:
        """
        Create and save default configuration.

        Returns:
            StarshotConfig: Default configuration.
        """
        config = StarshotConfig(
            network=NetworkConfig(),
            crop=CropConfig()
        )

        try:
            self.save_config(config)
            self._logger.info("Default configuration created")
        except IOError:
            self._logger.warning("Could not save default configuration")

        return config

    def get_value(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """
        Get a raw configuration value from INI file.

        Args:
            section: Configuration section name.
            key: Configuration key name.
            fallback: Value to return if key not found.

        Returns:
            str: Configuration value or fallback.

        Example:
            >>> service = ConfigService()
            >>> ip = service.get_value('network', 'ip_address_app')
        """
        if not self._parser.sections():
            self._parser.read(self.config_file)

        return self._parser.get(section, key, fallback=fallback)

    def reload(self) -> StarshotConfig:
        """
        Reload configuration from file.

        Returns:
            StarshotConfig: Reloaded configuration.

        Example:
            >>> service = ConfigService()
            >>> # ... external modification of config.ini ...
            >>> config = service.reload()
        """
        self._parser.clear()
        return self.load_config()
