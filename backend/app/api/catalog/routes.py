from flask import Blueprint, jsonify

from app.extensions import db
from app.models import ExchangeRate, Product
from app.services.catalog import current_exchange_rate, product_payload

catalog_blueprint = Blueprint("catalog", __name__)


def rate_payload(rate: ExchangeRate | None) -> dict | None:
    if rate is None:
        return None
    return {"currency": rate.currency, "rate_ves": str(rate.rate_ves), "effective_date": rate.effective_date.isoformat(), "source": "BCV"}


@catalog_blueprint.get("/products")
def list_products():
    rate = current_exchange_rate()
    products = db.session.scalars(db.select(Product).where(Product.is_active.is_(True)).order_by(Product.line, Product.id)).all()
    return jsonify(products=[product_payload(product, rate=rate) for product in products], exchange_rate=rate_payload(rate))


@catalog_blueprint.get("/products/<string:slug>")
def product_detail(slug: str):
    product = db.session.scalar(db.select(Product).where(Product.slug == slug, Product.is_active.is_(True)))
    if product is None:
        return jsonify(error={"code": "not_found", "message": "Product not found."}), 404
    rate = current_exchange_rate()
    return jsonify(product=product_payload(product, rate=rate), exchange_rate=rate_payload(rate))


@catalog_blueprint.get("/exchange-rates/current")
def current_rate():
    return jsonify(exchange_rate=rate_payload(current_exchange_rate()))
