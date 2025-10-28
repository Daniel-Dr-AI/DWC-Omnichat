#!/usr/bin/env python3
"""
Generate a fresh authentication token for testing
"""
import urllib.request
import urllib.parse
import json

def get_fresh_token():
    print("=" * 60)
    print("GENERATING FRESH AUTH TOKEN")
    print("=" * 60)

    # Login credentials (default admin)
    data = urllib.parse.urlencode({
        'username': 'admin@example.com',
        'password': 'admin123'
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            'http://localhost:8000/api/v1/auth/login',
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        response = urllib.request.urlopen(req)
        token_data = json.loads(response.read().decode())

        print(f"\n✅ Successfully generated token!")
        print(f"   Token type: {token_data.get('token_type')}")
        print(f"   Access token: {token_data.get('access_token')[:50]}...")

        # Save to file
        with open('authorizationtoken.txt', 'w') as f:
            json.dump(token_data, f, indent=2)

        print(f"\n✅ Saved to authorizationtoken.txt")
        print("\n💡 Now test the history endpoint:")
        print("   python3 test_history_api.py")

    except Exception as e:
        print(f"\n❌ Failed to generate token: {e}")
        print("\n💡 Make sure:")
        print("   1. Backend server is running on port 8000")
        print("   2. Admin credentials are: admin@example.com / admin123")

    print("=" * 60)

if __name__ == "__main__":
    get_fresh_token()
