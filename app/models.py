"""ORM models: Product, ScheduledPost, PostLog."""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(str, PyEnum):
    shopee = "shopee"
    tiktok = "tiktok"


class ProductStatus(str, PyEnum):
    pending = "pending"    # baru masuk, belum discrape
    ready = "ready"        # scrape sukses, metadata lengkap
    failed = "failed"      # scrape gagal


class Platform(str, PyEnum):
    threads = "threads"
    twitter = "twitter"


class PostStatus(str, PyEnum):
    scheduled = "scheduled"
    posted = "posted"
    failed = "failed"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[Source] = mapped_column(Enum(Source), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[str | None] = mapped_column(String(64))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.pending
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.scheduled
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="scheduled_posts")
    logs: Mapped[list["PostLog"]] = relationship(
        back_populates="scheduled_post", cascade="all, delete-orphan"
    )


class PostLog(Base):
    __tablename__ = "post_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheduled_post_id: Mapped[int] = mapped_column(ForeignKey("scheduled_posts.id"))
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(default=False)
    remote_post_id: Mapped[str | None] = mapped_column(String(128))
    message: Mapped[str | None] = mapped_column(Text)

    scheduled_post: Mapped[ScheduledPost] = relationship(back_populates="logs")
