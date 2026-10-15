import os

import click
from flask import Flask

from app.extensions import db
from app.models import User
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

    @app.cli.command("sync-bcv-rate")
    def sync_bcv_rate() -> None:
        """Fetch and save the current USD/VES rate from the configured BCV source."""
        try:
            rate = sync_official_bcv_rate()
        except BcvRateError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Saved BCV rate {rate.rate_ves} VES for {rate.effective_date.isoformat()}.")
