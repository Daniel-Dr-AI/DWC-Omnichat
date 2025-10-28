#!/usr/bin/env python3
"""
Test the /admin/api/history endpoint with authentication
"""
import urllib.request
import json

def test_history_api():
    print("=" * 60)
    print("TESTING /admin/api/history ENDPOINT")
    print("=" * 60)

    # Load token
    try:
        with open('authorizationtoken.txt', 'r') as f:
            token_data = json.load(f)
            token = token_data['access_token']
    except Exception as e:
        print(f"\n❌ Failed to load token: {e}")
        print("   Run: python3 refresh_token.py")
        return

    # Test history endpoint
    try:
        req = urllib.request.Request(
            'http://localhost:8000/admin/api/history',
            headers={'Authorization': f'Bearer {token}'}
        )

        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())

        print(f"\n✅ Endpoint responded successfully!")
        print(f"   Status: {response.status}")
        print(f"   Response keys: {list(data.keys())}")

        history = data.get('history', [])
        print(f"\n📊 History data:")
        print(f"   Total items: {len(history)}")

        if history:
            print(f"\n📋 First 3 items:")
            for item in history[:3]:
                source = item.get('source', 'unknown')
                user = item.get('user_id', 'N/A')
                updated = item.get('updated_at', 'N/A')
                msg_count = item.get('message_count', 0)
                print(f"   - [{source}] {user} - {msg_count} messages - {updated}")

            print(f"\n✅ The endpoint is working correctly!")
            print(f"   It's returning {len(history)} history records")
        else:
            print(f"\n⚠️  Endpoint returned empty history array")
            print(f"   Check database for closed conversations")

    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error {e.code}: {e.reason}")
        if e.code == 401:
            print("   Token is invalid or expired")
            print("   Run: python3 refresh_token.py")
    except Exception as e:
        print(f"\n❌ Failed to test endpoint: {e}")
        print("   Make sure backend is running on port 8000")

    print("=" * 60)

if __name__ == "__main__":
    test_history_api()
