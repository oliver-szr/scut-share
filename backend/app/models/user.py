from datetime import UTC, datetime

from sqlalchemy import Boolean, Enum, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import Campus
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("student_no", name="uq_users_student_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    is_admin: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="0")
    nickname: Mapped[str] = mapped_column(String(30))
    student_no: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(512))
    campus: Mapped[Campus] = mapped_column(Enum(
        Campus, values_callable=lambda enum: [item.value for item in enum],
        native_enum=False, create_constraint=True, name="user_campus",
    ))
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), onupdate=lambda: datetime.now(UTC),
    )
