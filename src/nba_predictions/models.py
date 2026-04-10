from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    score: Mapped[int] = mapped_column(Integer, default=0)

    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction", back_populates="user"
    )
    comments: Mapped[list[Comment]] = relationship("Comment", back_populates="user")
    sent_messages: Mapped[list[Message]] = relationship(
        "Message", foreign_keys="Message.from_user_id", back_populates="sender"
    )
    received_messages: Mapped[list[Message]] = relationship(
        "Message", foreign_keys="Message.to_user_id", back_populates="recipient"
    )

    @property
    def password(self):
        raise AttributeError("password not readable")

    @password.setter
    def password(self, password: str) -> None:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        self.password_hash = ph.hash(password)

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        # Transparent re-hash: legacy werkzeug PBKDF2 → argon2
        if self.password_hash.startswith("pbkdf2:"):
            from werkzeug.security import check_password_hash
            if check_password_hash(self.password_hash, password):
                self.password = password
                db.session.commit()
                return True
            return False
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError
        ph = PasswordHasher()
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False

    @property
    def total(self) -> int:
        return sum(p.score_made or 0 for p in self.predictions)

    def __repr__(self) -> str:
        return self.username


class Series(db.Model):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    home: Mapped[str] = mapped_column(Text)
    away: Mapped[str] = mapped_column(Text)
    open: Mapped[bool] = mapped_column(Boolean, default=True)
    result: Mapped[Optional[str]] = mapped_column(String)
    is_playin: Mapped[bool] = mapped_column(Boolean, default=False)

    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction", back_populates="series"
    )

    def __repr__(self) -> str:
        return f"Series {self.home} - {self.away}"


class Prediction(db.Model):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("series_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    predicted: Mapped[Optional[str]] = mapped_column(String)
    score_made: Mapped[int] = mapped_column(Integer, default=0)

    series: Mapped[Series] = relationship("Series", back_populates="predictions")
    user: Mapped[User] = relationship("User", back_populates="predictions")

    def __repr__(self) -> str:
        return f"Prediction {self.series} → {self.user}: {self.predicted}"


class Comment(db.Model):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        return f"Comment from {self.user.username}"


class AdminLog(db.Model):
    __tablename__ = "admin_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    who: Mapped[str] = mapped_column(String(64))
    when: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    action: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[Optional[int]] = mapped_column(Integer)
    before: Mapped[Optional[str]] = mapped_column(Text)
    after: Mapped[Optional[str]] = mapped_column(Text)


class Message(db.Model):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    sender: Mapped[User] = relationship(
        "User", foreign_keys=[from_user_id], back_populates="sent_messages"
    )
    recipient: Mapped[User] = relationship(
        "User", foreign_keys=[to_user_id], back_populates="received_messages"
    )
