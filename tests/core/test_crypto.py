import pytest

from mediafactory.core.crypto import SecretDecryptError, decrypt, encrypt

KEY_A = "a" * 40
KEY_B = "b" * 40


def test_roundtrip():
    token = encrypt("sk-abc", key=KEY_A)
    assert token != "sk-abc"
    assert decrypt(token, key=KEY_A) == "sk-abc"


def test_wrong_key_raises():
    token = encrypt("sk-abc", key=KEY_A)
    with pytest.raises(SecretDecryptError):
        decrypt(token, key=KEY_B)


def test_garbage_raises():
    with pytest.raises(SecretDecryptError):
        decrypt("not-a-token", key=KEY_A)
