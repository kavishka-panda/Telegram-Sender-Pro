import asyncio
from concurrent.futures import ThreadPoolExecutor

# Global thread pool executor
executor = ThreadPoolExecutor(max_workers=1)

def run_async(coro):
    """
    Runs a coroutine in a separate thread's event loop.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)

def shutdown_executor():
    """Shuts down the global executor."""
    executor.shutdown()
