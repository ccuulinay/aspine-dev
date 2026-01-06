"""
Aspine 2.0 CLI - Command-line interface using typer

Provides both foreground and daemon modes for running the Aspine server.
"""
import asyncio
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from aspine import AspineClient, create_client

app = typer.Typer(
    name="aspine",
    help="Aspine 2.0 - Python-native async + multiprocessing hybrid caching system",
    rich_markup_mode="rich",
)
console = Console()


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Set up logging configuration."""
    # Convert string level to logging constant
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = log_levels.get(log_level.upper(), logging.INFO)

    # Configure logging
    handlers = []

    # Console handler with rich formatting
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
    )
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        # Ensure directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@app.command("server")
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Server host address"),
    port: int = typer.Option(5116, "--port", "-p", help="Server port"),
    authkey: str = typer.Option("123456", "--authkey", help="Authentication key"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run as background daemon"),
    persist: bool = typer.Option(False, "--persist", help="Enable disk persistence"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Log file path"),
    pid_file: Optional[str] = typer.Option(None, "--pid-file", help="PID file path"),
    max_size: int = typer.Option(1000, "--max-size", help="Maximum cache size before LRU eviction"),
):
    """
    Start the Aspine cache server.

    Can run in foreground (blocking) or daemon (background) mode.
    """
    # Setup logging
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)

    # Show banner
    console.print(
        Panel.fit(
            f"[bold blue]Aspine 2.0 Server[/bold blue]\n"
            f"Host: {host}\n"
            f"Port: {port}\n"
            f"Max Size: {max_size}\n"
            f"Persistence: {'Enabled' if persist else 'Disabled'}\n"
            f"Daemon: {'Yes' if daemon else 'No'}",
            title="Starting Server",
        )
    )

    if daemon:
        run_daemon_server(host, port, authkey, persist, log_level, log_file, pid_file, max_size)
    else:
        run_foreground_server(host, port, authkey, persist, log_level, log_file, max_size)


def run_foreground_server(
    host: str,
    port: int,
    authkey: str,
    persist: bool,
    log_level: str,
    log_file: Optional[str],
    max_size: int,
):
    """Run server in foreground (blocking) mode."""
    logger = logging.getLogger(__name__)
    persist_path = "aspine.rdb" if persist else None

    # Create client instance
    client = AspineClient(
        host=host,
        port=port,
        authkey=authkey,
        max_size=max_size,
        persist_path=persist_path,
    )

    # Connect
    try:
        console.print("[green]Connecting to Aspine server...[/green]")
        asyncio.run(client.connect())
        console.print("[green]✓ Connected successfully![/green]")

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            console.print(f"\n[yellow]Received signal {signum}, shutting down...[/yellow]")
            asyncio.run(client.disconnect())
            console.print("[green]✓ Server stopped[/green]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep running
        console.print("\n[bold green]Server is running...[/bold green]")
        console.print("Press Ctrl+C to stop\n")

        # Display info
        info = asyncio.run(client.info())
        console.print(f"[blue]Cache Info:[/blue]")
        for key, value in info.items():
            console.print(f"  {key}: {value}")

        # Run indefinitely
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        finally:
            asyncio.run(client.disconnect())
            console.print("[green]✓ Server stopped[/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        logger.exception("Server error")
        sys.exit(1)


def run_daemon_server(
    host: str,
    port: int,
    authkey: str,
    persist: bool,
    log_level: str,
    log_file: Optional[str],
    pid_file: Optional[str],
    max_size: int,
):
    """Run server in background daemon mode."""
    logger = logging.getLogger(__name__)

    # Default PID file location
    if not pid_file:
        pid_file = "/var/run/aspine/aspine.pid"

    pid_path = Path(pid_file)

    # Check if already running
    if pid_path.exists():
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            console.print(f"[red]✗ Aspine is already running with PID {old_pid}[/red]")
            console.print(f"Use: kill {old_pid} to stop it")
            sys.exit(1)
        except (ValueError, FileNotFoundError):
            # Stale PID file, remove it
            pid_path.unlink()

    persist_path = "aspine.rdb" if persist else None

    # Create daemon directory
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    # Daemonize
    try:
        # Write PID
        pid = os.getpid()
        with open(pid_file, 'w') as f:
            f.write(str(pid))

        console.print(f"[green]✓ Daemon started with PID {pid}[/green]")
        console.print(f"PID file: {pid_file}")

        if log_file:
            console.print(f"Log file: {log_file}")

        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            # Remove PID file
            if pid_path.exists():
                pid_path.unlink()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Create and run client
        client = AspineClient(
            host=host,
            port=port,
            authkey=authkey,
            max_size=max_size,
            persist_path=persist_path,
        )

        # Connect
        asyncio.run(client.connect())
        logger.info("Aspine daemon started successfully")

        # Run indefinitely
        asyncio.get_event_loop().run_forever()

    except Exception as e:
        logger.exception("Daemon error")
        console.print(f"[red]✗ Error: {e}[/red]")
        # Clean up PID file on error
        if pid_path.exists():
            pid_path.unlink()
        sys.exit(1)


@app.command("info")
def server_info(
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
    port: int = typer.Option(5116, "--port", "-p"),
    authkey: str = typer.Option("123456", "--authkey"),
):
    """
    Get server information and statistics.
    """
    console.print("[blue]Connecting to Aspine server...[/blue]")

    async def _get_info():
        client = AspineClient(host=host, port=port, authkey=authkey)
        await client.connect()
        info = await client.info()
        await client.disconnect()
        return info

    try:
        info = asyncio.run(_get_info())
        console.print("\n[bold green]Server Information:[/bold green]")
        for key, value in info.items():
            console.print(f"  [cyan]{key}[/cyan]: {value}")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@app.command("stop")
def stop_server(
    pid_file: str = typer.Option("/var/run/aspine/aspine.pid", "--pid-file", "-f"),
    force: bool = typer.Option(False, "--force", help="Force kill the process"),
):
    """
    Stop the Aspine daemon server.
    """
    pid_path = Path(pid_file)

    if not pid_path.exists():
        console.print(f"[red]✗ PID file not found: {pid_file}[/red]")
        console.print("Is the server running?")
        sys.exit(1)

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        console.print(f"Sending SIGTERM to PID {pid}...")

        try:
            os.kill(pid, signal.SIGTERM)
            console.print("[green]✓ Sent stop signal[/green]")

            # Wait for process to exit
            import time
            for _ in range(5):
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(1)
                except OSError:
                    # Process has exited
                    break
            else:
                if force:
                    console.print("[yellow]Force killing process...[/yellow]")
                    os.kill(pid, signal.SIGKILL)
                    console.print("[green]✓ Process force killed[/green]")
                else:
                    console.print("[yellow]Process still running, use --force to force kill[/yellow]")
                    sys.exit(1)

            # Remove PID file
            pid_path.unlink()
            console.print("[green]✓ PID file removed[/green]")

        except OSError as e:
            console.print(f"[red]✗ Error stopping process: {e}[/red]")
            console.print("The process may have already stopped")
            pid_path.unlink()
            sys.exit(1)

    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]✗ Invalid PID file: {e}[/red]")
        sys.exit(1)


@app.command("clear")
def clear_cache(
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
    port: int = typer.Option(5116, "--port", "-p"),
    authkey: str = typer.Option("123456", "--authkey"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Clear all data from the cache.
    """
    if not yes:
        confirm = typer.confirm("Are you sure you want to clear all cache data?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    async def _clear():
        client = AspineClient(host=host, port=port, authkey=authkey)
        await client.connect()
        await client.clear()
        await client.disconnect()

    try:
        asyncio.run(_clear())
        console.print("[green]✓ Cache cleared successfully[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
