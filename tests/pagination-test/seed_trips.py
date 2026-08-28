import os
import sys
import random
from pathlib import Path
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Load .env explicitly
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

from sqlalchemy.orm import Session
from backend.database import init_db, SessionLocal
from backend.models.trip import Trip
from backend.models.user import User
from backend.services.auth_service import hash_password, normalize_username
from backend.services.trip_service import (
    get_trip_category, 
    get_recommended_transportation, 
    get_travel_season, 
    get_recommended_places
)

DESTINATIONS = [
    {"destination": "Tokyo", "country": "Japan", "days": 5, "travel_month": "December", "budget": 3000.0},
    {"destination": "Oslo", "country": "Norway", "days": 7, "travel_month": "June", "budget": 4500.0},
    {"destination": "Bali", "country": "Indonesia", "days": 10, "travel_month": "August", "budget": 1000.0},
    {"destination": "Paris", "country": "France", "days": 4, "travel_month": "May", "budget": 2500.0},
    {"destination": "New York", "country": "USA", "days": 6, "travel_month": "October", "budget": 4000.0},
    {"destination": "Cairo", "country": "Egypt", "days": 5, "travel_month": "January", "budget": 1200.0},
    {"destination": "Sydney", "country": "Australia", "days": 8, "travel_month": "February", "budget": 3500.0},
    {"destination": "Rio de Janeiro", "country": "Brazil", "days": 7, "travel_month": "March", "budget": 1800.0},
    {"destination": "Cape Town", "country": "South Africa", "days": 6, "travel_month": "April", "budget": 2000.0},
    {"destination": "Kyoto", "country": "Japan", "days": 4, "travel_month": "November", "budget": 2200.0},
    {"destination": "Reykjavik", "country": "Iceland", "days": 5, "travel_month": "September", "budget": 3800.0},
    {"destination": "Istanbul", "country": "Turkey", "days": 6, "travel_month": "July", "budget": 1500.0},
]

def main():
    if len(sys.argv) != 2:
        print("Usage: python seed_trips.py <username>")
        sys.exit(1)

    raw_username = sys.argv[1]
    
    # Initialize DB (creates tables if missing)
    try:
        init_db()
    except RuntimeError as e:
        print(f"Error initializing DB: {e}")
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        username = normalize_username(raw_username)
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found. Creating user with password 'password123'...")
            user = User(username=username, password_hash=hash_password("password123"))
            db.add(user)
            db.commit()
            db.refresh(user)

        print(f"Injecting trips for user: {username} (ID: {user.id})")
        
        # Select 11 random destinations to test pagination (page size is 10)
        selected = random.sample(DESTINATIONS, 11)
        
        for i, item in enumerate(selected):
            budget = item["budget"]
            days = item["days"]
            daily_budget = round(budget / days, 2)
            category = get_trip_category(budget)
            
            trip = Trip(
                user_id=user.id,
                destination=item["destination"],
                country=item["country"],
                days=days,
                budget=budget,
                daily_budget=daily_budget,
                currency="USD",
                travel_month=item["travel_month"],
                category=category,
                travel_season=get_travel_season(item["travel_month"]),
                recommended_places=get_recommended_places(category),
                recommended_transportation=get_recommended_transportation(category),
                ai_recommendation=f"### Seeded Trip {i+1}\n\nThis is a seeded dummy recommendation for {item['destination']} to test pagination."
            )
            db.add(trip)
        
        db.commit()
        print("Successfully injected 11 dummy trips!")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
