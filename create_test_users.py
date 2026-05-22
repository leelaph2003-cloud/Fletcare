#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicleservicemanagement.settings')
django.setup()

from django.contrib.auth.models import User, Group
from vehicle import models

def create_test_users():
    # Create CUSTOMER group if it doesn't exist
    customer_group, created = Group.objects.get_or_create(name='CUSTOMER')
    print(f"Customer group: {'Created' if created else 'Already exists'}")
    
    # Create MECHANIC group if it doesn't exist
    mechanic_group, created = Group.objects.get_or_create(name='MECHANIC')
    print(f"Mechanic group: {'Created' if created else 'Already exists'}")
    
    # Create test customer
    if not User.objects.filter(username='testcustomer').exists():
        customer_user = User.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Customer'
        )
        customer_user.groups.add(customer_group)
        
        # Create customer profile
        customer = models.Customer.objects.create(
            user=customer_user,
            address='Test Address',
            mobile='1234567890',
            profile_pic=''
        )
        print("Test customer created: testcustomer / testpass123")
    else:
        print("Test customer already exists")
    
    # Create test mechanic
    if not User.objects.filter(username='testmechanic').exists():
        mechanic_user = User.objects.create_user(
            username='testmechanic',
            email='mechanic@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Mechanic'
        )
        mechanic_user.groups.add(mechanic_group)
        
        # Create mechanic profile
        mechanic = models.Mechanic.objects.create(
            user=mechanic_user,
            address='Test Address',
            mobile='1234567890',
            skill='General Repair',
            profile_pic='',
            status=True  # Approved
        )
        print("Test mechanic created: testmechanic / testpass123")
    else:
        print("Test mechanic already exists")
    
    # Create admin user if it doesn't exist
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        print("Admin user created: admin / admin123")
    else:
        print("Admin user already exists")
    
    print("\nTest users created successfully!")
    print("You can now test login functionality with:")
    print("- Customer: testcustomer / testpass123")
    print("- Mechanic: testmechanic / testpass123")
    print("- Admin: admin / admin123")

if __name__ == '__main__':
    create_test_users() 