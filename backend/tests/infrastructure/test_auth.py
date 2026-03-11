import pytest

from textbook_agent.infrastructure.auth.jwt_handler import JWTHandler


class TestJWTHandler:
    def setup_method(self):
        self.handler = JWTHandler(
            secret_key="test-secret-key-for-unit-tests",
            algorithm="HS256",
            expire_minutes=60,
        )

    def test_create_and_decode_token(self):
        token = self.handler.create_access_token("user-123", "test@example.com")
        payload = self.handler.decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_invalid_token_raises(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            self.handler.decode_token("invalid.jwt.token")

    def test_wrong_secret_raises(self):
        from jose import JWTError

        token = self.handler.create_access_token("user-123", "test@example.com")
        other_handler = JWTHandler(
            secret_key="different-secret", algorithm="HS256", expire_minutes=60
        )
        with pytest.raises(JWTError):
            other_handler.decode_token(token)

    def test_token_contains_expiry(self):
        token = self.handler.create_access_token("user-123", "test@example.com")
        payload = self.handler.decode_token(token)
        assert isinstance(payload["exp"], int)
