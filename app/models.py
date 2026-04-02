from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


class UserRole(Enum):
    FARMER = "farmer"
    CONSUMER = "consumer"
    SUPPLIER = "supplier"
    ADMIN = "admin"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.CONSUMER, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    profile_pic = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    farm_name = db.Column(db.String(100))
    farm_size = db.Column(db.Float)
    gst_number = db.Column(db.String(50))
    company_name = db.Column(db.String(100))
    preferred_categories = db.Column(db.String(200))

    products = db.relationship("Product", backref="seller", lazy=True, foreign_keys="Product.seller_id")
    orders = db.relationship("Order", backref="buyer", lazy=True, foreign_keys="Order.buyer_id")
    cart_items = db.relationship("CartItem", backref="user", lazy=True)
    crop_recommendations = db.relationship("CropRecommendation", backref="farmer", lazy=True)
    fertilizer_orders = db.relationship("FertilizerOrder", backref="supplier", lazy=True)
    scheme_applications = db.relationship("SchemeApplication", backref="user", lazy=True)
    chat_history = db.relationship("ChatHistory", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_role_display(self):
        return self.role.value.capitalize()

    def get_dashboard_url(self):
        if self.role == UserRole.FARMER:
            return "/farmer/dashboard"
        if self.role == UserRole.CONSUMER:
            return "/consumer/dashboard"
        if self.role == UserRole.SUPPLIER:
            return "/supplier/dashboard"
        if self.role == UserRole.ADMIN:
            return "/admin/dashboard"
        return "/"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), default="kg")
    category = db.Column(db.String(50), index=True)
    image_url = db.Column(db.String(255))
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_fertilizer = db.Column(db.Boolean, default=False, index=True)
    fertilizer_type = db.Column(db.String(100))
    is_available = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    cart_items = db.relationship("CartItem", backref="product", lazy=True, cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", backref="product", lazy=True)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(50), default="cod")
    shipping_address = db.Column(db.Text)
    status = db.Column(db.String(30), default="pending", index=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False, default=0.0)


class CropRecommendation(db.Model):
    __tablename__ = "crop_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    recommended_crop = db.Column(db.String(100), nullable=False)
    confidence_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class MandiPrice(db.Model):
    __tablename__ = "mandi_prices"

    id = db.Column(db.Integer, primary_key=True)
    commodity = db.Column(db.String(100), nullable=False, index=True)
    market = db.Column(db.String(100))
    min_price = db.Column(db.Float, default=0.0)
    max_price = db.Column(db.Float, default=0.0)
    modal_price = db.Column(db.Float, default=0.0)
    price_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class ChatHistory(db.Model):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class GovernmentScheme(db.Model):
    __tablename__ = "government_schemes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    scheme_type = db.Column(db.String(50), nullable=False, index=True)
    eligibility = db.Column(db.Text)
    benefits = db.Column(db.Text)
    official_url = db.Column(db.String(255), nullable=False)
    deadline = db.Column(db.DateTime, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship("SchemeApplication", backref="scheme", lazy=True, cascade="all, delete-orphan")


class SchemeApplication(db.Model):
    __tablename__ = "scheme_applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey("government_schemes.id"), nullable=False, index=True)
    status = db.Column(db.String(30), default="pending", index=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class FertilizerOrder(db.Model):
    __tablename__ = "fertilizer_orders"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_name = db.Column(db.String(120))
    quantity = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
