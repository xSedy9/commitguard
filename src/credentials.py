"""
Secure file-based credential storage for commitguard.

Stores API keys in a dedicated user-level credentials file (~/.commitguard/credentials)
with restricted file permissions (POSIX 0600 / Windows user ACL), avoiding
environment variable exposure and child process inheritance.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_credentials_path() -> Path:
    """
    Return the path to the commitguard credentials file.

    Defaults to ~/.commitguard/credentials. Can be overridden via
    the COMMITGUARD_CREDENTIALS_FILE environment variable (primarily for tests).
    """
    override = os.environ.get("COMMITGUARD_CREDENTIALS_FILE")
    if override:
        return Path(override)
    return Path.home() / ".commitguard" / "credentials"


def _ensure_secure_dir(dir_path: Path) -> None:
    """Create directory if needed and restrict permissions to owner (0700)."""
    dir_path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        try:
            dir_path.chmod(0o700)
        except OSError:
            pass


def _ensure_secure_file(file_path: Path) -> None:
    """Set strict file permissions (0600 on POSIX, ACL on Windows)."""
    if os.name == "posix":
        try:
            file_path.chmod(0o600)
        except OSError:
            pass
    elif sys.platform == "win32":
        try:
            username = os.environ.get("USERNAME")
            if username:
                subprocess.run(
                    ["icacls", str(file_path), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                    capture_output=True,
                    check=False,
                )
        except Exception:
            pass


def load_credentials() -> dict[str, str]:
    """
    Load key-value pairs from the credentials file.

    Returns an empty dictionary if the file does not exist or is unreadable.
    """
    path = get_credentials_path()
    if not path.is_file():
        return {}

    credentials: dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
            elif ":" in line:
                k, v = line.split(":", 1)
            else:
                continue

            k = k.strip().lower()
            v = v.strip().strip("'\"")
            if k and v:
                credentials[k] = v
    except OSError:
        return {}

    return credentials


def get_credential(provider: str) -> Optional[str]:
    """
    Retrieve an API key for the given provider from credentials.

    Args:
        provider: Provider identifier (e.g. 'gemini', 'openai', 'anthropic').

    Returns:
        The API key string, or None if not configured.
    """
    creds = load_credentials()
    norm = provider.strip().lower()

    # Candidate keys to look up in the credentials mapping
    candidates: list[str]
    if norm == "gemini":
        candidates = ["gemini", "gemini_api_key", "google", "google_api_key"]
    elif norm == "openai":
        candidates = ["openai", "openai_api_key"]
    elif norm in ("anthropic", "claude"):
        candidates = ["anthropic", "anthropic_api_key", "claude", "claude_api_key"]
    else:
        candidates = [norm, f"{norm}_api_key"]

    for candidate in candidates:
        if candidate in creds:
            return creds[candidate]

    return None


def set_credential(provider: str, key: str) -> Path:
    """
    Save or update an API key for the given provider in ~/.commitguard/credentials.

    Args:
        provider: Provider identifier (e.g. 'gemini', 'openai', 'anthropic').
        key: The API key string.

    Returns:
        The Path to the updated credentials file.
    """
    path = get_credentials_path()
    _ensure_secure_dir(path.parent)

    norm = provider.strip().lower()
    creds = load_credentials()
    creds[norm] = key.strip()

    lines = [
        "# commitguard credentials",
        "# This file contains sensitive API keys. Keep file permissions restricted.",
        "",
    ]
    for k, v in sorted(creds.items()):
        lines.append(f"{k} = {v}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    _ensure_secure_file(path)
    return path


def remove_credential(provider: str) -> bool:
    """
    Remove any credential associated with the given provider.

    Returns:
        True if a credential was removed, False if not found.
    """
    path = get_credentials_path()
    if not path.is_file():
        return False

    norm = provider.strip().lower()
    creds = load_credentials()

    candidates: list[str]
    if norm == "gemini":
        candidates = ["gemini", "gemini_api_key", "google", "google_api_key"]
    elif norm == "openai":
        candidates = ["openai", "openai_api_key"]
    elif norm in ("anthropic", "claude"):
        candidates = ["anthropic", "anthropic_api_key", "claude", "claude_api_key"]
    else:
        candidates = [norm, f"{norm}_api_key"]

    removed = False
    for candidate in candidates:
        if candidate in creds:
            del creds[candidate]
            removed = True

    if not removed:
        return False

    lines = [
        "# commitguard credentials",
        "# This file contains sensitive API keys. Keep file permissions restricted.",
        "",
    ]
    for k, v in sorted(creds.items()):
        lines.append(f"{k} = {v}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    _ensure_secure_file(path)
    return True


def mask_key(key: str) -> str:
    """Return a masked representation of a sensitive key."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def list_credentials() -> dict[str, str]:
    """Return a dictionary of configured providers and their masked keys."""
    creds = load_credentials()
    return {k: mask_key(v) for k, v in creds.items()}


def handle_auth_command(argv: list[str]) -> int:
    """
    CLI command handler for credential management.

    Supported commands:
        set <provider> <key>
        get <provider>
        remove <provider>
        list
        path
    """
    if not argv or argv[0] in ("--help", "-h", "help"):
        sys.stderr.write(
            "commitguard auth — manage API credentials\n\n"
            "Usage:\n"
            "    git auth set <provider> <key>    Save an API key (gemini, openai, anthropic)\n"
            "    git auth get <provider>          Show masked API key\n"
            "    git auth remove <provider>       Remove stored key for provider\n"
            "    git auth list                    List all configured credentials\n"
            "    git auth path                    Display path to credentials file\n\n"
            "Credentials are saved to ~/.commitguard/credentials with owner-only access.\n"
        )
        return 0

    subcommand = argv[0].lower()

    if subcommand == "path":
        sys.stdout.write(f"{get_credentials_path()}\n")
        return 0

    if subcommand == "list":
        creds = list_credentials()
        if not creds:
            sys.stdout.write("[commitguard] No credentials configured in ~/.commitguard/credentials\n")
            return 0
        sys.stdout.write("[commitguard] Configured credentials:\n")
        for p, masked in sorted(creds.items()):
            sys.stdout.write(f"  {p}: {masked}\n")
        return 0

    if subcommand == "get":
        if len(argv) < 2:
            sys.stderr.write("[commitguard] Error: missing provider name. Usage: git auth get <provider>\n")
            return 1
        provider = argv[1].lower()
        key = get_credential(provider)
        if not key:
            sys.stderr.write(f"[commitguard] No credential configured for '{provider}'.\n")
            return 1
        sys.stdout.write(f"{provider}: {mask_key(key)}\n")
        return 0

    if subcommand == "set":
        if len(argv) < 3:
            sys.stderr.write("[commitguard] Error: missing arguments. Usage: git auth set <provider> <key>\n")
            return 1
        provider = argv[1].lower()
        key = argv[2].strip()
        path = set_credential(provider, key)
        sys.stdout.write(f"[commitguard] Saved credential for '{provider}' to {path}\n")
        return 0

    if subcommand in ("remove", "delete", "rm"):
        if len(argv) < 2:
            sys.stderr.write("[commitguard] Error: missing provider name. Usage: git auth remove <provider>\n")
            return 1
        provider = argv[1].lower()
        if remove_credential(provider):
            sys.stdout.write(f"[commitguard] Removed credential for '{provider}'.\n")
            return 0
        sys.stderr.write(f"[commitguard] No credential found for '{provider}'.\n")
        return 1

    sys.stderr.write(f"[commitguard] Unknown auth command: '{subcommand}'. Run 'git auth --help' for usage.\n")
    return 1


if __name__ == "__main__":
    sys.exit(handle_auth_command(sys.argv[1:]))
