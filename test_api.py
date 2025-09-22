#!/usr/bin/env python3
"""
Simple test script to verify PhotoHunter API endpoints
Run this after starting the Django server
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_api():
    print("🧪 Testing PhotoHunter API...")
    
    # Test 1: Check if API is accessible
    print("\n1. Testing API accessibility...")
    try:
        response = requests.get(f"{BASE_URL}/photohunts/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ API is running (authentication required)")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: User registration
    print("\n2. Testing user registration...")
    registration_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123",
        "password_confirm": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register/", json=registration_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ User registered successfully")
            user_data = response.json()
            token = user_data.get('token')
            print(f"   Token: {token[:20]}...")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: User login
    print("\n3. Testing user login...")
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ User logged in successfully")
            user_data = response.json()
            token = user_data.get('token')
            print(f"   Token: {token[:20]}...")
        else:
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 4: Get PhotoHunts (authenticated)
    print("\n4. Testing authenticated PhotoHunts endpoint...")
    headers = {"Authorization": f"Token {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/photohunts/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ PhotoHunts retrieved successfully")
            data = response.json()
            print(f"   Found {len(data.get('results', []))} PhotoHunts")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Create a PhotoHunt
    print("\n5. Testing PhotoHunt creation...")
    photohunt_data = {
        "name": "Test PhotoHunt",
        "description": "A test PhotoHunt for API testing",
        "latitude": 41.3907,
        "longitude": 2.1589,
        "reference_image": "https://example.com/test-image.jpg"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/photohunts/", json=photohunt_data, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ PhotoHunt created successfully")
            data = response.json()
            print(f"   PhotoHunt ID: {data.get('id')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 6: Get user profile
    print("\n6. Testing user profile...")
    try:
        response = requests.get(f"{BASE_URL}/profile/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ User profile retrieved successfully")
            data = response.json()
            print(f"   User: {data.get('user', {}).get('email')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 API testing completed!")

if __name__ == "__main__":
    test_api()
