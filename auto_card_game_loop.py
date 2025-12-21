"""
Continuous Automated Card Matching Game Player

Runs multiple games in a loop without user input.
Useful for farming/grinding the card matching game automatically.
"""

import time
import sys
from log_helper import log
from auto_card_game import AutoCardGame


def run_continuous_games(num_games=None, delay_between_games=5.0, dry_run=False):
    """Run multiple card matching games automatically.
    
    Args:
        num_games: Number of games to play (None = infinite)
        delay_between_games: Seconds to wait between games
        dry_run: If True, don't actually click cards (for testing)
        
    Returns:
        Statistics dict with game results
    """
    stats = {
        'total_games': 0,
        'successful': 0,
        'failed': 0,
        'start_time': time.time()
    }
    
    game_player = AutoCardGame()
    game_count = 0
    
    try:
        while True:
            game_count += 1
            stats['total_games'] = game_count
            
            if num_games and game_count > num_games:
                log(f"\n✅ Completed target of {num_games} games")
                break
            
            log("\n" + "=" * 70)
            log(f"GAME {game_count}" + (f" of {num_games}" if num_games else ""))
            log("=" * 70)
            
            # Run the game
            success = game_player.run_full_game(dry_run=dry_run)
            
            if success:
                stats['successful'] += 1
                log(f"\n✅ Game {game_count} completed successfully!")
            else:
                stats['failed'] += 1
                log(f"\n❌ Game {game_count} failed!")
                
                # Ask if user wants to continue after failure
                if not dry_run:
                    log("\nGame failed. Options:")
                    log("  - Press ENTER to continue to next game")
                    log("  - Press Ctrl+C to stop")
                    try:
                        input()
                    except KeyboardInterrupt:
                        log("\nStopping after failure...")
                        break
            
            # Show running stats
            elapsed = time.time() - stats['start_time']
            avg_time = elapsed / game_count if game_count > 0 else 0
            log("\n" + "-" * 70)
            log("STATISTICS:")
            log(f"  Games played: {stats['total_games']}")
            log(f"  Successful: {stats['successful']} ({stats['successful']/stats['total_games']*100:.1f}%)")
            log(f"  Failed: {stats['failed']} ({stats['failed']/stats['total_games']*100:.1f}%)")
            log(f"  Total time: {elapsed/60:.1f} minutes")
            log(f"  Average time per game: {avg_time:.1f} seconds")
            log("-" * 70)
            
            # Wait before next game
            if num_games is None or game_count < num_games:
                log(f"\nWaiting {delay_between_games}s before next game...")
                time.sleep(delay_between_games)
    
    except KeyboardInterrupt:
        log("\n\n🛑 Stopped by user (Ctrl+C)")
    
    # Final summary
    log("\n" + "=" * 70)
    log("FINAL SUMMARY")
    log("=" * 70)
    log(f"Total games: {stats['total_games']}")
    log(f"Successful: {stats['successful']}")
    log(f"Failed: {stats['failed']}")
    
    if stats['total_games'] > 0:
        success_rate = stats['successful'] / stats['total_games'] * 100
        log(f"Success rate: {success_rate:.1f}%")
    
    elapsed = time.time() - stats['start_time']
    log(f"Total runtime: {elapsed/60:.1f} minutes")
    log("=" * 70)
    
    return stats


def main():
    """Main entry point."""
    
    log("Continuous Automated Card Matching Game")
    log("=" * 70)
    log("")
    log("This will run multiple games automatically without user input.")
    log("")
    log("Options:")
    log("  --games N     : Play N games then stop (default: infinite)")
    log("  --delay N     : Wait N seconds between games (default: 3)")
    log("  --dry-run     : Test mode, don't click cards")
    log("")
    log("Press Ctrl+C at any time to stop gracefully.")
    log("")
    
    # Parse arguments
    num_games = None
    delay = 3.0
    dry_run = False
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--games" and i + 1 < len(sys.argv):
            num_games = int(sys.argv[i + 1])
            i += 2
        elif arg == "--delay" and i + 1 < len(sys.argv):
            delay = float(sys.argv[i + 1])
            i += 2
        elif arg in ["--dry-run", "-n"]:
            dry_run = True
            i += 1
        else:
            i += 1
    
    if num_games:
        log(f"Will play {num_games} games")
    else:
        log("Will play games continuously (infinite loop)")
    
    log(f"Delay between games: {delay}s")
    
    if dry_run:
        log("\n*** DRY RUN MODE - Will not click cards ***")
    
    log("")
    log("Make sure:")
    log("  - Card matching game is visible")
    log("  - Run Button is visible on screen")
    log("  - Templates configured correctly")
    log("  - Config coordinates set up")
    log("")
    
    input("Press ENTER to start automated games...")
    log("")
    
    stats = run_continuous_games(
        num_games=num_games,
        delay_between_games=delay,
        dry_run=dry_run
    )
    
    # Return exit code based on success rate
    if stats['total_games'] > 0:
        success_rate = stats['successful'] / stats['total_games']
        return 0 if success_rate >= 0.8 else 1  # 80% success rate threshold
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
