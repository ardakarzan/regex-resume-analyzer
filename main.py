# main.py
import tkinter as tk
import logging
from gui.main_window import DynamicDFASimulatorApp

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                        handlers=[logging.StreamHandler()]) # Log to console

    logging.info("Starting Resume DFA Simulator Application...")

    # Create the main Tkinter window and run the app
    root = tk.Tk()
    app = DynamicDFASimulatorApp(root)
    root.mainloop()

    logging.info("Application closed.")