"""Unit tests for authentication module."""

import pytest
from whodis.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_password_hashing_roundtrip(self):
        """Test that passwords can be hashed and verified."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")
        
        assert hash1 != hash2


class TestJWTToken:
    """Test JWT token functions."""

    def test_create_and_decode_token(self):
        """Test token creation and decoding."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        decoded = decode_token("invalid.token.here")
        
        assert decoded is None


class TestAPIKey:
    """Test API key functions."""

    def test_generate_api_key_format(self):
        """Test API key generation format."""
        key = generate_api_key()
        
        assert key.startswith("whodis_")
        assert len(key) > 20

    def test_api_key_hashing(self):
        """Test API key hashing and verification."""
        key = generate_api_key()
        key_hash = hash_api_key(key)
        
        assert verify_api_key(key, key_hash) is True
        assert verify_api_key("wrongkey", key_hash) is False

    def test_different_keys_different_hashes(self):
        """Test that different API keys produce different hashes."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)
        
        assert hash1 != hash2
        assert verify_api_key(key1, hash2) is False
