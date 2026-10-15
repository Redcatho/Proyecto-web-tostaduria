from datetime import UTC, datetime

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    roles = db.relationship("Role", secondary=user_roles, lazy="selectin")
    memberships = db.relationship("BusinessMembership", back_populates="user", cascade="all, delete-orphan")

    def has_role(self, *role_codes: str) -> bool:
        return any(role.code in role_codes for role in self.roles)


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(db.Integer, primary_key=True)
    legal_name = db.Column(db.String(180), nullable=True)
    tax_id = db.Column(db.String(32), unique=True, nullable=True, index=True)
    business_type = db.Column(db.String(32), nullable=True)
    contact_name = db.Column(db.String(160), nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    contact_phone = db.Column(db.String(40), nullable=True)
    profile_status = db.Column(db.String(24), nullable=False, default="incomplete")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    memberships = db.relationship("BusinessMembership", back_populates="business", cascade="all, delete-orphan")
    addresses = db.relationship("BusinessAddress", back_populates="business", cascade="all, delete-orphan")


class BusinessMembership(db.Model):
    __tablename__ = "business_memberships"
    __table_args__ = (db.UniqueConstraint("user_id", "business_id", name="uq_business_membership"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    is_owner = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="memberships")
    business = db.relationship("Business", back_populates="memberships")


class BusinessAddress(db.Model):
    __tablename__ = "business_addresses"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(80), nullable=False, default="Principal")
    line1 = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    business = db.relationship("Business", back_populates="addresses")


class CreditApplication(db.Model):
    __tablename__ = "credit_applications"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    requested_days = db.Column(db.Integer, nullable=False)
    requested_limit_usd = db.Column(db.Numeric(12, 2), nullable=False)
    justification = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(24), nullable=False, default="pending")
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    business = db.relationship("Business")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_user_id])


class CreditTerms(db.Model):
    __tablename__ = "credit_terms"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    payment_days = db.Column(db.Integer, nullable=False)
    credit_limit_usd = db.Column(db.Numeric(12, 2), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    business = db.relationship("Business")
    approved_by = db.relationship("User", foreign_keys=[approved_by_user_id])


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    replaced_by_jti = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    line = db.Column(db.String(24), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    coffee_type = db.Column(db.String(120), nullable=True)
    variety = db.Column(db.String(120), nullable=True)
    origin = db.Column(db.String(180), nullable=True)
    sensory_notes = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    availability_mode = db.Column(db.String(24), nullable=False, default="auto")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    variants = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    quality_code = db.Column(db.String(24), nullable=True)
    sale_unit = db.Column(db.String(16), nullable=False)
    inventory_unit = db.Column(db.String(16), nullable=False)
    unit_weight_kg = db.Column(db.Numeric(10, 3), nullable=False)
    packages_per_unit = db.Column(db.Integer, nullable=True)
    price_usd = db.Column(db.Numeric(12, 2), nullable=False)
    low_stock_threshold = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    product = db.relationship("Product", back_populates="variants")
    balances = db.relationship("InventoryBalance", back_populates="variant", cascade="all, delete-orphan")


class InventoryLocation(db.Model):
    __tablename__ = "inventory_locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class InventoryBalance(db.Model):
    __tablename__ = "inventory_balances"
    __table_args__ = (db.UniqueConstraint("variant_id", "location_id", name="uq_inventory_balance"),)

    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    variant = db.relationship("ProductVariant", back_populates="balances")
    location = db.relationship("InventoryLocation")


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"

    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("inventory_locations.id", ondelete="RESTRICT"), nullable=False)
    movement_type = db.Column(db.String(32), nullable=False)
    quantity_delta = db.Column(db.Numeric(12, 3), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    variant = db.relationship("ProductVariant")
    location = db.relationship("InventoryLocation")
    actor = db.relationship("User")


class ExchangeRate(db.Model):
    __tablename__ = "exchange_rates"
    __table_args__ = (db.UniqueConstraint("currency", "effective_date", name="uq_exchange_rate_date"),)

    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(8), nullable=False, default="USD")
    rate_ves = db.Column(db.Numeric(14, 2), nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    retrieved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    source_url = db.Column(db.String(500), nullable=False)
    source_method = db.Column(db.String(16), nullable=False)
    note = db.Column(db.String(500), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = db.relationship("User")


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (db.UniqueConstraint("cart_id", "variant_id", "roast_profile", name="uq_cart_item_configuration"),)

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    roast_profile = db.Column(db.String(24), nullable=True)
    customer_note = db.Column(db.String(1000), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    cart = db.relationship("Cart", back_populates="items")
    variant = db.relationship("ProductVariant")


class Quote(db.Model):
    __tablename__ = "quotes"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="issued")
    delivery_method = db.Column(db.String(24), nullable=False)
    delivery_address_id = db.Column(db.Integer, db.ForeignKey("business_addresses.id", ondelete="SET NULL"), nullable=True)
    payment_condition = db.Column(db.String(32), nullable=False)
    rate_ves = db.Column(db.Numeric(14, 2), nullable=False)
    rate_effective_date = db.Column(db.Date, nullable=False)
    subtotal_usd = db.Column(db.Numeric(14, 2), nullable=False)
    discount_usd = db.Column(db.Numeric(14, 2), nullable=False)
    total_usd = db.Column(db.Numeric(14, 2), nullable=False)
    total_ves = db.Column(db.Numeric(16, 2), nullable=False)
    required_advance_usd = db.Column(db.Numeric(14, 2), nullable=False)
    estimated_dispatch_hours = db.Column(db.Integer, nullable=True)
    estimate_note = db.Column(db.String(500), nullable=True)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    items = db.relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    business = db.relationship("Business")


class QuoteItem(db.Model):
    __tablename__ = "quote_items"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    sku_snapshot = db.Column(db.String(80), nullable=False)
    product_name_snapshot = db.Column(db.String(180), nullable=False)
    line_snapshot = db.Column(db.String(24), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    roast_profile = db.Column(db.String(24), nullable=True)
    customer_note = db.Column(db.String(1000), nullable=True)
    unit_price_usd = db.Column(db.Numeric(12, 2), nullable=False)
    discount_per_unit_usd = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    line_total_usd = db.Column(db.Numeric(14, 2), nullable=False)

    quote = db.relationship("Quote", back_populates="items")


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, unique=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    payment_condition = db.Column(db.String(32), nullable=True)
    total_usd = db.Column(db.Numeric(14, 2), nullable=True)
    total_ves = db.Column(db.Numeric(16, 2), nullable=True)
    rate_ves = db.Column(db.Numeric(14, 2), nullable=True)
    rate_effective_date = db.Column(db.Date, nullable=True)
    required_payment_usd = db.Column(db.Numeric(14, 2), nullable=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    production_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    production_started_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    production_notes = db.Column(db.String(1000), nullable=True)
    return_reason = db.Column(db.String(1000), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    returned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    estimated_dispatch_hours = db.Column(db.Integer, nullable=True)
    estimate_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("PaymentSubmission", back_populates="order", cascade="all, delete-orphan")
    credit_usage = db.relationship("CreditUsage", back_populates="order", uselist=False, cascade="all, delete-orphan")
    dispatch_guide = db.relationship("DispatchGuide", back_populates="order", uselist=False, cascade="all, delete-orphan")
    quote = db.relationship("Quote")
    business = db.relationship("Business")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    quote_item_id = db.Column(db.Integer, db.ForeignKey("quote_items.id", ondelete="SET NULL"), nullable=True)
    sku_snapshot = db.Column(db.String(80), nullable=False)
    product_name_snapshot = db.Column(db.String(180), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    roast_profile = db.Column(db.String(24), nullable=True)
    customer_note = db.Column(db.String(1000), nullable=True)
    unit_price_usd = db.Column(db.Numeric(12, 2), nullable=False)
    discount_per_unit_usd = db.Column(db.Numeric(12, 2), nullable=False)
    line_total_usd = db.Column(db.Numeric(14, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")


class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    note = db.Column(db.String(1000), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class DispatchGuide(db.Model):
    __tablename__ = "dispatch_guides"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    prepared_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    carrier_name = db.Column(db.String(160), nullable=False)
    tracking_number = db.Column(db.String(120), nullable=True)
    dispatch_note = db.Column(db.String(1000), nullable=True)
    dispatched_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivery_confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    order = db.relationship("Order", back_populates="dispatch_guide")


class PaymentSubmission(db.Model):
    __tablename__ = "payment_submissions"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    currency = db.Column(db.String(8), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    amount_usd_equivalent = db.Column(db.Numeric(14, 2), nullable=False)
    reference = db.Column(db.String(120), nullable=False)
    payment_method = db.Column(db.String(40), nullable=False)
    proof_storage_key = db.Column(db.String(512), nullable=False, unique=True)
    proof_original_filename = db.Column(db.String(255), nullable=False)
    proof_content_type = db.Column(db.String(100), nullable=False)
    proof_size_bytes = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(1000), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="submitted", index=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_note = db.Column(db.String(1000), nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", back_populates="payments")


class CreditUsage(db.Model):
    __tablename__ = "credit_usages"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    credit_terms_id = db.Column(db.Integer, db.ForeignKey("credit_terms.id", ondelete="RESTRICT"), nullable=False)
    amount_usd = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    released_at = db.Column(db.DateTime(timezone=True), nullable=True)
    released_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    release_note = db.Column(db.String(1000), nullable=True)

    order = db.relationship("Order", back_populates="credit_usage")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(60), nullable=False)
    entity_id = db.Column(db.String(64), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
