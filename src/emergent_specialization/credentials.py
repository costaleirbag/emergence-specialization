"""Explicit, non-plaintext credential management for the direct backend.

The default local source is the macOS Keychain through ``keyring``.  Environment
variables are supported only when explicitly selected in configuration; there
is no silent fallback between sources.
"""

from __future__ import annotations

import argparse
import getpass
import os
import platform
from dataclasses import dataclass
from typing import Any, Iterable

import keyring


DEFAULT_SERVICE = "emergence-specialization.deepseek"
DEFAULT_ACCOUNT = "api"


class CredentialError(RuntimeError):
    """A safe, secret-free credential error."""


class CredentialMissing(CredentialError):
    pass


def keyring_backend_info(backend: Any | None = None) -> dict[str, str]:
    selected = backend if backend is not None else keyring.get_keyring()
    backend_type = type(selected)
    return {"name": backend_type.__name__, "module": backend_type.__module__}


def _is_safe_backend(backend: Any) -> bool:
    info = keyring_backend_info(backend)
    module = info["module"].lower()
    name = info["name"].lower()
    unsafe_markers = ("plaintext", "fail", "null", "chainer")
    if any(marker in module or marker in name for marker in unsafe_markers):
        return False
    if platform.system() == "Darwin":
        return any(marker in module or marker in name for marker in ("macos", "os_x", "keychain"))
    return any(marker in module for marker in ("secretservice", "libsecret", "macos", "os_x", "keychain"))


def require_safe_keyring(backend: Any | None = None) -> dict[str, str]:
    selected = backend if backend is not None else keyring.get_keyring()
    info = keyring_backend_info(selected)
    if not _is_safe_backend(selected):
        raise CredentialError(
            f"Refusing credential storage with unsafe keyring backend {info['module']}.{info['name']}"
        )
    return info


@dataclass(frozen=True)
class CredentialStore:
    service: str = DEFAULT_SERVICE
    account: str = DEFAULT_ACCOUNT

    def backend_info(self) -> dict[str, str]:
        return require_safe_keyring()

    def get(self, *, source: str = "keychain") -> str:
        if source == "env":
            value = os.environ.get("DEEPSEEK_API_KEY")
            if not value:
                raise CredentialMissing("DEEPSEEK_API_KEY is not configured for explicit env credential source")
            return value
        if source != "keychain":
            raise CredentialError(f"Unsupported credential source: {source}")
        self.backend_info()
        try:
            value = keyring.get_password(self.service, self.account)
        except Exception as exc:  # pragma: no cover - backend-specific boundary
            raise CredentialError("Unable to read the configured secure credential store") from exc
        if not value:
            raise CredentialMissing("DeepSeek credential is missing from the configured Keychain entry")
        return value

    def status(self) -> dict[str, str]:
        info = self.backend_info()
        try:
            configured = bool(keyring.get_password(self.service, self.account))
        except Exception as exc:  # pragma: no cover - backend-specific boundary
            raise CredentialError("Unable to inspect the configured secure credential store") from exc
        return {"status": "configured" if configured else "missing", **info}

    def store_interactively(self) -> dict[str, str]:
        info = self.backend_info()
        value = getpass.getpass("DeepSeek API key (hidden): ")
        if not value:
            raise CredentialError("Refusing to store an empty credential")
        try:
            keyring.set_password(self.service, self.account, value)
        except Exception as exc:  # pragma: no cover - backend-specific boundary
            raise CredentialError("Unable to store the credential in the secure store") from exc
        return {"status": "configured", **info}

    def delete_interactively(self) -> dict[str, str]:
        info = self.backend_info()
        confirmation = input("Type DELETE to remove the DeepSeek credential: ")
        if confirmation != "DELETE":
            return {"status": "unchanged", **info}
        try:
            was_configured = bool(keyring.get_password(self.service, self.account))
        except Exception as exc:  # pragma: no cover - backend-specific boundary
            raise CredentialError("Unable to inspect the credential before deletion") from exc
        try:
            keyring.delete_password(self.service, self.account)
        except keyring.errors.PasswordDeleteError:
            was_configured = False
        except Exception as exc:  # pragma: no cover - backend-specific boundary
            raise CredentialError("Unable to delete the credential from the secure store") from exc
        return {"status": "deleted" if was_configured else "missing", **info}


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Manage the DeepSeek credential in macOS Keychain")
    parser.add_argument("action", choices=("status", "store", "delete"))
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    store = CredentialStore(args.service, args.account)
    try:
        result = {
            "status": store.status,
            "store": store.store_interactively,
            "delete": store.delete_interactively,
        }[args.action]()
    except CredentialError as exc:
        parser.error(str(exc))
    print(" ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
