#!/usr/bin/env python
"""Debug script to check task manager state."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.task.manager import task_manager
from app.config import settings


async def main():
    print("=" * 50)
    print("Task Manager Debug Info")
    print("=" * 50)
    
    print(f"\nMax concurrent tasks: {task_manager.max_concurrent}")
    print(f"Running count: {task_manager.running_count}")
    print(f"Running tasks: {task_manager.get_running_info()}")
    
    print(f"\nScripts dir: {settings.SCRIPTS_DIR}")
    
    # Check if scripts directory exists
    if os.path.exists(settings.SCRIPTS_DIR):
        print(f"Scripts directory exists: Yes")
        # List task directories
        for item in os.listdir(settings.SCRIPTS_DIR):
            task_dir = os.path.join(settings.SCRIPTS_DIR, item)
            if os.path.isdir(task_dir):
                print(f"\n  Task {item}:")
                for f in os.listdir(task_dir):
                    filepath = os.path.join(task_dir, f)
                    size = os.path.getsize(filepath)
                    print(f"    - {f} ({size} bytes)")
    else:
        print(f"Scripts directory exists: No")
    
    print("\n" + "=" * 50)
    print("Cleaning up task manager state...")
    await task_manager.force_cleanup()
    print("Done! Running count now: {}".format(task_manager.running_count))


if __name__ == "__main__":
    asyncio.run(main())
