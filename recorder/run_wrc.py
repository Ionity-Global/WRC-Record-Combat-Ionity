# Entry point used by PyInstaller to build WRC-Recorder.exe
import sys
from wrc_recorder.app import main
if __name__ == "__main__":
    sys.exit(main())
