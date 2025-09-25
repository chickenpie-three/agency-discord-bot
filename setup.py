#!/usr/bin/env python3
"""
Setup script for SV Brand Assistant Discord Bot
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    env_path = Path(".env")
    template_path = Path("env_template.txt")
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
    
    if not template_path.exists():
        print("❌ env_template.txt not found")
        return False
    
    try:
        with open(template_path, 'r') as template:
            content = template.read()
        
        with open(env_path, 'w') as env_file:
            env_file.write(content)
        
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file with your actual API keys and tokens")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def create_output_directories():
    """Create output directories for generated content"""
    directories = [
        "output",
        "output/documents",
        "output/videos"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created output directories")

def check_autoagent_installation():
    """Check if AutoAgent is properly installed"""
    try:
        import autoagent
        print("✅ AutoAgent is installed")
        return True
    except ImportError:
        print("❌ AutoAgent not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "autoagent"])
            print("✅ AutoAgent installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install AutoAgent: {e}")
            return False

def main():
    """Main setup function"""
    print("🚀 Setting up SV Brand Assistant Discord Bot")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Install dependencies
    if success and not install_dependencies():
        success = False
    
    # Check AutoAgent installation
    if success and not check_autoagent_installation():
        success = False
    
    # Create .env file
    if success and not create_env_file():
        success = False
    
    # Create output directories
    if success:
        create_output_directories()
    
    print("=" * 50)
    
    if success:
        print("✅ Setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Edit .env file with your API keys and tokens")
        print("2. Create a Discord bot at https://discord.com/developers/applications")
        print("3. Invite the bot to your server with proper permissions")
        print("4. Run: python main.py")
        print("\n📖 See README.md for detailed instructions")
    else:
        print("❌ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
