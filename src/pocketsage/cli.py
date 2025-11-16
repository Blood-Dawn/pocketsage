"""Flask CLI commands for PocketSage."""

from __future__ import annotations

import click


def init_app(app) -> None:
    """Register CLI commands on the Flask app."""

    @app.cli.command("pocketsage-seed")
    @click.option("--demo", is_flag=True, default=False, help="Run demo data seed")
    def pocketsage_seed(demo: bool) -> None:
        """Seed application data (demo)."""

        if demo:
            # Import here to avoid circular imports at module import time
            from .blueprints.admin.tasks import run_demo_seed

            click.echo("Scheduling demo seed...")
            run_demo_seed()
            click.echo("Demo seed completed (or scheduled).")
        else:
            click.echo("No action specified. Use --demo to seed demo data.")

    @app.cli.command("pocketsage-export")
    def pocketsage_export() -> None:
        """Export CSV/PNG artifacts into a zip file."""

        from .blueprints.admin.tasks import run_export

        click.echo("Starting export...")
        path = run_export()
        click.echo(f"Export written: {path}")
