import asyncio
from src.ui.app_ui import App
from src.utils.async_runner import shutdown_executor

def main():
    """
    Main function to run the application.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = App(loop)
    app.mainloop()

    # Clean up resources
    shutdown_executor()

    # It's good practice to also close the loop
    # although in this script, it might not be strictly necessary
    # as the program is ending.
    loop.close()

if __name__ == "__main__":
    main()
