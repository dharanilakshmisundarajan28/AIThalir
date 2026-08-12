"""Small, idempotent marketplace seed for fertilizer recommendations.

The marketplace schema has no crop/stage columns, so crop suitability is
recorded in the product description and fertilizer_type.  The visualization
queries the same Product rows used by the existing fertilizer marketplace.
"""
from app import db
from app.models import Product, User, UserRole


CATALOG = (
    ('Urea 46-0-0', 'Urea · NPK 46:0:0', 290.0, 'Nitrogen source for vegetative growth; suitable for cereals, fruit crops and vegetables.'),
    ('DAP 18-46-0', 'DAP · NPK 18:46:0', 1350.0, 'Phosphorus-rich basal and early root-development fertilizer for all crop groups.'),
    ('NPK 10-26-26', 'NPK · 10:26:26', 1480.0, 'Balanced phosphorus and potassium fertilizer for flowering and fruit development.'),
    ('MOP 0-0-60', 'MOP · NPK 0:0:60', 820.0, 'Potassium source for fruit development, quality and stress tolerance.'),
)


def ensure_fertilizer_catalog():
    """Create only absent marketplace records; never overwrite supplier data."""
    supplier = User.query.filter_by(role=UserRole.SUPPLIER).first()
    if not supplier:
        supplier = User(username='aithalir_fertilizer_supply', email='supply@aithalir.local', role=UserRole.SUPPLIER,
                        company_name='AIThalir Fertilizer Supply', is_verified=True)
        supplier.set_password('seed-only-account-not-for-login')
        db.session.add(supplier)
        db.session.flush()
    created = 0
    for name, fertilizer_type, price, description in CATALOG:
        if not Product.query.filter_by(name=name, is_fertilizer=True).first():
            db.session.add(Product(name=name, fertilizer_type=fertilizer_type, description=description,
                                   price=price, quantity=500, unit='50 kg bag', category='fertilizer',
                                   seller_id=supplier.id, is_fertilizer=True, is_available=True))
            created += 1
    if created:
        db.session.commit()
