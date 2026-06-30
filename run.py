from app import create_app, db
from app.models import User, UserRole, GovernmentScheme, Product
from app.schemes.defaults import get_default_schemes

app = create_app()

def init_database():
    """Initialize database with all role accounts and sample data"""
    with app.app_context():
        db.create_all()
        
        # Create Admin User
        admin = User.query.filter_by(email='admin@agriplatform.com').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@agriplatform.com',
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
        
        # Create Sample Farmer
        farmer = User.query.filter_by(email='farmer@example.com').first()
        if not farmer:
            farmer = User(
                username='ramesh_farmer',
                email='farmer@example.com',
                role=UserRole.FARMER,
                phone='9876543210',
                address='Village Pimpla, Maharashtra',
                farm_name='Ramesh Organic Farm',
                farm_size=5.5,
                is_active=True,
                is_verified=True
            )
            farmer.set_password('Farmer@123')
            db.session.add(farmer)
        
        # Create Sample Consumer
        consumer = User.query.filter_by(email='consumer@example.com').first()
        if not consumer:
            consumer = User(
                username='priya_consumer',
                email='consumer@example.com',
                role=UserRole.CONSUMER,
                phone='9876543211',
                address='Mumbai, Maharashtra',
                preferred_categories='vegetables,fruits',
                is_active=True,
                is_verified=True
            )
            consumer.set_password('Consumer@123')
            db.session.add(consumer)
        
        # Create Sample Supplier
        supplier = User.query.filter_by(email='supplier@example.com').first()
        if not supplier:
            supplier = User(
                username='kisan_fertilizers',
                email='supplier@example.com',
                role=UserRole.SUPPLIER,
                phone='9876543212',
                address='Pune, Maharashtra',
                company_name='Kisan Fertilizers Pvt Ltd',
                gst_number='27AAAAA1234A1Z',
                is_active=True,
                is_verified=True
            )
            supplier.set_password('Supplier@123')
            db.session.add(supplier)

        db.session.flush()

        sample_products = [
            {
                'name': 'Farm Fresh Tomatoes',
                'description': 'Ripe red tomatoes harvested from local farms.',
                'price': 38,
                'quantity': 120,
                'unit': 'kg',
                'category': 'vegetables',
                'image_url': 'https://images.unsplash.com/photo-1546470427-e26264be0b0d?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Organic Carrots',
                'description': 'Crunchy carrots grown with natural farming practices.',
                'price': 55,
                'quantity': 90,
                'unit': 'kg',
                'category': 'vegetables',
                'image_url': 'https://images.unsplash.com/photo-1447175008436-054170c2e979?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Green Spinach Bunch',
                'description': 'Tender spinach leaves packed fresh for daily cooking.',
                'price': 25,
                'quantity': 80,
                'unit': 'bunch',
                'category': 'vegetables',
                'image_url': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Sweet Alphonso Mangoes',
                'description': 'Premium seasonal mangoes with rich aroma and flavor.',
                'price': 140,
                'quantity': 70,
                'unit': 'kg',
                'category': 'fruits',
                'image_url': 'https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Banana Robusta',
                'description': 'Naturally ripened bananas for snacking and smoothies.',
                'price': 48,
                'quantity': 140,
                'unit': 'dozen',
                'category': 'fruits',
                'image_url': 'https://images.unsplash.com/photo-1603833665858-e61d17a86224?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Pomegranate Ruby',
                'description': 'Juicy pomegranates with bright red arils.',
                'price': 165,
                'quantity': 55,
                'unit': 'kg',
                'category': 'fruits',
                'image_url': 'https://images.unsplash.com/photo-1604495772376-9657f0035eb5?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Whole Wheat Grain',
                'description': 'Cleaned whole wheat grains for flour milling.',
                'price': 42,
                'quantity': 300,
                'unit': 'kg',
                'category': 'grains',
                'image_url': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Premium Sona Masoori Rice',
                'description': 'Lightweight aromatic rice suitable for everyday meals.',
                'price': 68,
                'quantity': 260,
                'unit': 'kg',
                'category': 'grains',
                'image_url': 'https://images.unsplash.com/photo-1536304993881-ff6e9eefa2a6?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Pearl Millet Bajra',
                'description': 'Nutritious bajra grains sourced from dryland farms.',
                'price': 36,
                'quantity': 210,
                'unit': 'kg',
                'category': 'grains',
                'image_url': 'https://images.unsplash.com/photo-1603569283847-aa295f0d016a?auto=format&fit=crop&q=80&w=700',
            },
            {
                'name': 'Fresh Green Beans',
                'description': 'Crisp green beans sorted for freshness and quality.',
                'price': 72,
                'quantity': 85,
                'unit': 'kg',
                'category': 'vegetables',
                'image_url': 'https://images.unsplash.com/photo-1567375698348-5d9d5ae99de0?auto=format&fit=crop&q=80&w=700',
            },
        ]

        for item in sample_products:
            existing_product = Product.query.filter_by(name=item['name'], seller_id=farmer.id).first()
            if not existing_product:
                db.session.add(Product(
                    **item,
                    seller_id=farmer.id,
                    is_fertilizer=False,
                    is_available=True
                ))
        
        # Create government schemes
        schemes_data = get_default_schemes()
        
        for scheme_data in schemes_data:
            existing = GovernmentScheme.query.filter_by(name=scheme_data['name']).first()
            if existing:
                updated = False
                for field in ('description', 'scheme_type', 'eligibility', 'benefits', 'official_url', 'deadline'):
                    if getattr(existing, field) != scheme_data[field]:
                        setattr(existing, field, scheme_data[field])
                        updated = True
                if updated:
                    db.session.add(existing)
            else:
                scheme = GovernmentScheme(**scheme_data)
                db.session.add(scheme)
        
        db.session.commit()
        print("Database initialized successfully!")
        print("\nDemo Accounts Created:")
        print("=======================")
        print("Admin:     admin@agriplatform.com / Admin@123")
        print("Farmer:    farmer@example.com / Farmer@123")
        print("Consumer:  consumer@example.com / Consumer@123")
        print("Supplier:  supplier@example.com / Supplier@123")

if __name__ == '__main__':
    init_database()
    app.run(debug=False, host='0.0.0.0', port=5000)
