"""Main CLI entry point with command definitions."""

import click
import asyncio
from typing import Optional

from .client import (
    OrchestratorClient,
    ConnectionError,
    AuthenticationError,
    NotFoundError,
    OrchestratorClientError,
)
from .config import Config, ConfigError
from .ui import (
    console,
    print_welcome,
    print_error,
    print_success,
    print_info,
    format_incident,
    print_incident_table,
    show_progress,
)
from .session import Session


def get_client_from_config(config: Config) -> OrchestratorClient:
    """Create orchestrator client from config."""
    url = config.get("orchestrator_url")
    api_key = config.get("api_key")

    if not url:
        raise ConfigError(
            "Orchestrator URL not configured. Run: sre-orchestrator config set orchestrator-url <url>"
        )

    return OrchestratorClient(base_url=url, api_key=api_key)


@click.group()
@click.version_option()
def cli():
    """SRE Orchestrator CLI - Investigate incidents using natural language."""
    pass


@cli.command()
@click.option("--url", help="Orchestrator URL (overrides config)")
@click.option("--api-key", help="API key (overrides config)")
def chat(url: Optional[str], api_key: Optional[str]):
    """Start interactive chat mode for incident investigation."""
    asyncio.run(chat_async(url, api_key))


async def chat_async(url: Optional[str], api_key: Optional[str]):
    """Async implementation of chat command."""
    try:
        config = Config()

        # Override config with command-line options
        if url:
            orchestrator_url = url
        else:
            orchestrator_url = config.get("orchestrator_url")

        if api_key:
            auth_key = api_key
        else:
            auth_key = config.get("api_key")

        if not orchestrator_url:
            print_error("Orchestrator URL not configured.")
            print_info(
                "Set it with: sre-orchestrator config set orchestrator-url <url>"
            )
            print_info("Or use: sre-orchestrator chat --url <url>")
            return

        print_welcome()
        print_info(f"Connected to: {orchestrator_url}")
        console.print()

        session = Session()
        client = OrchestratorClient(base_url=orchestrator_url, api_key=auth_key)

        try:
            while True:
                try:
                    # Get user input
                    user_input = await session.get_input("🔍 ")

                    if not user_input.strip():
                        continue

                    # Handle commands
                    if user_input.lower() in ["exit", "quit"]:
                        print_info("Goodbye!")
                        break
                    elif user_input.lower() == "help":
                        print_welcome()
                        continue
                    elif user_input.lower() == "list":
                        await handle_list_command(client)
                        continue
                    elif user_input.lower().startswith("show "):
                        incident_id = user_input[5:].strip()
                        await handle_show_command(client, incident_id)
                        continue

                    # Create incident
                    with show_progress() as progress:
                        task = progress.add_task("Creating incident...", total=None)
                        result = await client.create_incident(user_input)
                        incident_id = result["incident_id"]
                        progress.update(task, description="Incident created")

                    session.add_incident(incident_id)
                    print_success(f"Incident created: {incident_id[:8]}...")

                    # Poll for completion with 5-second intervals and 10-minute timeout
                    console.print()
                    try:
                        with show_progress() as progress:
                            task = progress.add_task("Investigating...", total=None)

                            def update_progress(incident):
                                status = incident.get("status", "unknown")
                                progress.update(
                                    task, description=f"Investigating... ({status})"
                                )

                            incident = await client.poll_incident(
                                incident_id,
                                interval=5.0,
                                timeout=600.0,
                                callback=update_progress,
                            )

                        # Display results
                        console.print()
                        console.print(format_incident(incident))
                        console.print()

                    except KeyboardInterrupt:
                        console.print()
                        print_info("Investigation continues in background.")
                        print_info(
                            f"Check status with: sre-orchestrator show {incident_id}"
                        )
                        print_info("Use 'exit' or 'quit' to leave")
                        continue
                    except TimeoutError as e:
                        console.print()
                        print_error(str(e))
                        print_info("Investigation continues in background.")
                        print_info(
                            f"Check status with: sre-orchestrator show {incident_id}"
                        )
                        continue

                except KeyboardInterrupt:
                    console.print()
                    print_info("Use 'exit' or 'quit' to leave")
                    continue
                except (
                    ConnectionError,
                    AuthenticationError,
                    OrchestratorClientError,
                ) as e:
                    print_error(str(e))
                    continue

        finally:
            await client.close()

    except ConfigError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


async def handle_list_command(client: OrchestratorClient):
    """Handle the list command."""
    try:
        incidents = await client.list_incidents(limit=10)
        print_incident_table(incidents)
    except (ConnectionError, OrchestratorClientError) as e:
        print_error(str(e))


async def handle_show_command(client: OrchestratorClient, incident_id: str):
    """Handle the show command."""
    try:
        incident = await client.get_incident(incident_id)
        console.print(format_incident(incident))
    except NotFoundError as e:
        print_error(str(e))
    except (ConnectionError, OrchestratorClientError) as e:
        print_error(str(e))


@cli.command()
@click.argument("description")
@click.option("--url", help="Orchestrator URL (overrides config)")
@click.option("--api-key", help="API key (overrides config)")
@click.option(
    "--wait/--no-wait", default=True, help="Wait for investigation to complete"
)
def investigate(
    description: str, url: Optional[str], api_key: Optional[str], wait: bool
):
    """Investigate an incident with a one-shot command."""
    asyncio.run(investigate_async(description, url, api_key, wait))


async def investigate_async(
    description: str, url: Optional[str], api_key: Optional[str], wait: bool
):
    """Async implementation of investigate command."""
    try:
        config = Config()

        # Override config with command-line options
        if url:
            orchestrator_url = url
        else:
            orchestrator_url = config.get("orchestrator_url")

        if api_key:
            auth_key = api_key
        else:
            auth_key = config.get("api_key")

        if not orchestrator_url:
            print_error("Orchestrator URL not configured.")
            print_info(
                "Set it with: sre-orchestrator config set orchestrator-url <url>"
            )
            print_info(
                "Or use: sre-orchestrator investigate --url <url> '<description>'"
            )
            return

        async with OrchestratorClient(
            base_url=orchestrator_url, api_key=auth_key
        ) as client:
            # Create incident
            with show_progress() as progress:
                task = progress.add_task("Creating incident...", total=None)
                result = await client.create_incident(description)
                incident_id = result["incident_id"]

            print_success(f"Incident created: {incident_id}")

            if wait:
                try:
                    # Poll for completion with 5-second intervals and 10-minute timeout
                    with show_progress() as progress:
                        task = progress.add_task("Investigating...", total=None)

                        def update_progress(incident):
                            status = incident.get("status", "unknown")
                            progress.update(
                                task, description=f"Investigating... ({status})"
                            )

                        incident = await client.poll_incident(
                            incident_id,
                            interval=5.0,
                            timeout=600.0,
                            callback=update_progress,
                        )

                    # Display results
                    console.print()
                    console.print(format_incident(incident))

                except KeyboardInterrupt:
                    console.print()
                    print_info("Investigation continues in background.")
                    print_info(
                        f"Check status with: sre-orchestrator show {incident_id}"
                    )
                except TimeoutError as e:
                    console.print()
                    print_error(str(e))
                    print_info("Investigation continues in background.")
                    print_info(
                        f"Check status with: sre-orchestrator show {incident_id}"
                    )
            else:
                print_info(
                    f"Investigation started. Check status with: sre-orchestrator show {incident_id}"
                )

    except ConfigError as e:
        print_error(str(e))
    except (ConnectionError, AuthenticationError, OrchestratorClientError) as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


@cli.command()
@click.option("--limit", default=10, help="Number of incidents to list")
@click.option("--url", help="Orchestrator URL (overrides config)")
@click.option("--api-key", help="API key (overrides config)")
def list(limit: int, url: Optional[str], api_key: Optional[str]):
    """List recent incidents."""
    asyncio.run(list_async(limit, url, api_key))


async def list_async(limit: int, url: Optional[str], api_key: Optional[str]):
    """Async implementation of list command."""
    try:
        config = Config()

        # Override config with command-line options
        if url:
            orchestrator_url = url
        else:
            orchestrator_url = config.get("orchestrator_url")

        if api_key:
            auth_key = api_key
        else:
            auth_key = config.get("api_key")

        if not orchestrator_url:
            print_error("Orchestrator URL not configured.")
            print_info(
                "Set it with: sre-orchestrator config set orchestrator-url <url>"
            )
            return

        async with OrchestratorClient(
            base_url=orchestrator_url, api_key=auth_key
        ) as client:
            incidents = await client.list_incidents(limit=limit)
            print_incident_table(incidents)

    except ConfigError as e:
        print_error(str(e))
    except (ConnectionError, OrchestratorClientError) as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


@cli.command()
@click.argument("incident_id")
@click.option("--url", help="Orchestrator URL (overrides config)")
@click.option("--api-key", help="API key (overrides config)")
def show(incident_id: str, url: Optional[str], api_key: Optional[str]):
    """Show details of a specific incident."""
    asyncio.run(show_async(incident_id, url, api_key))


async def show_async(incident_id: str, url: Optional[str], api_key: Optional[str]):
    """Async implementation of show command."""
    try:
        config = Config()

        # Override config with command-line options
        if url:
            orchestrator_url = url
        else:
            orchestrator_url = config.get("orchestrator_url")

        if api_key:
            auth_key = api_key
        else:
            auth_key = config.get("api_key")

        if not orchestrator_url:
            print_error("Orchestrator URL not configured.")
            print_info(
                "Set it with: sre-orchestrator config set orchestrator-url <url>"
            )
            return

        async with OrchestratorClient(
            base_url=orchestrator_url, api_key=auth_key
        ) as client:
            incident = await client.get_incident(incident_id)
            console.print(format_incident(incident))

    except ConfigError as e:
        print_error(str(e))
    except NotFoundError as e:
        print_error(str(e))
    except (ConnectionError, OrchestratorClientError) as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


@cli.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value."""
    try:
        cfg = Config()
        cfg.set(key, value)
        print_success(f"Configuration updated: {key} = {value}")
    except ConfigError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


@config.command(name="get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value."""
    try:
        cfg = Config()
        value = cfg.get(key)
        if value:
            console.print(f"{key} = {value}")
        else:
            print_info(f"Configuration key '{key}' not set")
    except ConfigError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


@config.command(name="list")
def config_list():
    """List all configuration values."""
    try:
        cfg = Config()
        config_data = cfg.get_all()

        if not config_data:
            print_info("No configuration set")
            return

        console.print("[bold]Configuration:[/bold]")
        for key, value in config_data.items():
            # Mask API key
            if key == "api_key" and value:
                value = "*" * 8 + value[-4:] if len(value) > 4 else "****"
            console.print(f"  {key} = {value}")

    except ConfigError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    cli()
