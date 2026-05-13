"""Product routes: batch-add link, lihat status, hapus."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, ProductStatus
from app.scheduler import enqueue_scrape
from app.scrapers import detect_source

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return templates.TemplateResponse(
        "index.html", {"request": request, "products": products}
    )


@router.post("/products")
def add_products(urls: str = Form(...), db: Session = Depends(get_db)):
    """Batch-add: textarea berisi satu URL per baris."""
    added = 0
    for line in urls.splitlines():
        url = line.strip()
        if not url:
            continue
        source = detect_source(url)
        if not source:
            continue
        product = Product(url=url, source=source, status=ProductStatus.pending)
        db.add(product)
        db.commit()
        db.refresh(product)
        enqueue_scrape(product.id)
        added += 1
    return RedirectResponse(url=f"/?added={added}", status_code=303)


@router.post("/products/{product_id}/delete")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/", status_code=303)
