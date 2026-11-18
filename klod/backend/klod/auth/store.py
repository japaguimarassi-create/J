from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


class AuthStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError("psycopg is required for PostgreSQL authentication") from error
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create_session(self, identity: dict[str, str]) -> dict[str, Any]:
        session_token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=14)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM klod_sessions WHERE expires_at <= now()")
                cursor.execute("INSERT INTO klod_platform_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
                cursor.execute("SELECT owner_google_sub FROM klod_platform_state WHERE id = 1 FOR UPDATE")
                state = cursor.fetchone()
                cursor.execute(
                    """
                    INSERT INTO klod_users (id, google_sub, email, display_name, picture_url, role)
                    VALUES (%s, %s, %s, %s, %s, 'user')
                    ON CONFLICT (google_sub) DO UPDATE
                    SET email = EXCLUDED.email,
                        display_name = EXCLUDED.display_name,
                        picture_url = EXCLUDED.picture_url
                    RETURNING id, google_sub, email, display_name, picture_url, role
                    """,
                    (uuid.uuid4(), identity["google_sub"], identity["email"], identity["display_name"], identity["picture"]),
                )
                user = cursor.fetchone()
                owner_sub = state["owner_google_sub"] if state else None
                if owner_sub is None:
                    cursor.execute(
                        "UPDATE klod_platform_state SET owner_google_sub = %s, initialized_at = now() WHERE id = 1 AND owner_google_sub IS NULL",
                        (identity["google_sub"],),
                    )
                    owner_sub = identity["google_sub"]
                role = "admin" if identity["google_sub"] == owner_sub else "user"
                cursor.execute("UPDATE klod_users SET role = %s WHERE id = %s", (role, user["id"]))
                cursor.execute(
                    """
                    INSERT INTO klod_sessions (id, user_id, token_hash, csrf_hash, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (uuid.uuid4(), user["id"], self.digest(session_token), self.digest(csrf_token), expires_at),
                )
        return {
            "session_token": session_token,
            "csrf_token": csrf_token,
            "expires_at": expires_at,
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "display_name": user["display_name"],
                "picture": user["picture_url"],
                "role": role,
            },
        }

    def get_session(self, session_token: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.id, u.google_sub, u.email, u.display_name, u.picture_url, u.role,
                           s.csrf_hash, s.expires_at
                    FROM klod_sessions AS s
                    JOIN klod_users AS u ON u.id = s.user_id
                    WHERE s.token_hash = %s AND s.expires_at > now()
                    """,
                    (self.digest(session_token),),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "google_sub": row["google_sub"],
            "email": row["email"],
            "display_name": row["display_name"],
            "picture": row["picture_url"],
            "role": row["role"],
            "csrf_hash": row["csrf_hash"],
            "expires_at": row["expires_at"],
        }

    def revoke_session(self, session_token: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM klod_sessions WHERE token_hash = %s", (self.digest(session_token),))

    def list_users(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, email, display_name, role, created_at FROM klod_users ORDER BY created_at DESC LIMIT %s",
                    (max(1, min(limit, 200)),),
                )
                rows = cursor.fetchall()
        return [{**row, "id": str(row["id"])} for row in rows]
