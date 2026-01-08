"""Test script for multi-tenancy functionality."""
import asyncio

import httpx

BASE_URL = "http://localhost:7777/api/v1"


async def test_multi_tenancy():
    """Test multi-tenancy functionality."""
    async with httpx.AsyncClient() as client:
        print("=== Multi-Tenancy Test ===\n")

        # Step 1: Create Tenant A
        print("1. Creating Tenant A...")
        tenant_a_response = await client.post(
            f"{BASE_URL}/auth/tenants/",
            json={
                "tenant_id": "tenant_a",
                "name": "BigCorp Finance",
                "description": "Finance Division",
            },
        )
        print(f"   Status: {tenant_a_response.status_code}")
        print(f"   Response: {tenant_a_response.json()}\n")

        # Step 2: Create Tenant B
        print("2. Creating Tenant B...")
        tenant_b_response = await client.post(
            f"{BASE_URL}/auth/tenants/",
            json={
                "tenant_id": "tenant_b",
                "name": "TechStart Manufacturing",
                "description": "Manufacturing Division",
            },
        )
        print(f"   Status: {tenant_b_response.status_code}")
        print(f"   Response: {tenant_b_response.json()}\n")

        # Step 3: Create User A (Tenant A)
        print("3. Creating User A (Tenant A)...")
        user_a_response = await client.post(
            f"{BASE_URL}/auth/users/",
            json={
                "email": "alice@bigcorp.com",
                "password": "password123",
                "full_name": "Alice Anderson",
                "tenant_id": "tenant_a",
            },
        )
        print(f"   Status: {user_a_response.status_code}")
        print(f"   Response: {user_a_response.json()}\n")

        # Step 4: Create User B (Tenant B)
        print("4. Creating User B (Tenant B)...")
        user_b_response = await client.post(
            f"{BASE_URL}/auth/users/",
            json={
                "email": "bob@techstart.com",
                "password": "password456",
                "full_name": "Bob Brown",
                "tenant_id": "tenant_b",
            },
        )
        print(f"   Status: {user_b_response.status_code}")
        print(f"   Response: {user_b_response.json()}\n")

        # Step 5: Login as User A
        print("5. Logging in as User A...")
        login_a_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "alice@bigcorp.com", "password": "password123"},
        )
        print(f"   Status: {login_a_response.status_code}")
        token_a_data = login_a_response.json()
        print(f"   Token: {token_a_data['access_token'][:30]}...")
        print(f"   Tenant ID: {token_a_data['tenant_id']}\n")

        token_a = token_a_data["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Step 6: Login as User B
        print("6. Logging in as User B...")
        login_b_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "bob@techstart.com", "password": "password456"},
        )
        print(f"   Status: {login_b_response.status_code}")
        token_b_data = login_b_response.json()
        print(f"   Token: {token_b_data['access_token'][:30]}...")
        print(f"   Tenant ID: {token_b_data['tenant_id']}\n")

        token_b = token_b_data["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Step 7: User A creates a repository
        print("7. User A creates a Git repository...")
        repo_a_response = await client.post(
            f"{BASE_URL}/repositories/",
            json={
                "name": "Finance App",
                "description": "Finance division application",
                "repository_type": "git",
                "source_url": "https://github.com/octocat/Hello-World.git",
            },
            headers=headers_a,
        )
        print(f"   Status: {repo_a_response.status_code}")
        print(f"   Response: {repo_a_response.json()}\n")

        # Step 8: User B creates a repository
        print("8. User B creates a Git repository...")
        repo_b_response = await client.post(
            f"{BASE_URL}/repositories/",
            json={
                "name": "Manufacturing App",
                "description": "Manufacturing division application",
                "repository_type": "git",
                "source_url": "https://github.com/octocat/Spoon-Knife.git",
            },
            headers=headers_b,
        )
        print(f"   Status: {repo_b_response.status_code}")
        print(f"   Response: {repo_b_response.json()}\n")

        # Step 9: User A lists repositories (should only see their own)
        print("9. User A lists repositories...")
        list_a_response = await client.get(f"{BASE_URL}/repositories/", headers=headers_a)
        print(f"   Status: {list_a_response.status_code}")
        list_a_data = list_a_response.json()
        print(f"   Total repositories: {list_a_data['total']}")
        print(f"   Repositories: {[r['name'] for r in list_a_data['repositories']]}\n")

        # Step 10: User B lists repositories (should only see their own)
        print("10. User B lists repositories...")
        list_b_response = await client.get(f"{BASE_URL}/repositories/", headers=headers_b)
        print(f"   Status: {list_b_response.status_code}")
        list_b_data = list_b_response.json()
        print(f"   Total repositories: {list_b_data['total']}")
        print(f"   Repositories: {[r['name'] for r in list_b_data['repositories']]}\n")

        # Step 11: Test isolation - User B tries to access User A's repository
        print("11. Test isolation: User B tries to access User A's repository...")
        repo_a_id = repo_a_response.json()["id"]
        access_test_response = await client.get(
            f"{BASE_URL}/repositories/{repo_a_id}", headers=headers_b
        )
        print(f"   Status: {access_test_response.status_code}")
        if access_test_response.status_code == 404:
            print("   ✅ SUCCESS: Tenant B cannot access Tenant A's repository!\n")
        else:
            print("   ❌ FAILURE: Tenant isolation broken!\n")

        # Step 12: List repositories without authentication
        print("12. Listing repositories without authentication...")
        unauth_response = await client.get(f"{BASE_URL}/repositories/")
        print(f"   Status: {unauth_response.status_code}")
        unauth_data = unauth_response.json()
        print(f"   Total repositories: {unauth_data['total']}")
        print(
            "   Note: Without auth, sees all repositories (no tenant filtering applied)\n"
        )

        print("=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_multi_tenancy())
