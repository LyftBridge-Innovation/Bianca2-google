"""
Google Workspace CLI (gws) Python wrapper.

Executes gws commands as subprocesses and returns parsed JSON responses.
Replaces the old google_auth.py + direct Google API client approach.

Authentication:
  Managed entirely by gws.  Run `gws auth login` once (one-time browser
  flow) and gws stores encrypted credentials in ~/.config/gws/.  Token
  refresh is automatic — no manual token management needed.
"""
import subprocess
import json
import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

GWS_CLI_PATH = os.getenv("GWS_CLI_PATH", "gws")


class GWSError(Exception):
    """Raised when a gws CLI command fails."""

    def __init__(self, message: str, exit_code: int = 1):
        self.exit_code = exit_code
        super().__init__(message)


def execute(
    args: list[str],
    *,
    body_json: Optional[dict] = None,
    timeout: int = 30,
    access_token: Optional[str] = None,
) -> Any:
    """
    Run a gws CLI command and return the parsed JSON output.

    When access_token is provided, it is injected via GOOGLE_WORKSPACE_CLI_TOKEN
    for per-user API calls.  When None, gws uses its global stored credentials.

    Args:
        args:         Command parts, e.g. ["gmail", "+send", "--to", "a@b.com"]
        body_json:    If provided, serialised and passed via --json flag.
        timeout:      Subprocess timeout in seconds.
        access_token: Per-user OAuth access token (optional).

    Returns:
        Parsed JSON (dict or list) from stdout.

    Raises:
        GWSError on non-zero exit, timeout, or invalid JSON.
    """
    cmd = [GWS_CLI_PATH] + args

    if body_json is not None:
        cmd += ["--json", json.dumps(body_json)]

    # Inject per-user token when provided
    env = None
    if access_token:
        env = os.environ.copy()
        env["GOOGLE_WORKSPACE_CLI_TOKEN"] = access_token

    logger.debug("gws command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        raise GWSError(
            f"gws CLI not found at '{GWS_CLI_PATH}'. "
            "Install with: npm install -g @googleworkspace/cli"
        )
    except subprocess.TimeoutExpired:
        raise GWSError(f"gws command timed out after {timeout}s")

    if result.returncode != 0:
        # Filter out gws informational lines from stderr
        stderr_lines = [
            line for line in result.stderr.strip().splitlines()
            if not line.startswith("Using keyring backend:")
        ]
        stderr = "\n".join(stderr_lines).strip()
        # gws writes API error details to stdout as JSON, not stderr
        if not stderr and result.stdout.strip():
            try:
                import json as _json
                err_body = _json.loads(result.stdout.strip())
                stderr = err_body.get("error", {}).get("message", "") or str(err_body)
            except Exception:
                stderr = result.stdout.strip()[:200]
        logger.error("gws exit %d: %s", result.returncode, stderr)
        raise GWSError(stderr or f"gws exited with code {result.returncode}",
                       exit_code=result.returncode)

    stdout = result.stdout.strip()
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("gws returned non-JSON: %s", stdout[:300])
        raise GWSError(f"Invalid JSON from gws: {exc}")
