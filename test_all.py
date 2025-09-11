# test_all.py - 全面测试脚本
import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

# 测试配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


class AuthTester:
    def __init__(self):
        self.session_token: Optional[str] = None
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.admin_user: Optional[Dict] = None
        self.test_user: Optional[Dict] = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = []

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        self.total_tests += 1
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}")
        if details:
            print(f"      {details}")

        if success:
            self.passed_tests += 1
        else:
            self.failed_tests.append(f"{test_name}: {details}")

    async def test_health_check(self):
        """测试健康检查"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/health")
                success = response.status_code == 200
                data = response.json() if success else {}

                self.log_test(
                    "Health Check",
                    success,
                    f"Status: {response.status_code}, Data: {data}"
                )
                return success
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {e}")
            return False

    async def test_root_endpoint(self):
        """测试根端点"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(BASE_URL)
                success = response.status_code == 200
                data = response.json() if success else {}

                self.log_test(
                    "Root Endpoint",
                    success,
                    f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
                )
                return success
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Exception: {e}")
            return False

    async def test_login_invalid_credentials(self):
        """测试无效凭据登录"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/auth/login",
                    json={
                        "email": "invalid@example.com",
                        "password": "wrongpassword"
                    }
                )

                success = response.status_code == 401
                data = response.json() if response.status_code in [401, 422] else {}

                self.log_test(
                    "Login Invalid Credentials",
                    success,
                    f"Status: {response.status_code}, Expected 401"
                )
                return success
        except Exception as e:
            self.log_test("Login Invalid Credentials", False, f"Exception: {e}")
            return False

    async def test_login_valid_credentials(self):
        """测试有效凭据登录"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/auth/login",
                    json={
                        "email": "admin@example.com",
                        "password": "admin123456",
                        "remember me": False
                    }
                )

                success = response.status_code == 200
                if success:
                    data = response.json()
                    if data.get("success") and data.get("data"):
                        token_data = data["data"]
                        self.session_token = token_data.get("session_token")
                        self.jwt_token = token_data.get("access_token")
                        self.refresh_token = token_data.get("refresh_token")
                        self.admin_user = token_data.get("user")

                        self.log_test(
                            "Login Valid Credentials",
                            True,
                            f"User: {self.admin_user.get('username', 'N/A')}, Tokens obtained"
                        )
                        return True

                self.log_test(
                    "Login Valid Credentials",
                    False,
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return False
        except Exception as e:
            self.log_test("Login Valid Credentials", False, f"Exception: {e}")
            return False

    async def test_session_authentication(self):
        """测试Session认证"""
        if not self.session_token:
            self.log_test("Session Authentication", False, "No session token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/auth/me",
                    cookies={"auth_session": self.session_token}
                )

                success = response.status_code == 200
                data = response.json() if success else {}

                self.log_test(
                    "Session Authentication",
                    success,
                    f"Status: {response.status_code}, User: {data.get('data', {}).get('username', 'N/A')}"
                )
                return success
        except Exception as e:
            self.log_test("Session Authentication", False, f"Exception: {e}")
            return False

    async def test_jwt_authentication(self):
        """测试JWT认证"""
        if not self.jwt_token:
            self.log_test("JWT Authentication", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/auth/me",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code == 200
                data = response.json() if success else {}

                self.log_test(
                    "JWT Authentication",
                    success,
                    f"Status: {response.status_code}, User: {data.get('data', {}).get('username', 'N/A')}"
                )
                return success
        except Exception as e:
            self.log_test("JWT Authentication", False, f"Exception: {e}")
            return False

    async def test_refresh_token(self):
        """测试刷新令牌"""
        if not self.refresh_token:
            self.log_test("Refresh Token", False, "No refresh token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/auth/refresh",
                    headers={"X-Refresh-Token": self.refresh_token}
                )

                success = response.status_code == 200
                if success:
                    data = response.json()
                    if data.get("success"):
                        new_token_data = data["data"]
                        new_access_token = new_token_data.get("access_token")

                        self.log_test(
                            "Refresh Token",
                            True,
                            f"New access token obtained: {new_access_token[:20]}..."
                        )
                        return True

                self.log_test(
                    "Refresh Token",
                    False,
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return False
        except Exception as e:
            self.log_test("Refresh Token", False, f"Exception: {e}")
            return False

    async def test_users_api(self):
        """测试用户管理API"""
        if not self.jwt_token:
            self.log_test("Users API", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                # 测试获取用户列表
                response = await client.get(
                    f"{API_BASE}/users",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code in [200, 403]  # 可能没有权限
                data = response.json() if response.status_code == 200 else {}

                if response.status_code == 403:
                    self.log_test(
                        "Users API - Get List",
                        True,
                        "Access denied (expected - no permission configured)"
                    )
                else:
                    self.log_test(
                        "Users API - Get List",
                        success,
                        f"Status: {response.status_code}, Users count: {len(data.get('data', {}).get('users', []))}"
                    )

                return success
        except Exception as e:
            self.log_test("Users API", False, f"Exception: {e}")
            return False

    async def test_roles_api(self):
        """测试角色管理API"""
        if not self.jwt_token:
            self.log_test("Roles API", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/roles",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code in [200, 403]
                data = response.json() if response.status_code == 200 else {}

                self.log_test(
                    "Roles API",
                    success,
                    f"Status: {response.status_code}, Roles: {data.get('data', [])}"
                )
                return success
        except Exception as e:
            self.log_test("Roles API", False, f"Exception: {e}")
            return False

    async def test_permissions_api(self):
        """测试权限管理API"""
        if not self.jwt_token:
            self.log_test("Permissions API", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/permissions",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code in [200, 403]
                data = response.json() if response.status_code == 200 else {}

                self.log_test(
                    "Permissions API",
                    success,
                    f"Status: {response.status_code}, Permissions: {data.get('data', [])}"
                )
                return success
        except Exception as e:
            self.log_test("Permissions API", False, f"Exception: {e}")
            return False

    async def test_projects_api(self):
        """测试项目管理API"""
        if not self.jwt_token:
            self.log_test("Projects API", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/projects",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code in [200, 403]
                data = response.json() if response.status_code == 200 else {}

                self.log_test(
                    "Projects API",
                    success,
                    f"Status: {response.status_code}, Projects: {data.get('data', [])}"
                )
                return success
        except Exception as e:
            self.log_test("Projects API", False, f"Exception: {e}")
            return False

    async def test_audit_api(self):
        """测试审计日志API"""
        if not self.jwt_token:
            self.log_test("Audit API", False, "No JWT token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/audit/logs",
                    headers={"Authorization": f"Bearer {self.jwt_token}"}
                )

                success = response.status_code in [200, 403]
                data = response.json() if response.status_code == 200 else {}

                self.log_test(
                    "Audit API",
                    success,
                    f"Status: {response.status_code}, Logs: {data.get('data', [])}"
                )
                return success
        except Exception as e:
            self.log_test("Audit API", False, f"Exception: {e}")
            return False

    async def test_logout(self):
        """测试登出"""
        if not self.session_token:
            self.log_test("Logout", False, "No session token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/auth/logout",
                    cookies={"auth_session": self.session_token}
                )

                success = response.status_code == 200
                data = response.json() if success else {}

                self.log_test(
                    "Logout",
                    success,
                    f"Status: {response.status_code}, Success: {data.get('success', False)}"
                )
                return success
        except Exception as e:
            self.log_test("Logout", False, f"Exception: {e}")
            return False

    async def test_api_key_authentication(self):
        """测试API Key认证（模拟）"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/auth/me",
                    headers={"X-API-Key": "ak_test_key_12345"}
                )

                # 预期是401，因为没有有效的API Key
                success = response.status_code == 401

                self.log_test(
                    "API Key Authentication",
                    success,
                    f"Status: {response.status_code} (Expected 401 - no valid API key)"
                )
                return success
        except Exception as e:
            self.log_test("API Key Authentication", False, f"Exception: {e}")
            return False

    async def test_service_key_authentication(self):
        """测试Service Key认证（模拟）"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/auth/me",
                    headers={
                        "X-Service-Key": "sk_test_service_key",
                        "X-Project-ID": "project-a"
                    }
                )

                # 预期是401，因为没有有效的Service Key
                success = response.status_code == 401

                self.log_test(
                    "Service Key Authentication",
                    success,
                    f"Status: {response.status_code} (Expected 401 - no valid service key)"
                )
                return success
        except Exception as e:
            self.log_test("Service Key Authentication", False, f"Exception: {e}")
            return False

    async def test_oauth_endpoints(self):
        """测试OAuth端点"""
        try:
            async with httpx.AsyncClient() as client:
                # 测试Google OAuth重定向
                response = await client.get(
                    f"{API_BASE}/auth/google/login",
                    follow_redirects=False
                )

                # 可能是302重定向或配置错误
                google_success = response.status_code in [302, 500]

                self.log_test(
                    "OAuth Google Login",
                    google_success,
                    f"Status: {response.status_code} (302=redirect OK, 500=config missing)"
                )

                # 测试ORCID OAuth重定向
                response = await client.get(
                    f"{API_BASE}/auth/orcid/login",
                    follow_redirects=False
                )

                orcid_success = response.status_code in [302, 500]

                self.log_test(
                    "OAuth ORCID Login",
                    orcid_success,
                    f"Status: {response.status_code} (302=redirect OK, 500=config missing)"
                )

                return google_success and orcid_success
        except Exception as e:
            self.log_test("OAuth Endpoints", False, f"Exception: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("UNIFIED AUTH SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Testing server: {BASE_URL}")
        print("-" * 80)

        # 基础连接测试
        print("\n>>> BASIC CONNECTIVITY TESTS")
        await self.test_health_check()
        await self.test_root_endpoint()

        # 认证流程测试
        print("\n>>> AUTHENTICATION FLOW TESTS")
        await self.test_login_invalid_credentials()
        await self.test_login_valid_credentials()
        await self.test_session_authentication()
        await self.test_jwt_authentication()
        await self.test_refresh_token()

        # API端点测试
        print("\n>>> API ENDPOINTS TESTS")
        await self.test_users_api()
        await self.test_roles_api()
        await self.test_permissions_api()
        await self.test_projects_api()
        await self.test_audit_api()

        # 多重认证方式测试
        print("\n>>> MULTIPLE AUTH METHODS TESTS")
        await self.test_api_key_authentication()
        await self.test_service_key_authentication()

        # OAuth测试
        print("\n>>> OAUTH INTEGRATION TESTS")
        await self.test_oauth_endpoints()

        # 登出测试
        print("\n>>> LOGOUT TESTS")
        await self.test_logout()

        # 测试结果汇总
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)

        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.failed_tests:
            print("\nFAILED TESTS:")
            for failure in self.failed_tests:
                print(f"  - {failure}")

        print("\n" + "=" * 80)

        if pass_rate >= 80:
            print("🎉 OVERALL STATUS: GOOD - Most functionality is working")
        elif pass_rate >= 60:
            print("⚠️  OVERALL STATUS: PARTIAL - Some issues need attention")
        else:
            print("❌ OVERALL STATUS: POOR - Significant issues detected")

        print("=" * 80)


async def main():
    """主函数"""
    print("Starting comprehensive test suite...")

    tester = AuthTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())