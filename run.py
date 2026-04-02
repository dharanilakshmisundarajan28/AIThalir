from app import create_app, db
from app.models import User, UserRole, GovernmentScheme
from datetime import datetime

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
        
        # Create government schemes
        schemes_data = [
            {
                'name': 'PM-KISAN Samman Nidhi',
                'description': 'Income support of Rs. 6000 per year to all landholding farmer families',
                'scheme_type': 'subsidy',
                'eligibility': 'All landholding farmers',
                'benefits': 'Rs. 6000 per year in three installments',
                'official_url': 'https://pmkisan.gov.in',
                'deadline': datetime(2024, 12, 31)
            },
            {
                'name': 'Pradhan Mantri Fasal Bima Yojana',
                'description': 'Crop insurance scheme to protect farmers against crop loss',
                'scheme_type': 'insurance',
                'eligibility': 'All farmers growing notified crops',
                'benefits': 'Insurance coverage for crop loss due to natural calamities',
                'official_url': 'https://pmfby.gov.in',
                'deadline': datetime(2024, 12, 31)
            },
            {
                'name': 'National Agricultural Scholarship',
                'description': 'Scholarship for students pursuing agricultural education',
                'scheme_type': 'scholarship',
                'eligibility': 'Students enrolled in agricultural courses',
                'benefits': 'Up to Rs. 50,000 per year',
                'official_url': 'https://education.gov.in/scholarships',
                'deadline': datetime(2024, 10, 31)
            }
        ]
        
        for scheme_data in schemes_data:
            existing = GovernmentScheme.query.filter_by(name=scheme_data['name']).first()
            if not existing:
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