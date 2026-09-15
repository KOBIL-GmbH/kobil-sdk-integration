"""Local stdio MCP. No backend credentials or remote provider actions."""
import hashlib
import os
from pathlib import Path
import stat

from mcp.server.fastmcp import FastMCP
from .planner import FRAMEWORKS, plan

mcp = FastMCP("KOBILSDK")


@mcp.tool()
def sdk_targets() -> dict:
    """List required integration targets; no native runtime coverage is claimed."""
    return {"frameworks": {k: sorted(v) for k, v in FRAMEWORKS.items()},
            "feature_scope": "All public KOBIL SDK features, subject to version/platform support",
            "runtime_verification": "pending"}


@mcp.tool()
def sdk_plan(profile: dict, capabilities: list[str] | None = None) -> dict:
    """Plan dependencies and optional provider offers. Never installs or contacts providers.

    Profile fields: framework, targets, backend, artifact_source; optional provider
    lists: distribution, observability, diagnostics, testing, infrastructure,
    documentation, issue_tracking. No credentials. Required adapters are pending.
    """
    return plan(profile, capabilities if capabilities is not None else [])


@mcp.tool()
def sdk_artifact_info(path: str) -> dict:
    """Hash a separately supplied SDK binary/archive; return metadata, never contents.

    Supported file suffixes: aar, jar, dll, dylib, so, zip, tar, gz, tgz.
    Framework directories must first be packaged as an archive. This does not
    verify authenticity, architecture, version compatibility or license rights.
    """
    source = Path(path).expanduser()
    if source.suffix.lower() not in {".aar", ".jar", ".dll", ".dylib", ".so", ".zip", ".tar", ".gz", ".tgz"}:
        raise ValueError("Expected a supported SDK binary/archive file")
    try:
        # Opening non-blocking avoids hangs on a FIFO disguised as an artifact.
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("Expected a regular file")
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("Artifact changed during inspection")
    except OSError:
        raise ValueError("Cannot read the SDK artifact") from None
    return {"path": str(source.absolute()), "bytes": after.st_size,
            "sha256": digest.hexdigest(), "compatibility_verified": False}


def main():
    mcp.run()
