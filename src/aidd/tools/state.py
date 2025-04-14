import json
from pathlib import Path



# Global state management
class GlobalState:
    def __init__(self):
        self.config_dir = Path.home() / '.skydeckai-code'
        self.config_file = self.config_dir / 'config.json'
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure the config directory exists."""
        self.config_dir.mkdir(exist_ok=True)

    def _load_config(self) -> dict:
        """Load the config file."""
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_config(self, config: dict):
        """Save the config file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, sort_keys=True)
        except OSError:
            pass  # Silently fail if we can't write the config

    @property
    def allowed_directory(self) -> str:
        """Get the allowed directory, falling back to Desktop if not set."""
        config = self._load_config()
        return config.get('allowed_directory', str(Path.home() / "Desktop"))

    @allowed_directory.setter
    def allowed_directory(self, value: str):
        """Set the allowed directory and persist it."""
        self._save_config({'allowed_directory': value})

# Single instance to be shared across modules
state = GlobalState()
