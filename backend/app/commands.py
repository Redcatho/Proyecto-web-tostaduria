import os
from datetime import date
from decimal import Decimal

import click
from flask import Flask

from app.extensions import db
from app.models import ExchangeRate, InventoryBalance, InventoryLocation, Product, ProductVariant, User
from app.security import audit, get_role, hash_password
from app.services.bcv import BcvRateError, sync_official_bcv_rate


def register_commands(app: Flask) -> None:
    @app.cli.command("create-initial-admins")
    def create_initial_admins() -> None:
        """Create or grant administrator access to the two initial accounts."""
        configurations = []
        for number in (1, 2):
            email = os.getenv(f"ADMIN_{number}_EMAIL", "").strip().lower()
            password = os.getenv(f"ADMIN_{number}_PASSWORD", "")
            name = os.getenv(f"ADMIN_{number}_NAME", f"Administrador {number}").strip()
            if not email or "@" not in email or len(password) < 6:
                raise click.ClickException(
                    f"ADMIN_{number}_EMAIL and ADMIN_{number}_PASSWORD (minimum 6 characters) are required."
                )
            configurations.append((email, password, name))

        admin_role = get_role("admin")
        for email, password, name in configurations:
            user = db.session.scalar(db.select(User).where(User.email == email))
            if user is None:
                user = User(email=email, full_name=name, password_hash=hash_password(password), roles=[admin_role])
                db.session.add(user)
                db.session.flush()
                audit(user.id, "admin.initial_account_created", "user", user.id)
                click.echo(f"Created administrator account for {email}.")
            elif not user.has_role("admin"):
                user.roles.append(admin_role)
                audit(user.id, "admin.initial_role_granted", "user", user.id)
                click.echo(f"Granted administrator access to {email}.")
            else:
                click.echo(f"Administrator account already exists for {email}.")
        db.session.commit()

    @app.cli.command("seed-initial-data")
    def seed_initial_data() -> None:
        """Seed the database with initial products, variants and a default inventory location."""
        if db.session.scalar(db.select(db.func.count()).select_from(Product)) > 0:
            click.echo("Products already exist. Skipping seed.")
            return

        loc = db.session.scalar(db.select(InventoryLocation).where(InventoryLocation.name == "Almacén principal"))
        if loc is None:
            loc = InventoryLocation(name="Almacén principal", is_active=True)
            db.session.add(loc)
            db.session.flush()

        products = [
            {"slug": "cafe-filtrado", "line": "commercial", "name": "Café Filtrado 250g", "description": "Café de especialidad en grano, ideal para filtrado. Notas cítricas y chocolate.", "coffee_type": "Arábica", "origin": "Venezuela - Mérida", "variants": [{"sku": "FIL-001", "name": "Bolsa 250g", "sale_unit": "bulto", "inventory_unit": "kg", "unit_weight_kg": "0.250", "packages_per_unit": 40, "price_usd": "150.00", "low_stock_threshold": "10", "stock": "40"}]},
            {"slug": "cafe-espresso", "line": "commercial", "name": "Café Espresso 500g", "description": "Mezcla equilibrada para espresso. Cuerpo medio, aroma intenso.", "coffee_type": "Arábica 80% / Robusta 20%", "origin": "Venezuela - Táchira", "variants": [{"sku": "ESP-001", "name": "Bolsa 500g", "sale_unit": "bulto", "inventory_unit": "kg", "unit_weight_kg": "0.500", "packages_per_unit": 20, "price_usd": "220.00", "low_stock_threshold": "10", "stock": "30"}]},
            {"slug": "cafe-premium", "line": "commercial", "name": "Café Premium 250g", "description": "Café de origen único, variedad bourbon. Notas florales y miel.", "coffee_type": "Bourbon", "origin": "Venezuela - Aragua", "variants": [{"sku": "PRM-001", "name": "Bolsa 250g", "sale_unit": "bulto", "inventory_unit": "kg", "unit_weight_kg": "0.250", "packages_per_unit": 40, "price_usd": "180.00", "low_stock_threshold": "5", "stock": "25"}]},
            {"slug": "cafe-grano-especial", "line": "cafeteria", "name": "Café Especial en Grano", "description": "Café de especialidad en grano entero. Para cafeterías que buscan calidad superior.", "coffee_type": "Arábica", "origin": "Venezuela - Mérida", "variants": [{"sku": "GRA-001", "name": "Saco 5 kg", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": "5.000", "price_usd": "80.00", "low_stock_threshold": "10", "stock": "20"}]},
            {"slug": "cafe-grano-premium", "line": "cafeteria", "name": "Café Premium Mezcla Casa", "description": "Nuestra mezcla insignia. Cuerpo completo, acidez equilibrada y final dulce.", "coffee_type": "Arábica", "origin": "Venezuela", "variants": [{"sku": "PRE-001", "name": "Saco 5 kg", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": "5.000", "price_usd": "90.00", "low_stock_threshold": "10", "stock": "15"}]},
            {"slug": "cafe-organico", "line": "cafeteria", "name": "Café Orgánico de Finca", "description": "Proveniente de fincas certificadas. Notas frutales y chocolate amargo.", "coffee_type": "Arábica Orgánico", "origin": "Venezuela - Monagas", "variants": [{"sku": "ORG-001", "name": "Saco 5 kg", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": "5.000", "price_usd": "105.00", "low_stock_threshold": "10", "stock": "12"}]},
        ]

        for data in products:
            variants_data = data.pop("variants", [])
            product = Product(**data)
            db.session.add(product)
            db.session.flush()
            for vdata in variants_data:
                initial_stock = Decimal(vdata.pop("stock", "0"))
                variant = ProductVariant(product_id=product.id, **vdata)
                db.session.add(variant)
                db.session.flush()
                if initial_stock > 0 and loc:
                    balance = InventoryBalance(variant_id=variant.id, location_id=loc.id, quantity=initial_stock)
                    db.session.add(balance)
            click.echo(f"  \u2713 {product.name} ({product.line})")

        rate = db.session.scalar(db.select(ExchangeRate).where(ExchangeRate.currency == "USD", ExchangeRate.effective_date == date.today()))
        if rate is None:
            rate = ExchangeRate(currency="USD", rate_ves="50.00", effective_date=date.today(), source_url="seed://initial", source_method="seed")
            db.session.add(rate)
            click.echo("  \u2713 Tasa BCV inicial: 50.00 VES")

        db.session.commit()
        click.echo("Seed completado. 6 productos creados.")

    @app.cli.command("fix-prices")
    def fix_prices() -> None:
        """Fix product prices and remove 15 kg variants in existing database."""
        from app.models import Product, ProductVariant, InventoryBalance

        price_fixes = {
            "cafe-filtrado": "150.00",
            "cafe-espresso": "220.00",
            "cafe-premium": "180.00",
            "cafe-grano-especial": "80.00",
            "cafe-grano-premium": "90.00",
            "cafe-organico": "105.00",
        }
        remove_skus = {"GRA-002", "PRE-002", "ORG-002"}

        for slug, price in price_fixes.items():
            product = db.session.scalar(db.select(Product).where(Product.slug == slug))
            if product is None:
                click.echo(f"  Producto '{slug}' no encontrado.")
                continue
            for variant in list(product.variants):
                if variant.sku in remove_skus:
                    for bal in list(variant.balances):
                        db.session.delete(bal)
                    db.session.delete(variant)
                    click.echo(f"  Eliminada variante {variant.sku}")
                else:
                    variant.price_usd = Decimal(price)
                    click.echo(f"  Actualizado {variant.sku}: USD ${price}")
        db.session.commit()
        click.echo("Precios actualizados y variantes de 15kg eliminadas.")

    @app.cli.command("sync-bcv-rate")
    def sync_bcv_rate() -> None:
        """Fetch and save the current USD/VES rate from the configured BCV source."""
        try:
            rate = sync_official_bcv_rate()
        except BcvRateError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Saved BCV rate {rate.rate_ves} VES for {rate.effective_date.isoformat()}.")