"""Runner script template - executed as subprocess for each task."""
import sys
import os
import json
import datetime


def log(level, msg):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def main():
    run_id = os.environ.get("SPIDER_RUN_ID", "0")
    task_id = os.environ.get("SPIDER_TASK_ID", "0")
    config_json = os.environ.get("SPIDER_CONFIG", "{}")
    config = json.loads(config_json)

    log("INFO", f"=== Task {task_id} (run {run_id}) started ===")
    log("INFO", f"Engine: {config.get('engine', 'requests')}")
    log("INFO", f"URL: {config.get('url', 'N/A')}")

    try:
        engine_name = config.get("engine", "requests")
        url = config.get("url", "")
        max_pages = config.get("max_pages", 1)
        headers = config.get("headers", {})
        timeout = config.get("timeout", 30)

        if not url:
            log("ERROR", "No URL configured")
            sys.exit(1)

        # Import and use the engine
        from app.engine.engine_factory import get_engine
        from app.engine import EngineConfig
        import asyncio

        async def run():
            engine = get_engine(engine_name)
            total = 0
            async with engine:
                for page in range(1, max_pages + 1):
                    page_url = url.replace("{page}", str(page))
                    log("INFO", f"Fetching page {page}: {page_url}")
                    ec = EngineConfig(url=page_url, headers=headers, timeout=timeout)
                    resp = await engine.fetch(ec)
                    if resp.ok:
                        log("INFO", f"Page {page}: {resp.status_code} - {len(resp.text)} chars")
                        total += 1
                    else:
                        log("ERROR", f"Page {page} failed: {resp.error or resp.status_code}")
            log("INFO", f"=== Completed: {total}/{max_pages} pages crawled ===")

        asyncio.run(run())

    except Exception as e:
        log("ERROR", f"Task failed: {e}")
        import traceback
        log("ERROR", traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
