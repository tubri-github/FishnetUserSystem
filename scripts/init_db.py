# scripts/init_db_enhanced.py - 增强版数据库初始化脚本
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, async_session_maker, Base
from app.models.user import User, UserPreferences
from app.models.rbac import Project, Role, Permission, RolePermission, UserRole
from app.models.auth import APIKey, ServiceKey
from app.core.security import SecurityUtils
from app.config import get_settings

settings = get_settings()


async def create_tables():
    """创建数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


async def create_projects():
    """创建项目"""
    async with async_session_maker() as db:
        projects_data = [
            {
                "id": uuid.uuid4(),
                "name": "Fishnet2",
                "code": "FN2",
                "description": "Fishnet2 - Data Platform",
                "base_url": "http://localhost:8001",
                "is_active": True
            },
            {
                "id": uuid.uuid4(),
                "name": "Fish Museum Management Tool",
                "code": "FMMT",
                "description": "Management System",
                "base_url": "http://localhost:8002",
                "is_active": True
            },
            {
                "id": uuid.uuid4(),
                "name": "FishAIR",
                "code": "FAIR",
                "description": "FishAIR - Fish AI Images Platform",
                "base_url": "http://localhost:8003",
                "is_active": True
            }
        ]

        project_ids = {}
        for project_data in projects_data:
            project = Project(**project_data)
            db.add(project)
            project_ids[project_data["code"]] = project_data["id"]

        await db.commit()
        print("✅ Projects created successfully")
        return project_ids


async def create_permissions(project_ids):
    """创建权限"""
    async with async_session_maker() as db:
        # 权限模板：(名称, 代码, 资源类型, 操作, 描述)
        permission_templates = [
            # 用户管理权限
            ("User Create", "user.create", "user", "create", "Create user account"),
            ("User Read", "user.read", "user", "read", "view user information"),
            ("User Update", "user.update", "user", "update", "update user information"),
            ("User Delete", "user.delete", "user", "delete", "delete user account"),
            ("User Manage", "user.manage", "user", "manage", "manage user account"),

            # 项目管理权限
            ("Project Access", "project.access", "project", "access", "access project"),
            ("Project Admin", "project.admin", "project", "admin", "project admin"),
            ("Project Read", "project.read", "project", "read", "View project information"),
            ("Project Manage", "project.manage", "project", "manage", "manage project "),

            # 数据权限
            ("Data Upload", "data.upload", "data", "upload", "upload data"),
            ("Data Download", "data.download", "data", "download", "download data"),
            ("Data View", "data.view", "data", "view", "view data"),
            ("Data Manage", "data.manage", "data", "manage", "manange data"),

            # 系统管理权限
            ("System Config", "system.config", "system", "config", "system configuration"),
            ("System Monitor", "system.monitor", "system", "monitor", "system monitor"),
            ("Audit Read", "audit.read", "audit", "read", "read audit logs"),
            ("Role Manage", "role.manage", "role", "manage", "manage roles"),
        ]

        permission_ids = {}
        for project_code, project_id in project_ids.items():
            permission_ids[project_code] = {}
            for name, code, resource_type, action, description in permission_templates:
                permission_data = {
                    "id": uuid.uuid4(),
                    "name": name,
                    "code": code,
                    "description": description,
                    "resource_type": resource_type,
                    "action": action,
                    "project_id": project_id
                }
                permission = Permission(**permission_data)
                db.add(permission)
                permission_ids[project_code][code] = permission_data["id"]

        await db.commit()
        print("✅ Permissions created successfully")
        return permission_ids


async def create_roles_and_assign_permissions(project_ids, permission_ids):
    """创建角色并分配权限"""
    async with async_session_maker() as db:
        role_ids = {}

        # 全局角色
        global_roles = [
            {
                "id": uuid.uuid4(),
                "name": "System Administrator",
                "code": "system_admin",
                "description": "System super administrator",
                "project_id": None,
                "is_system": True
            }
        ]

        for role_data in global_roles:
            role = Role(**role_data)
            db.add(role)
            role_ids[role_data["code"]] = role_data["id"]

        # 项目角色
        project_roles = {
            "FN2": [
                {
                    "name": "Data Provider",
                    "code": "data_provider",
                    "description": "Data Provider,access Musuem tool, and data provider funcs",
                    "permissions": ["project.access", "data.upload", "data.view", "data.manage"]
                },
                {
                    "name": "Regular User",
                    "code": "regular_user",
                    "description": "regular user, basic access permissions",
                    "permissions": ["project.access", "data.view"]
                }
            ],
            "FMMT": [
                {
                    "name": "System Manager",
                    "code": "system_manager",
                    "description": "System Manager",
                    "permissions": ["project.admin", "user.manage", "system.config", "system.monitor", "audit.read",
                                    "role.manage"]
                },
                {
                    "name": "Data Provider Portal",
                    "code": "data_provider_portal",
                    "description": "Data Provider Portal",
                    "permissions": ["project.access", "data.view", "data.download", "data.upload"]
                }
            ],
            "FAIR": [
                {
                    "name": "Portal User",
                    "code": "portal_user",
                    "description": "Portal regular user",
                    "permissions": ["project.access", "data.view", "data.download"]
                }
            ]
        }

        for project_code, roles in project_roles.items():
            project_id = project_ids[project_code]
            role_ids[project_code] = {}

            for role_info in roles:
                role_data = {
                    "id": uuid.uuid4(),
                    "name": role_info["name"],
                    "code": role_info["code"],
                    "description": role_info["description"],
                    "project_id": project_id,
                    "is_system": False
                }
                role = Role(**role_data)
                db.add(role)
                role_ids[project_code][role_info["code"]] = role_data["id"]

        await db.commit()

        # 分配权限给角色
        for project_code, roles in project_roles.items():
            for role_info in roles:
                role_id = role_ids[project_code][role_info["code"]]
                for permission_code in role_info["permissions"]:
                    if permission_code in permission_ids[project_code]:
                        permission_id = permission_ids[project_code][permission_code]
                        role_permission = RolePermission(
                            id=uuid.uuid4(),
                            role_id=role_id,
                            permission_id=permission_id
                        )
                        db.add(role_permission)

        await db.commit()
        print("✅ Roles and permissions assigned successfully")
        return role_ids


async def create_users_and_assign_roles(project_ids, role_ids):
    """创建用户并分配角色"""
    async with async_session_maker() as db:
        users_data = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "admin123456",
                "display_name": "System Administrator",
                "is_superuser": True,
                "is_verified": True,
                "roles": [
                    {"project": None, "role": "system_admin"},  # 全局管理员
                    {"project": "FMMT", "role": "system_manager"}  # 后台管理
                ]
            },
            {
                "username": "dataprovider1",
                "email": "dataprovider1@example.com",
                "password": "provider123456",
                "display_name": "Data Provider 1",
                "is_superuser": False,
                "is_verified": True,
                "roles": [
                    {"project": "FN2", "role": "data_provider"},  # A项目数据提供商
                    {"project": "FMMT", "role": "data_provider_portal"}  # B项目门户用户
                ]
            },
            {
                "username": "dataprovider2",
                "email": "dataprovider2@example.com",
                "password": "provider123456",
                "display_name": "Data Provider 2",
                "is_superuser": False,
                "is_verified": True,
                "roles": [
                    {"project": "FN2", "role": "data_provider"},
                    {"project": "FMMT", "role": "data_provider_portal"}
                ]
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": "user123456",
                "display_name": "Regular User 1",
                "is_superuser": False,
                "is_verified": True,
                "roles": [
                    {"project": "FN2", "role": "regular_user"},  # A项目普通用户
                    {"project": "FAIR", "role": "portal_user"}  # C项目门户用户
                ]
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "user123456",
                "display_name": "Regular User 2",
                "is_superuser": False,
                "is_verified": True,
                "roles": [
                    {"project": "FN2", "role": "regular_user"},
                    {"project": "FAIR", "role": "portal_user"}
                ]
            }
        ]

        user_ids = {}
        for user_data in users_data:
            # 创建用户
            user_info = {
                "id": uuid.uuid4(),
                "username": user_data["username"],
                "email": user_data["email"],
                "password_hash": SecurityUtils.get_password_hash(user_data["password"]),
                "display_name": user_data["display_name"],
                "is_active": True,
                "is_verified": user_data["is_verified"],
                "is_superuser": user_data["is_superuser"],
                "created_at": datetime.utcnow()
            }

            user = User(**user_info)
            db.add(user)
            user_ids[user_data["username"]] = user_info["id"]

            # 创建用户偏好设置
            preferences = UserPreferences(
                id=uuid.uuid4(),
                user_id=user_info["id"],
                language="en-US",
                timezone="UTC",
                theme="light"
            )
            db.add(preferences)

        await db.commit()

        # 分配角色给用户
        for user_data in users_data:
            user_id = user_ids[user_data["username"]]
            for role_assignment in user_data["roles"]:
                project_code = role_assignment["project"]
                role_code = role_assignment["role"]

                if project_code is None:
                    # 全局角色
                    role_id = role_ids[role_code]
                    project_id = None
                else:
                    # 项目角色
                    role_id = role_ids[project_code][role_code]
                    project_id = project_ids[project_code]

                user_role = UserRole(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role_id=role_id,
                    project_id=project_id,
                    granted_by=user_ids["admin"],  # 由管理员分配
                    granted_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(user_role)

        await db.commit()
        print("✅ Users and role assignments created successfully")
        return user_ids


async def create_api_keys(user_ids):
    """为用户创建API密钥"""
    async with async_session_maker() as db:
        api_keys_data = [
            {
                "user": "dataprovider1",
                "name": "Data Upload API Key",
                "permissions": {"data.upload": True, "data.view": True},
                "expires_days": 365
            },
            {
                "user": "dataprovider2",
                "name": "Data Upload API Key",
                "permissions": {"data.upload": True, "data.view": True},
                "expires_days": 365
            },
            {
                "user": "admin",
                "name": "Admin API Key",
                "permissions": {"*": True},  # 全部权限
                "expires_days": 180
            }
        ]

        created_keys = []
        for key_data in api_keys_data:
            api_key, key_hash = SecurityUtils.generate_api_key()

            api_key_obj = APIKey(
                id=uuid.uuid4(),
                user_id=user_ids[key_data["user"]],
                name=key_data["name"],
                key_hash=key_hash,
                permissions=key_data["permissions"],
                rate_limit=1000,
                expires_at=datetime.utcnow() + timedelta(days=key_data["expires_days"]),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(api_key_obj)
            created_keys.append({
                "user": key_data["user"],
                "name": key_data["name"],
                "key": api_key
            })

        await db.commit()
        print("✅ API keys created successfully")

        # 输出API密钥（仅在初始化时显示）
        print("\n📋 Created API Keys:")
        for key_info in created_keys:
            print(f"  {key_info['user']} - {key_info['name']}: {key_info['key']}")

        return created_keys


async def create_service_keys(project_ids):
    """创建项目间通信的服务密钥"""
    async with async_session_maker() as db:
        service_keys_data = [
            {
                "project": "FN2",
                "service_name": "Fishnet2 API Service",
                "allowed_projects": [project_ids["FMMT"], project_ids["FAIR"]],
                "permissions": {"data.read": True, "user.read": True}
            },
            {
                "project": "FMMT",
                "service_name": "Musuem Tool Management Service",
                "allowed_projects": [project_ids["FN2"], project_ids["FAIR"]],
                "permissions": {"user.manage": True, "audit.read": True}
            },
            {
                "project": "FAIR",
                "service_name": "FishAIR Portal Service",
                "allowed_projects": [project_ids["FN2"], project_ids["FMMT"]],
                "permissions": {"data.read": True, "user.read": True}
            }
        ]

        created_service_keys = []
        for key_data in service_keys_data:
            service_key, key_hash = SecurityUtils.generate_service_key()

            service_key_obj = ServiceKey(
                id=uuid.uuid4(),
                project_id=project_ids[key_data["project"]],
                service_name=key_data["service_name"],
                key_hash=key_hash,
                allowed_projects=key_data["allowed_projects"],
                permissions=key_data["permissions"],
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(service_key_obj)
            created_service_keys.append({
                "project": key_data["project"],
                "service": key_data["service_name"],
                "key": service_key
            })

        await db.commit()
        print("✅ Service keys created successfully")

        # 输出服务密钥
        print("\n🔗 Created Service Keys:")
        for key_info in created_service_keys:
            print(f"  {key_info['project']} - {key_info['service']}: {key_info['key']}")

        return created_service_keys


async def main():
    """主初始化函数"""
    print("🚀 Starting enhanced database initialization...")

    try:
        # 1. 创建数据库表
        await create_tables()

        # 2. 创建项目
        project_ids = await create_projects()

        # 3. 创建权限
        permission_ids = await create_permissions(project_ids)

        # 4. 创建角色并分配权限
        role_ids = await create_roles_and_assign_permissions(project_ids, permission_ids)

        # 5. 创建用户并分配角色
        user_ids = await create_users_and_assign_roles(project_ids, role_ids)

        # 6. 创建API密钥
        api_keys = await create_api_keys(user_ids)

        # 7. 创建服务密钥
        service_keys = await create_service_keys(project_ids)

        print("\n🎉 Enhanced database initialization completed!")
        print("\n📋 Summary:")
        print("👥 Users created:")
        print("  - admin (System Administrator): admin@example.com / admin123456")
        print("  - dataprovider1 (Data Provider): dataprovider1@example.com / provider123456")
        print("  - dataprovider2 (Data Provider): dataprovider2@example.com / provider123456")
        print("  - user1 (Regular User): user1@example.com / user123456")
        print("  - user2 (Regular User): user2@example.com / user123456")
        print("\n🏗️ Projects:")
        print("  - Project A: Data Platform (localhost:8001)")
        print("  - Project B: Management System (localhost:8002)")
        print("  - Project C: User Portal (localhost:8003)")
        print("\n🔐 Access Matrix:")
        print("  - System Admin: All projects + backend management")
        print("  - Data Providers: Project A (special pages) + Project C (normal user)")
        print("  - Regular Users: Project A + Project C (normal users)")

    except Exception as e:
        print(f"❌ Enhanced database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())