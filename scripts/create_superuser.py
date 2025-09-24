# scripts/create_superuser.py - 创建超级用户脚本
import asyncio
import uuid
from getpass import getpass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import async_session_maker
from app.models.user import User
from app.core.security import SecurityUtils


async def create_superuser(username=None, email=None, password=None, display_name=None):
    """创建超级用户"""
    if not username or not email or not password:
        print("交互式创建超级用户")
        print("=" * 30)

        username = input("用户名: ").strip()
        if not username:
            print("❌ 用户名不能为空")
            return

        email = input("邮箱: ").strip()
        if not email:
            print("❌ 邮箱不能为空")
            return

        password = getpass("密码: ").strip()
        if len(password) < 8:
            print("❌ 密码长度至少8位")
            return

        password_confirm = getpass("确认密码: ").strip()
        if password != password_confirm:
            print("❌ 两次密码输入不一致")
            return

        display_name = input("显示名称 (可选): ").strip() or username
    else:
        print(f"创建超级用户: {username}")
        if len(password) < 8:
            print("❌ 密码长度至少8位")
            return
        if not display_name:
            display_name = username

    async with async_session_maker() as db:
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            print(f"❌ 用户名 '{username}' 已存在")
            return

        # 检查邮箱是否已存在
        result = await db.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            print(f"❌ 邮箱 '{email}' 已存在")
            return

        # 创建超级用户
        user_data = {
            "id": uuid.uuid4(),
            "username": username,
            "email": email,
            "password_hash": SecurityUtils.get_password_hash(password),
            "display_name": display_name,
            "is_active": True,
            "is_verified": True,
            "is_superuser": True
        }

        user = User(**user_data)
        db.add(user)
        await db.commit()

        print("✅ 超级用户创建成功！")


if __name__ == "__main__":
    asyncio.run(create_superuser())
