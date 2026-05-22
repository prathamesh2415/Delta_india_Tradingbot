#!/usr/bin/env python3
"""Start the profit vs fees web dashboard."""

import uvicorn

from trading_bot.config import Settings
from trading_bot.dashboard.server import create_app
from trading_bot.utils.logging_setup import setup_logging


def main() -> None:
    settings = Settings.from_env()
    settings.ensure_paths()
    setup_logging(settings.log_level, settings.log_file)
    app = create_app(settings)
    print(f"Dashboard: http://127.0.0.1:{settings.server_port}/")
    if settings.dashboard_password:
        print("Password required (?password=YOUR_PASSWORD)")
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
