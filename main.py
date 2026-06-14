#!/usr/bin/env python3
"""
PaperSearch Main Entry Point

This script launches the PaperSearch GUI application.
"""

import sys
import os

def main():
    """Launch the PaperSearch GUI."""
    # Add src directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        from papersearch.gui.gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI module: {e}")
        print("Please make sure the package is installed correctly.")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching PaperSearch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
