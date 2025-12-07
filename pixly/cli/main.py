"""CLI entry point for Pixly."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from pixly.core.config import Config, ConfigError, load_config, save_config
from pixly.core.database import ScreenshotDatabase
from pixly.core.pipeline import ProcessingPipeline


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def cmd_start(args: argparse.Namespace) -> int:
    """Start background monitoring service."""
    print("Starting Pixly monitoring service...")
    
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1
    
    pipeline = ProcessingPipeline(config)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        pipeline.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    pipeline.start()
    
    print(f"Monitoring {len(config.monitored_dirs)} directories:")
    for d in config.monitored_dirs:
        print(f"  - {d}")
    print("\nPress Ctrl+C to stop.")
    
    # Keep running
    try:
        signal.pause()
    except AttributeError:
        # Windows doesn't have signal.pause
        import time
        while True:
            time.sleep(1)
    
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search screenshots."""
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1
    
    db = ScreenshotDatabase(config.db_path)
    
    try:
        results = db.search(args.query, limit=args.limit)
        
        if not results:
            print(f"No results found for: {args.query}")
            return 0
        
        print(f"Found {len(results)} result(s):\n")
        
        for r in results:
            print(f"  {r.new_name}")
            print(f"    Path: {r.filepath}")
            print(f"    Category: {r.category}")
            if r.ocr_text:
                preview = r.ocr_text[:100].replace('\n', ' ')
                print(f"    Preview: {preview}...")
            print()
        
        return 0
    finally:
        db.close()


def cmd_stats(args: argparse.Namespace) -> int:
    """Display statistics."""
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1
    
    db = ScreenshotDatabase(config.db_path)
    
    try:
        stats = db.get_stats()
        
        print("Pixly Statistics")
        print("=" * 40)
        print(f"Total screenshots: {stats['total']}")
        print(f"Total size: {stats['total_size'] / (1024*1024):.2f} MB")
        print(f"Duplicates: {stats['duplicates']}")
        
        if stats['by_category']:
            print("\nBy Category:")
            for cat, count in sorted(stats['by_category'].items()):
                print(f"  {cat}: {count}")
        
        return 0
    finally:
        db.close()


def cmd_scan(args: argparse.Namespace) -> int:
    """Process existing screenshots in directory."""
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return 1
    
    if not directory.is_dir():
        print(f"Not a directory: {directory}")
        return 1
    
    print(f"Scanning directory: {directory}")
    
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1
    
    pipeline = ProcessingPipeline(config)
    
    try:
        count = pipeline.scan_directory(directory)
        print(f"Processed {count} screenshot(s)")
        return 0
    finally:
        pipeline.stop()


def cmd_config(args: argparse.Namespace) -> int:
    """Manage configuration."""
    try:
        config = load_config()
    except ConfigError:
        # Create default config if it doesn't exist
        config = Config()
    
    if args.add_dir:
        new_dir = Path(args.add_dir).expanduser().resolve()
        
        if not new_dir.exists():
            print(f"Directory not found: {new_dir}")
            return 1
        
        if new_dir in config.monitored_dirs:
            print(f"Directory already monitored: {new_dir}")
            return 0
        
        config.monitored_dirs.append(new_dir)
        save_config(config)
        print(f"Added monitored directory: {new_dir}")
        return 0
    
    if args.remove_dir:
        remove_dir = Path(args.remove_dir).expanduser().resolve()
        
        if remove_dir not in config.monitored_dirs:
            print(f"Directory not in monitored list: {remove_dir}")
            return 1
        
        config.monitored_dirs.remove(remove_dir)
        save_config(config)
        print(f"Removed monitored directory: {remove_dir}")
        return 0
    
    if args.show:
        print("Pixly Configuration")
        print("=" * 40)
        print(f"Screenshots directory: {config.screenshots_dir}")
        print(f"Database path: {config.db_path}")
        print(f"AI model: {config.ai_model}")
        print(f"OCR min confidence: {config.ocr_min_confidence}")
        print("\nMonitored directories:")
        for d in config.monitored_dirs:
            print(f"  - {d}")
        return 0
    
    # Default: show config
    return cmd_config(argparse.Namespace(add_dir=None, remove_dir=None, show=True))


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='pixly',
        description='Pixly: Screenshots, Organized Intelligently'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # start command
    start_parser = subparsers.add_parser('start', help='Start background monitoring service')
    start_parser.set_defaults(func=cmd_start)
    
    # search command
    search_parser = subparsers.add_parser('search', help='Search screenshots')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-l', '--limit', type=int, default=20, help='Max results')
    search_parser.set_defaults(func=cmd_search)
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Display statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # scan command
    scan_parser = subparsers.add_parser('scan', help='Process existing screenshots')
    scan_parser.add_argument('directory', help='Directory to scan')
    scan_parser.set_defaults(func=cmd_scan)
    
    # config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--add-dir', help='Add monitored directory')
    config_parser.add_argument('--remove-dir', help='Remove monitored directory')
    config_parser.add_argument('--show', action='store_true', help='Show current config')
    config_parser.set_defaults(func=cmd_config)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
