from __future__ import annotations

import unittest
from unittest.mock import patch

from emergent_specialization.credentials import CredentialError, CredentialStore


class SafeFakeKeyring:
    __module__ = "keyring.backends.macOS"


class UnsafeFakeKeyring:
    __module__ = "keyring.backends.fail"


class CredentialTests(unittest.TestCase):
    def test_unsafe_backend_is_rejected_without_reading_secret(self) -> None:
        with patch("emergent_specialization.credentials.keyring.get_keyring", return_value=UnsafeFakeKeyring()):
            with self.assertRaises(CredentialError):
                CredentialStore().get()

    def test_keychain_status_and_get_never_return_secret_in_status(self) -> None:
        with patch("emergent_specialization.credentials.keyring.get_keyring", return_value=SafeFakeKeyring()), patch(
            "emergent_specialization.credentials.keyring.get_password", return_value="secret-value"
        ):
            store = CredentialStore()
            self.assertEqual(store.get(), "secret-value")
            status = store.status()
            self.assertEqual(status["status"], "configured")
            self.assertNotIn("secret-value", repr(status))

    def test_explicit_env_source_does_not_fallback_to_keychain(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(Exception):
                CredentialStore().get(source="env")
