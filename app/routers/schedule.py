"""Schedule routes: bikin batch schedule & lihat daftar."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Platform, PostStatus, Product, ProductStatus, ScheduledPost
from app.scheduler import enqueue_publish

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
    scheduled_at: str = Form(...),
    caption: str = Form(""),
    db: Session = Depends(get_db),
):
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
            enqueue_publish(sp.id, run_at)
            created += 1
    return RedirectResponse(url=f"/schedule?created={created}", status_code=303)
