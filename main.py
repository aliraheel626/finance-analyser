from src.app import App
from nicegui import ui

def main():
    # Initialize the app (builds the UI)
    App()
    
    # Run NiceGUI
    ui.run(
        title="Budget Tracker",
        native=True,  # Let's try native again with the standard setup
        port=8081,
        window_size=(1400, 900)
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
