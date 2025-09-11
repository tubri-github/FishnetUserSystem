# test_login_users.py
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


class AuthAPITester:
    def __init__(self):
        self.session_token = None
        self.jwt_token = None
        self.cookies = {}

    async def test_login(self, email="admin@example.com", password="admin123456"):
        """测试登录"""
        print("=" * 50)
        print("1. Testing Login")
        print("=" * 50)

        login_data = {
            "email": email,
            "password": password
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    json=login_data,
                    timeout=10.0
                )

                print(f"Login Status Code: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()

                    if result.get("success"):
                        print("✅ Login successful!")

                        # 保存认证信息
                        data = result.get("data", {})
                        self.jwt_token = data.get("access_token")
                        self.session_token = data.get("session_token")

                        # 模拟cookie设置
                        self.cookies["auth_session"] = self.session_token

                        # 打印用户信息
                        user_info = data.get("user", {})
                        print(f"User ID: {user_info.get('id')}")
                        print(f"Username: {user_info.get('username')}")
                        print(f"Email: {user_info.get('email')}")
                        print(f"Is Superuser: {user_info.get('is_superuser')}")

                        return True
                    else:
                        print(f"❌ Login failed: {result.get('message')}")
                        return False
                else:
                    print(f"❌ Login failed with status {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"Error details: {error_detail}")
                    except:
                        print(f"Response text: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Login request failed: {e}")
                return False

    async def test_users_api_with_jwt(self):
        """使用JWT Token测试用户API"""
        print("\n" + "=" * 50)
        print("2. Testing /api/v1/users with JWT Token")
        print("=" * 50)

        if not self.jwt_token:
            print("❌ No JWT token available")
            return False

        headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/users",
                    headers=headers,
                    timeout=10.0
                )

                print(f"Users API Status Code: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Users API call successful!")
                    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    print(f"❌ Users API call failed")
                    try:
                        error_detail = response.json()
                        print(f"Error details: {json.dumps(error_detail, indent=2)}")
                    except:
                        print(f"Response text: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Users API request failed: {e}")
                return False

    async def test_users_api_with_cookie(self):
        """使用Cookie Session测试用户API"""
        print("\n" + "=" * 50)
        print("3. Testing /api/v1/users with Cookie Session")
        print("=" * 50)

        if not self.session_token:
            print("❌ No session token available")
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/users",
                    cookies=self.cookies,
                    timeout=10.0
                )

                print(f"Users API Status Code: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Users API call with cookie successful!")
                    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    print(f"❌ Users API call with cookie failed")
                    try:
                        error_detail = response.json()
                        print(f"Error details: {json.dumps(error_detail, indent=2)}")
                    except:
                        print(f"Response text: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Users API request with cookie failed: {e}")
                return False

    async def test_protected_endpoints(self):
        """测试多个受保护的端点"""
        print("\n" + "=" * 50)
        print("4. Testing Multiple Protected Endpoints")
        print("=" * 50)

        endpoints = [
            "/api/v1/auth/me",
            "/api/v1/users",
            "/api/v1/roles",
            "/api/v1/permissions",
            "/api/v1/projects"
        ]

        headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

        results = {}

        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                try:
                    response = await client.get(
                        f"{BASE_URL}{endpoint}",
                        headers=headers,
                        timeout=5.0
                    )

                    results[endpoint] = {
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    }

                    status_icon = "✅" if response.status_code == 200 else "❌"
                    print(f"{status_icon} {endpoint}: {response.status_code}")

                    if response.status_code != 200:
                        try:
                            error = response.json()
                            print(f"   Error: {error.get('detail', 'Unknown error')}")
                        except:
                            pass

                except Exception as e:
                    results[endpoint] = {"status_code": "ERROR", "success": False}
                    print(f"❌ {endpoint}: Request failed - {e}")

        # 统计结果
        successful = sum(1 for r in results.values() if r["success"])
        total = len(results)
        print(f"\nSuccess rate: {successful}/{total} ({successful / total * 100:.1f}%)")

        return results

    async def test_without_auth(self):
        """测试未认证的请求"""
        print("\n" + "=" * 50)
        print("5. Testing Without Authentication")
        print("=" * 50)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/users",
                    timeout=5.0
                )

                print(f"Unauthenticated request status: {response.status_code}")

                if response.status_code == 401:
                    print("✅ Correctly rejected unauthenticated request")
                    return True
                else:
                    print(f"❌ Unexpected response for unauthenticated request")
                    try:
                        result = response.json()
                        print(f"Response: {json.dumps(result, indent=2)}")
                    except:
                        print(f"Response text: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Unauthenticated request failed: {e}")
                return False


async def test_server_connection():
    """测试服务器连接"""
    print("Testing server connection...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                print("✅ Server is running")
                return True
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"Make sure the server is running on {BASE_URL}")
        return False


async def main():
    """主测试函数"""
    print(f"Auth API Tester - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Server: {BASE_URL}")

    # 测试服务器连接
    if not await test_server_connection():
        return

    # 创建测试器实例
    tester = AuthAPITester()

    # 执行测试流程
    test_results = []

    # 1. 测试登录
    login_success = await tester.test_login()
    test_results.append(("Login", login_success))

    if login_success:
        # 2. 测试JWT认证的用户API
        jwt_success = await tester.test_users_api_with_jwt()
        test_results.append(("Users API (JWT)", jwt_success))

        # 3. 测试Cookie认证的用户API
        cookie_success = await tester.test_users_api_with_cookie()
        test_results.append(("Users API (Cookie)", cookie_success))

        # 4. 测试多个受保护端点
        await tester.test_protected_endpoints()

    # 5. 测试未认证请求
    unauth_success = await tester.test_without_auth()
    test_results.append(("Unauthenticated Request", unauth_success))

    # 打印总结
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, success in test_results:
        status = "PASS" if success else "FAIL"
        icon = "✅" if success else "❌"
        print(f"{icon} {test_name:<30}: {status}")

    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())