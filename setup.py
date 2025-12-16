#!/usr/bin/env python3
"""
VVV Token Watch - Interactive Setup Script
Walks users through installation, dependency setup, and configuration.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def disable(cls):
        """Disable colors for Windows or non-TTY environments."""
        cls.HEADER = ''
        cls.BLUE = ''
        cls.CYAN = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.ENDC = ''
        cls.BOLD = ''
        cls.UNDERLINE = ''


# Disable colors on Windows unless ANSICON is set
if platform.system() == 'Windows' and 'ANSICON' not in os.environ:
    Colors.disable()


class SetupWizard:
    """Interactive setup wizard for VVV Token Watch."""

    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.venv_path = self.project_root / 'venv'
        self.env_file = self.project_root / '.env'
        self.env_example = self.project_root / '.env.example'
        self.requirements_file = self.project_root / 'requirements.txt'
        self.is_windows = platform.system() == 'Windows'
        self.python_cmd = 'python' if self.is_windows else 'python3'

    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}\n")

    def print_success(self, text: str):
        """Print a success message."""
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

    def print_error(self, text: str):
        """Print an error message."""
        print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

    def print_warning(self, text: str):
        """Print a warning message."""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

    def print_info(self, text: str):
        """Print an info message."""
        print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")

    def check_python_version(self) -> bool:
        """Check if Python version meets minimum requirements."""
        self.print_header("Checking Python Version")
        
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        
        print(f"Detected Python version: {version_str}")
        
        if version_info < (3, 8):
            self.print_error(f"Python 3.8+ is required, but you have {version_str}")
            self.print_info("Please upgrade Python and try again.")
            return False
        
        self.print_success(f"Python {version_str} meets requirements (3.8+)")
        return True

    def check_venv(self) -> bool:
        """Check if virtual environment exists."""
        return self.venv_path.exists()

    def create_venv(self) -> bool:
        """Create virtual environment."""
        self.print_header("Setting Up Virtual Environment")
        
        if self.check_venv():
            self.print_info(f"Virtual environment already exists at: {self.venv_path}")
            response = input(f"{Colors.YELLOW}Recreate virtual environment? (y/N): {Colors.ENDC}").strip().lower()
            if response != 'y':
                self.print_info("Using existing virtual environment")
                return True
            self.print_info("Removing existing virtual environment...")
            shutil.rmtree(self.venv_path)
        
        print(f"Creating virtual environment at: {self.venv_path}")
        try:
            subprocess.run([self.python_cmd, '-m', 'venv', str(self.venv_path)], check=True)
            self.print_success("Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to create virtual environment: {e}")
            return False

    def get_pip_cmd(self) -> str:
        """Get the pip command for the virtual environment."""
        if self.is_windows:
            return str(self.venv_path / 'Scripts' / 'pip.exe')
        else:
            return str(self.venv_path / 'bin' / 'pip')

    def get_python_venv_cmd(self) -> str:
        """Get the python command for the virtual environment."""
        if self.is_windows:
            return str(self.venv_path / 'Scripts' / 'python.exe')
        else:
            return str(self.venv_path / 'bin' / 'python')

    def install_dependencies(self) -> bool:
        """Install Python dependencies from requirements.txt."""
        self.print_header("Installing Dependencies")
        
        if not self.requirements_file.exists():
            self.print_error(f"requirements.txt not found at: {self.requirements_file}")
            return False
        
        pip_cmd = self.get_pip_cmd()
        print(f"Installing packages from requirements.txt...")
        print(f"{Colors.CYAN}This may take a few minutes...{Colors.ENDC}\n")
        
        try:
            # Try to upgrade pip first (may fail on Windows, which is okay)
            python_cmd = self.get_python_venv_cmd()
            try:
                subprocess.run([python_cmd, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                              check=True, capture_output=True, text=True)
                self.print_success("pip upgraded successfully")
            except subprocess.CalledProcessError:
                # Pip upgrade failed (common on Windows) - not critical, continue anyway
                self.print_warning("Could not upgrade pip (this is okay, continuing...)")
            
            # Install requirements
            subprocess.run([pip_cmd, 'install', '-r', str(self.requirements_file)], check=True)
            
            self.print_success("All dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install dependencies: {e}")
            return False

    def get_input(self, prompt: str, default: Optional[str] = None, required: bool = False, secret: bool = False) -> str:
        """Get user input with optional default value."""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        while True:
            if secret:
                # For sensitive input like API keys, we won't use getpass to keep it simple
                # User can see what they type to avoid mistakes
                value = input(f"{Colors.YELLOW}{full_prompt}{Colors.ENDC}").strip()
            else:
                value = input(f"{Colors.YELLOW}{full_prompt}{Colors.ENDC}").strip()
            
            if not value and default:
                return default
            elif not value and required:
                self.print_error("This field is required. Please enter a value.")
                continue
            elif not value and not required:
                return ""
            else:
                return value

    def validate_api_key(self, key: str) -> Tuple[bool, str]:
        """Basic validation for Venice API key format."""
        if not key:
            return False, "API key cannot be empty"
        
        # Basic length check (Venice keys are typically long)
        if len(key) < 20:
            return False, "API key seems too short (should be 20+ characters)"
        
        # Check for common placeholder values
        placeholders = ['your-api-key', 'paste-here', 'xxx', 'replace-me']
        if key.lower() in placeholders:
            return False, "Please replace the placeholder with your actual API key"
        
        return True, "Format looks valid"

    def test_admin_key(self, admin_key: str) -> bool:
        """Test Venice Admin API key by making a test request using venv's Python."""
        self.print_info("Testing admin key connectivity...")
        
        # Create a test script to run in the venv
        test_script = """
import sys
import requests

admin_key = sys.argv[1]
url = "https://api.venice.ai/api/v1/billing/usage"
headers = {
    "Authorization": f"Bearer {admin_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    sys.exit(response.status_code)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(500)
"""
        
        try:
            python_cmd = self.get_python_venv_cmd()
            result = subprocess.run(
                [python_cmd, '-c', test_script, admin_key],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 200:
                self.print_success("Admin key verified! Successfully connected to Venice API")
                return True
            elif result.returncode == 401:
                self.print_error("Admin key authentication failed (401)")
                self.print_warning("Make sure you're using an ADMIN key, not an inference key")
                return False
            elif result.returncode == 500:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.print_warning(f"Could not test key: {error_msg}")
                self.print_info("Key will be validated when you run the application")
                return True
            else:
                self.print_warning(f"Unexpected response code: {result.returncode}")
                self.print_info("Key may still work, but couldn't verify")
                return True
        except subprocess.TimeoutExpired:
            self.print_warning("API test timed out")
            self.print_info("Key will be validated when you run the application")
            return True
        except Exception as e:
            self.print_warning(f"Could not test key: {e}")
            self.print_info("Key will be validated when you run the application")
            return True

    def configure_environment(self) -> bool:
        """Interactive configuration of .env file."""
        self.print_header("Configuration Wizard")
        
        if self.env_file.exists():
            self.print_warning(f".env file already exists at: {self.env_file}")
            response = self.get_input("Overwrite existing .env file? (y/N)", default="n")
            if response.lower() != 'y':
                self.print_info("Keeping existing .env file")
                return True
            # Backup existing .env
            backup_path = self.env_file.with_suffix('.env.backup')
            shutil.copy(self.env_file, backup_path)
            self.print_info(f"Backed up existing .env to: {backup_path}")
        
        print(f"\n{Colors.BOLD}Venice API Configuration{Colors.ENDC}")
        print(f"{Colors.CYAN}Get your API keys from: https://venice.ai/settings/api{Colors.ENDC}\n")
        
        # Required: Admin Key
        print(f"{Colors.BOLD}REQUIRED: Venice Admin API Key{Colors.ENDC}")
        print("This monitoring application requires an Admin key for billing/usage data.")
        print(f"{Colors.RED}IMPORTANT: Must be 'Admin' key type, NOT 'Inference Only'{Colors.ENDC}")
        print("Regular inference keys will fail with 401 Unauthorized.\n")
        
        while True:
            admin_key = self.get_input("VENICE_ADMIN_KEY", required=True, secret=True)
            is_valid, msg = self.validate_api_key(admin_key)
            if not is_valid:
                self.print_error(msg)
                continue
            
            # Optionally test the key
            test_response = self.get_input("Test admin key now? (Y/n)", default="y")
            if test_response.lower() != 'n':
                if self.test_admin_key(admin_key):
                    break
                else:
                    retry = self.get_input("Key test failed. Use this key anyway? (y/N)", default="n")
                    if retry.lower() == 'y':
                        break
            else:
                break
        
        # Optional: Inference Key
        print(f"\n{Colors.BOLD}OPTIONAL: Venice Inference API Key{Colors.ENDC}")
        print("Not currently used by this monitoring application.")
        print("Reserved for potential future model testing features.")
        inference_key = self.get_input("VENICE_API_KEY (press Enter to skip)", required=False, secret=True)
        
        if inference_key:
            is_valid, msg = self.validate_api_key(inference_key)
            if not is_valid:
                self.print_warning(f"Inference key validation: {msg}")
        
        # Optional: CoinGecko Settings
        print(f"\n{Colors.BOLD}CoinGecko Configuration (Optional){Colors.ENDC}")
        print("Configure cryptocurrency price tracking for Venice (VVV) and DIEM tokens.\n")
        
        configure_coingecko = self.get_input("Configure CoinGecko settings? (y/N)", default="n")
        
        if configure_coingecko.lower() == 'y':
            vvv_holdings = self.get_input("Your VVV token holdings", default="2750")
            diem_holdings = self.get_input("Your DIEM token holdings", default="0")
            currencies = self.get_input("Currencies to track (comma-separated)", default="usd,aud")
        else:
            vvv_holdings = "2750"
            diem_holdings = "0"
            currencies = "usd,aud"
        
        # Optional: Refresh Intervals
        print(f"\n{Colors.BOLD}Refresh Intervals (Optional){Colors.ENDC}")
        configure_intervals = self.get_input("Customize refresh intervals? (y/N)", default="n")
        
        if configure_intervals.lower() == 'y':
            usage_interval = self.get_input("Usage data refresh interval (ms)", default="30000")
            price_interval = self.get_input("Price data refresh interval (ms)", default="60000")
        else:
            usage_interval = "30000"
            price_interval = "60000"
        
        # Theme
        print(f"\n{Colors.BOLD}Theme Selection{Colors.ENDC}")
        theme = self.get_input("UI theme (dark/light)", default="dark")
        
        # Write .env file
        self.print_info("Writing configuration to .env file...")
        
        env_content = f"""# VVV Token Watch - Environment Configuration
# Generated by setup.py on {platform.node()}

# ============================================================================
# VENICE AI API KEYS - From https://venice.ai/settings/api
# ============================================================================

# REQUIRED: Venice Admin API Key (for billing/usage monitoring)
VENICE_ADMIN_KEY={admin_key}

# OPTIONAL: Venice Inference API Key (for future features)
VENICE_API_KEY={inference_key}

# ============================================================================
# COINGECKO CONFIGURATION
# ============================================================================

COINGECKO_TOKEN_ID=venice-token
COINGECKO_CURRENCIES={currencies}
COINGECKO_HOLDING_AMOUNT={vvv_holdings}
COINGECKO_REFRESH_INTERVAL_MS={price_interval}
COINGECKO_INITIAL_DELAY_MS=500

DIEM_TOKEN_ID=diem
DIEM_HOLDING_AMOUNT={diem_holdings}

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

THEME_MODE={theme}
USAGE_REFRESH_INTERVAL_MS={usage_interval}

# ============================================================================
# ADVANCED SETTINGS (defaults work for most users)
# ============================================================================

API_PAGE_SIZE=500
API_MAX_PAGES=20
DEFAULT_DAILY_DIEM_LIMIT=100.0
DEFAULT_DAILY_USD_LIMIT=25.0
DEFAULT_EXCHANGE_RATE=0.72
"""
        
        try:
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            self.print_success(f"Configuration saved to: {self.env_file}")
            return True
        except Exception as e:
            self.print_error(f"Failed to write .env file: {e}")
            return False

    def print_launch_instructions(self):
        """Print instructions for launching the application."""
        self.print_header("Setup Complete!")
        
        print(f"{Colors.GREEN}✓ Python version verified{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Virtual environment created{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Dependencies installed{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Configuration file created{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}\n")
        
        if self.is_windows:
            print(f"  {Colors.CYAN}1. Launch the application:{Colors.ENDC}")
            print(f"     {Colors.BOLD}run.bat{Colors.ENDC}")
            print(f"\n  {Colors.CYAN}2. Or manually:{Colors.ENDC}")
            print(f"     {Colors.BOLD}venv\\Scripts\\activate{Colors.ENDC}")
            print(f"     {Colors.BOLD}python run.py{Colors.ENDC}")
        else:
            print(f"  {Colors.CYAN}1. Activate the virtual environment:{Colors.ENDC}")
            print(f"     {Colors.BOLD}source venv/bin/activate{Colors.ENDC}")
            print(f"\n  {Colors.CYAN}2. Launch the application:{Colors.ENDC}")
            print(f"     {Colors.BOLD}python run.py{Colors.ENDC}")
        
        print(f"\n{Colors.YELLOW}Tips:{Colors.ENDC}")
        print(f"  • Edit .env file anytime to update configuration")
        print(f"  • Run 'python setup.py' again to reconfigure")
        print(f"  • Check error_log.txt if you encounter issues\n")

    def run(self) -> int:
        """Run the complete setup wizard."""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print(r"""
╦  ╦╦  ╦╦  ╦  ╔╦╗┌─┐┬┌─┌─┐┌┐┌  ╦ ╦┌─┐┌┬┐┌─┐┬ ┬
╚╗╔╝╚╗╔╝╚╗╔╝   ║ │ │├┴┐├┤ │││  ║║║├─┤ │ │  ├─┤
 ╚╝  ╚╝  ╚╝    ╩ └─┘┴ ┴└─┘┘└┘  ╚╩╝┴ ┴ ┴ └─┘┴ ┴
        """)
        print(f"         Venice AI Usage Monitor - Setup Wizard")
        print(f"{Colors.ENDC}")
        
        # Step 1: Check Python version
        if not self.check_python_version():
            return 1
        
        # Step 2: Create virtual environment
        if not self.create_venv():
            return 1
        
        # Step 3: Install dependencies
        if not self.install_dependencies():
            return 1
        
        # Step 4: Configure environment
        if not self.configure_environment():
            return 1
        
        # Step 5: Print launch instructions
        self.print_launch_instructions()
        
        return 0


def main():
    """Main entry point."""
    wizard = SetupWizard()
    try:
        exit_code = wizard.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error during setup: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
