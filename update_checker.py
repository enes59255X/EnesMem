"""
Update Checker Module for EnesMem
Checks for new versions from GitHub releases.
"""
import json
import urllib.request
import urllib.error
import ssl
from typing import Optional, Dict
from utils.logger import log


# GitHub repository info
GITHUB_REPO = "enes59255/EnesMem"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version() -> Dict:
    """Get current version from local file."""
    try:
        with open("version.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "version": "1.0.0",
            "build": 0,
            "channel": "stable"
        }


def fetch_latest_version(timeout: int = 5) -> Optional[Dict]:
    """
    Fetch latest version info from GitHub.
    Returns None if fetch fails.
    """
    try:
        # Create SSL context that allows us to connect
        ssl_context = ssl.create_default_context()
        
        # Try to fetch from raw GitHub first
        req = urllib.request.Request(
            VERSION_URL,
            headers={
                "User-Agent": "EnesMem-UpdateChecker/1.0"
            }
        )
        
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                log.info("UpdateChecker: Fetched version info from GitHub")
                return data
                
    except urllib.error.URLError as e:
        log.debug("UpdateChecker: Network error - %s", e)
    except json.JSONDecodeError as e:
        log.debug("UpdateChecker: JSON parse error - %s", e)
    except Exception as e:
        log.debug("UpdateChecker: Error fetching version - %s", e)
    
    return None


def compare_versions(current: str, latest: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    try:
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        
        # Pad with zeros if needed
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        
        for c, l in zip(current_parts, latest_parts):
            if c < l:
                return -1
            if c > l:
                return 1
        return 0
    except ValueError:
        # Fallback to string comparison
        if current < latest:
            return -1
        elif current > latest:
            return 1
        return 0


def check_for_updates(silent: bool = False) -> Optional[Dict]:
    """
    Check if updates are available.
    
    Args:
        silent: If True, don't log info messages (for background checks)
        
    Returns:
        Update info dict if update available, None otherwise
    """
    current = get_current_version()
    latest_data = fetch_latest_version()
    
    if not latest_data:
        if not silent:
            log.info("UpdateChecker: Could not check for updates")
        return None
    
    current_ver = current.get("version", "1.0.0")
    latest_ver = latest_data.get("version", "1.0.0")
    
    comparison = compare_versions(current_ver, latest_ver)
    
    if comparison < 0:
        # Update available
        log.info("UpdateChecker: Update available! %s -> %s", current_ver, latest_ver)
        return {
            "current_version": current_ver,
            "latest_version": latest_ver,
            "download_url": latest_data.get("download_url", RELEASES_URL),
            "changelog": latest_data.get("changelog", "No changelog available"),
            "release_date": latest_data.get("release_date", "Unknown"),
            "hash": latest_data.get("hash", ""),
            "channel": latest_data.get("channel", "stable")
        }
    elif comparison == 0:
        if not silent:
            log.info("UpdateChecker: Running latest version (%s)", current_ver)
    else:
        log.info("UpdateChecker: Running newer than release (%s > %s)", 
                 current_ver, latest_ver)
    
    return None


def format_update_message(update_info: Dict) -> str:
    """Format update information for display."""
    lines = [
        "🔄 Yeni Güncelleme Mevcut! / Update Available!",
        "",
        f"Mevcut / Current: {update_info['current_version']}",
        f"Yeni / Latest: {update_info['latest_version']}",
        f"Tarih / Date: {update_info['release_date']}",
        "",
        "Değişiklikler / Changes:",
        update_info['changelog'],
        "",
        f"İndir / Download:\n{update_info['download_url']}"
    ]
    return "\\n".join(lines)


# Auto-update check on module import (can be disabled)
if __name__ != "__main__":
    # Background check (silent)
    try:
        check_for_updates(silent=True)
    except Exception:
        pass  # Don't fail if update check fails
