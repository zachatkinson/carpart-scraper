"""Sync-images command for CLI.

Standalone command for syncing AVIF images to WordPress outside of
the scrape pipeline. Useful for retrying failed syncs or manually
pushing images that were processed in a previous scrape run.
"""

import sys
from pathlib import Path

import click
import structlog
from rich.console import Console

from src.scraper.image_processor import ImageProcessor
from src.scraper.image_syncer import ImageSyncer, LocalFileSyncer, RemoteAPISyncer

logger = structlog.get_logger()
console = Console()


@click.command("sync-images")
@click.option(
    "--wp-url",
    type=str,
    required=True,
    envvar="CSF_WP_URL",
    help="WordPress URL or local uploads path (env: CSF_WP_URL)",
)
@click.option(
    "--wp-api-key",
    type=str,
    default=None,
    envvar="CSF_WP_API_KEY",
    help="WordPress API key for remote sync (env: CSF_WP_API_KEY)",
)
@click.option(
    "--images-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="images",
    help="Image directory (default: images)",
)
@click.option(
    "--no-cleanup",
    is_flag=True,
    default=False,
    help="Skip deleting synced files after sync",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be synced without syncing",
)
def sync_images(
    wp_url: str,
    wp_api_key: str | None,
    images_dir: Path,
    no_cleanup: bool,
    dry_run: bool,
) -> None:
    r"""Sync AVIF images to WordPress.

    Reads the image manifest to find unsynced files and delivers them
    to WordPress via local file copy or REST API upload.

    After successful sync, local AVIF files are deleted from the staging
    directory unless --no-cleanup is specified.

    Examples:
        \b
        # Sync to local WordPress (DDEV)
        $ carpart sync-images --wp-url /path/to/wp-content/uploads

        \b
        # Sync to remote WordPress
        $ carpart sync-images --wp-url https://site.com --wp-api-key KEY

        \b
        # Dry run — show what would be synced
        $ carpart sync-images --wp-url /path/to/uploads --dry-run

        \b
        # Sync without cleaning up local files
        $ carpart sync-images --wp-url /path/to/uploads --no-cleanup
    """
    try:
        # Initialize image processor to access manifest
        processor = ImageProcessor(images_dir=images_dir)

        unsynced = processor.get_unsynced_files()
        if not unsynced:
            console.print("[green]All images are already synced.[/green]")
            processor.close()
            return

        if dry_run:
            console.print(f"[bold]Dry run:[/bold] {len(unsynced)} files would be synced:")
            for filename in unsynced:
                avif_path = processor.avif_dir / filename
                exists = avif_path.exists()
                status = "[green]on disk[/green]" if exists else "[yellow]missing[/yellow]"
                console.print(f"  {filename} ({status})")
            processor.close()
            return

        # Create sync strategy
        strategy = _create_strategy(wp_url, wp_api_key)

        # Verify connection
        if not strategy.verify_connection():
            console.print("[red]Error:[/red] Cannot connect to sync target.")
            processor.close()
            sys.exit(1)

        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Sync
        result = syncer.sync()
        console.print()
        console.print("[bold green]Image sync complete![/bold green]")
        console.print(f"  Uploaded:  {result.uploaded}")
        console.print(f"  Skipped:   {result.skipped}")
        console.print(f"  Failed:    {result.failed}")

        if result.errors:
            console.print()
            console.print("[yellow]Errors:[/yellow]")
            for error in result.errors:
                console.print(f"  {error}")

        # Cleanup
        if not no_cleanup and result.uploaded > 0:
            cleanup_count = syncer.cleanup()
            console.print(f"  Cleaned up: {cleanup_count} local files")

        # Close resources
        if hasattr(strategy, "close"):
            strategy.close()
        processor.close()

    except click.UsageError:
        raise
    except Exception as e:
        logger.exception("sync_images_error", error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _create_strategy(
    wp_url: str,
    wp_api_key: str | None,
) -> LocalFileSyncer | RemoteAPISyncer:
    """Create the appropriate sync strategy.

    Args:
        wp_url: WordPress URL or local directory path
        wp_api_key: API key for remote WordPress

    Returns:
        Sync strategy instance

    Raises:
        click.UsageError: If configuration is invalid
    """
    wp_path = Path(wp_url)
    if wp_path.is_dir() or (not wp_url.startswith(("http://", "https://")) and "/" in wp_url):
        return LocalFileSyncer(wp_uploads_dir=wp_path)

    if wp_url.startswith(("http://", "https://")):
        if not wp_api_key:
            msg = "--wp-api-key is required for remote WordPress sync"
            raise click.UsageError(msg)
        return RemoteAPISyncer(wp_url=wp_url, api_key=wp_api_key)

    msg = f"--wp-url must be a local directory path or HTTP(S) URL, got: {wp_url}"
    raise click.UsageError(msg)
