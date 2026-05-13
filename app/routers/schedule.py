"""Schedule routes: bikin batch schedule, post-now, retry, lihat log."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Platform,
    PostLog,
    PostStatus,
    Product,
    ProductStatus,
    ScheduledPost,
)
from app.scheduler import enqueue_publish, enqueue_publish_now

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/schedule")
def schedule_form(request: Request, db: Session = Depends(get_db)):
    ready = (
        db.query(Product)
        .filter(Product.status == ProductStatus.ready)
        .order_by(Product.created_at.desc())
        .all()
    )
    scheduled = (
        db.query(ScheduledPost)
        .order_by(ScheduledPost.scheduled_at.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(
        "schedule.html",
        {"request": request, "products": ready, "scheduled": scheduled},
    )


@router.post("/schedule")
def schedule_create(
    product_ids: list[int] = Form(...),
    platforms: list[str] = Form(...),
    scheduled_at: str = Form(""),
    post_now: str = Form(""),
    caption: str = Form(""),
    db: Session = Depends(get_db),
):
    """Buat jadwal. Kalau `post_now=1`, abaikan `scheduled_at` dan post segera."""
    immediate = bool(post_now)
    if immediate:
        run_at = datetime.utcnow()
    else:
        if not scheduled_at:
            raise HTTPException(400, "scheduled_at wajib jika bukan post now")
        run_at = datetime.fromisoformat(scheduled_at)

    chosen = [Platform(p) for p in platforms]
    created = 0
    for pid in product_ids:
        product = db.get(Product, pid)
        if not product or product.status != ProductStatus.ready:
            continue
        for plat in chosen:
            sp = ScheduledPost(
                product_id=product.id,
                platform=plat,
                caption=caption or None,
                scheduled_at=run_at,
                status=PostStatus.scheduled,
            )
            db.add(sp)
            db.commit()
            db.refresh(sp)
            if immediate:
                enqueue_publish_now(sp.id)
            else:
                enqueue_publish(sp.id, run_at)
            created += 1
    return RedirectResponse(
        url=f"/schedule?created={created}&now={int(immediate)}", status_code=303
    )


@router.post("/schedule/{sp_id}/retry")
def retry_scheduled_post(sp_id: int, db: Session = Depends(get_db)):
    """Re-run scheduled post yang failed, segera."""
    sp = db.get(ScheduledPost, sp_id)
    if not sp:
        raise HTTPException(404, "ScheduledPost not found")
    if sp.status != PostStatus.failed:
        raise HTTPException(
            400, f"Hanya bisa retry yang failed (status sekarang: {sp.status.value})"
        )
    sp.status = PostStatus.scheduled
    sp.scheduled_at = datetime.utcnow()
    db.commit()
    enqueue_publish_now(sp.id)
    return RedirectResponse(url=f"/schedule/{sp_id}", status_code=303)


@router.post("/schedule/{sp_id}/delete")
def delete_scheduled_post(sp_id: int, db: Session = Depends(get_db)):
    sp = db.get(ScheduledPost, sp_id)
    if sp:
        db.delete(sp)
        db.commit()
    return RedirectResponse(url="/schedule", status_code=303)


@router.get("/schedule/{sp_id}")
def schedule_detail(sp_id: int, request: Request, db: Session = Depends(get_db)):
    sp = db.get(ScheduledPost, sp_id)
    if not sp:
        raise HTTPException(404, "ScheduledPost not found")
    logs = (
        db.query(PostLog)
        .filter(PostLog.scheduled_post_id == sp_id)
        .order_by(PostLog.attempted_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "schedule_detail.html",
        {"request": request, "sp": sp, "logs": logs},
    )
