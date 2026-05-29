import math
from typing import List, Tuple
from .models import Mechanic, Customer

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points using Haversine formula
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r

def find_nearest_mechanics(customer_lat: float, customer_lon: float, 
                          count: int = 5, max_distance: float = 50.0) -> List[Tuple[Mechanic, float]]:
    """
    Find the nearest available mechanics using KNN algorithm
    Returns list of tuples: (mechanic, distance_in_km)
    Enhanced to find 4-5 nearest service shops
    """
    available_mechanics = Mechanic.objects.filter(
        status=True,  # Approved mechanics only
        is_available=True,  # Currently available
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )
    
    if not available_mechanics.exists():
        return []
    
    # Calculate distances for all available mechanics
    mechanic_distances = []
    for mechanic in available_mechanics:
        if mechanic.current_latitude and mechanic.current_longitude:
            distance = calculate_distance(
                customer_lat, customer_lon,
                float(mechanic.current_latitude), 
                float(mechanic.current_longitude)
            )
            
            # Only include mechanics within max_distance
            if distance <= max_distance:
                mechanic_distances.append((mechanic, distance))
    
    # Sort by distance (KNN - K Nearest Neighbors)
    mechanic_distances.sort(key=lambda x: x[1])
    
    # Return top K results (4-5 nearest service shops)
    return mechanic_distances[:count]

def find_nearest_customers(mechanic_lat: float, mechanic_lon: float, 
                          count: int = 10, max_distance: float = 50.0) -> List[Tuple[Customer, float]]:
    """
    Find the nearest customers for a mechanic
    Returns list of tuples: (customer, distance_in_km)
    """
    customers_with_location = Customer.objects.filter(
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )
    
    if not customers_with_location.exists():
        return []
    
    # Calculate distances for all customers
    customer_distances = []
    for customer in customers_with_location:
        if customer.current_latitude and customer.current_longitude:
            distance = calculate_distance(
                mechanic_lat, mechanic_lon,
                float(customer.current_latitude), 
                float(customer.current_longitude)
            )
            
            # Only include customers within max_distance
            if distance <= max_distance:
                customer_distances.append((customer, distance))
    
    # Sort by distance
    customer_distances.sort(key=lambda x: x[1])
    
    # Return top K results
    return customer_distances[:count]

def find_nearest_service_shops(user_lat: float, user_lon: float, 
                              count: int = 5, max_distance: float = 50.0) -> List[Tuple[Mechanic, float]]:
    """
    Find the nearest service shops (mechanics) for any user using KNN
    This is the main function for finding 4-5 nearest service shops
    """
    return find_nearest_mechanics(user_lat, user_lon, count, max_distance)

def find_nearest_mechanics_for_admin(admin_lat: float, admin_lon: float, 
                                   count: int = 5, max_distance: float = 100.0) -> List[Tuple[Mechanic, float]]:
    """
    Find nearest mechanics for admin monitoring (larger search radius)
    """
    available_mechanics = Mechanic.objects.filter(
        status=True,  # Approved mechanics only
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )
    
    if not available_mechanics.exists():
        return []
    
    # Calculate distances for all mechanics
    mechanic_distances = []
    for mechanic in available_mechanics:
        if mechanic.current_latitude and mechanic.current_longitude:
            distance = calculate_distance(
                admin_lat, admin_lon,
                float(mechanic.current_latitude), 
                float(mechanic.current_longitude)
            )
            
            # Include mechanics within max_distance
            if distance <= max_distance:
                mechanic_distances.append((mechanic, distance))
    
    # Sort by distance
    mechanic_distances.sort(key=lambda x: x[1])
    
    return mechanic_distances[:count]

def get_mechanic_service_area_stats(mechanic_id: int) -> dict:
    """
    Get statistics about a mechanic's service area and nearby customers
    """
    try:
        mechanic = Mechanic.objects.get(id=mechanic_id)
        
        if not mechanic.current_latitude or not mechanic.current_longitude:
            return {
                'total_customers_nearby': 0,
                'customers_within_10km': 0,
                'customers_within_25km': 0,
                'customers_within_50km': 0,
                'average_distance': 0,
                'service_area_coverage': 'Not available'
            }
        
        # Find customers in different radius ranges
        customers_10km = find_nearest_customers(
            float(mechanic.current_latitude), 
            float(mechanic.current_longitude), 
            count=100, 
            max_distance=10.0
        )
        
        customers_25km = find_nearest_customers(
            float(mechanic.current_latitude), 
            float(mechanic.current_longitude), 
            count=100, 
            max_distance=25.0
        )
        
        customers_50km = find_nearest_customers(
            float(mechanic.current_latitude), 
            float(mechanic.current_longitude), 
            count=100, 
            max_distance=50.0
        )
        
        # Calculate average distance
        total_distance = sum(distance for _, distance in customers_50km)
        avg_distance = total_distance / len(customers_50km) if customers_50km else 0
        
        # Determine service area coverage
        if len(customers_10km) >= 5:
            coverage = "High Density"
        elif len(customers_25km) >= 10:
            coverage = "Medium Density"
        elif len(customers_50km) >= 5:
            coverage = "Low Density"
        else:
            coverage = "Sparse Area"
        
        return {
            'total_customers_nearby': len(customers_50km),
            'customers_within_10km': len(customers_10km),
            'customers_within_25km': len(customers_25km),
            'customers_within_50km': len(customers_50km),
            'average_distance': round(avg_distance, 2),
            'service_area_coverage': coverage
        }
        
    except Mechanic.DoesNotExist:
        return {}

def update_mechanic_location(mechanic_id: int, lat: float, lon: float) -> bool:
    """
    Update mechanic's current location
    Returns True if successful, False otherwise
    """
    try:
        mechanic = Mechanic.objects.get(id=mechanic_id)
        mechanic.current_latitude = lat
        mechanic.current_longitude = lon
        mechanic.save()
        return True
    except Mechanic.DoesNotExist:
        return False

def update_customer_location(customer_id: int, lat: float, lon: float) -> bool:
    """
    Update customer's current location
    Returns True if successful, False otherwise
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        customer.current_latitude = lat
        customer.current_longitude = lon
        customer.save()
        return True
    except Customer.DoesNotExist:
        return False

def get_nearest_mechanics(customer_lat: float, customer_lon: float, radius_km: float = 50.0) -> List[Tuple[Mechanic, float]]:
    """
    Find nearest mechanics within specified radius using KNN algorithm
    Returns list of tuples: (mechanic, distance_in_km)
    """
    return find_nearest_mechanics(customer_lat, customer_lon, count=10, max_distance=radius_km)

def get_location_stats() -> dict:
    """
    Get location tracking statistics for admin dashboard
    Enhanced with KNN service area information
    """
    total_mechanics = Mechanic.objects.count()
    tracked_mechanics = Mechanic.objects.filter(
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).count()
    
    total_customers = Customer.objects.count()
    tracked_customers = Customer.objects.filter(
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).count()
    
    available_mechanics = Mechanic.objects.filter(
        status=True, 
        is_available=True,
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).count()
    
    # Calculate average service area coverage
    total_coverage = 0
    coverage_count = 0
    
    for mechanic in Mechanic.objects.filter(status=True):
        stats = get_mechanic_service_area_stats(mechanic.id)
        if stats and stats['total_customers_nearby'] > 0:
            total_coverage += stats['total_customers_nearby']
            coverage_count += 1
    
    avg_service_area = total_coverage / coverage_count if coverage_count > 0 else 0
    
    return {
        'total_mechanics': total_mechanics,
        'tracked_mechanics': tracked_mechanics,
        'total_customers': total_customers,
        'tracked_customers': tracked_customers,
        'available_mechanics': available_mechanics,
        'tracking_coverage_mechanics': (tracked_mechanics / total_mechanics * 100) if total_mechanics > 0 else 0,
        'tracking_coverage_customers': (tracked_customers / total_customers * 100) if total_customers > 0 else 0,
        'average_service_area_coverage': round(avg_service_area, 1),
        'mechanics_with_service_areas': coverage_count
    } 