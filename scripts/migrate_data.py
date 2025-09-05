# scripts/migrate_data.py - Data Migration Script
import asyncio
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_maker
from app.models.user import User
from app.models.rbac import Project, Role, Permission


async def export_data():
    """Export data to JSON file"""
    async with async_session_maker() as db:
        # Export user data
        from sqlalchemy import select

        users = await db.execute(select(User))
        users_data = []
        for user in users.scalars():
            users_data.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat()
            })

        # Export project data
        projects = await db.execute(select(Project))
        projects_data = []
        for project in projects.scalars():
            projects_data.append({
                "id": str(project.id),
                "name": project.name,
                "code": project.code,
                "description": project.description,
                "base_url": project.base_url,
                "is_active": project.is_active
            })

        # Save to file
        export_data = {
            "users": users_data,
            "projects": projects_data,
            "exported_at": datetime.utcnow().isoformat()
        }

        export_path = Path("data_export.json")
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Data export completed: {export_path}")


async def import_data(file_path: str):
    """Import data from JSON file"""
    if not Path(file_path).exists():
        print(f"❌ File does not exist: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session_maker() as db:
        # Import user data
        for user_data in data.get("users", []):
            # Check if user already exists
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.email == user_data["email"])
            )
            if result.scalar_one_or_none():
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash="",  # Password needs to be reset
                display_name=user_data.get("display_name"),
                is_active=user_data.get("is_active", True),
                is_verified=user_data.get("is_verified", False),
                is_superuser=user_data.get("is_superuser", False)
            )
            db.add(user)

        await db.commit()
        print("✅ Data import completed")


if __name__ == "__main__":
    import sys
    from datetime import datetime

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Export: python migrate_data.py export")
        print("  Import: python migrate_data.py import <file_path>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "export":
        asyncio.run(export_data())
    elif command == "import":
        if len(sys.argv) < 3:
            print("❌ Please specify import file path")
            sys.exit(1)
        asyncio.run(import_data(sys.argv[2]))
    else:
        print("❌ Unknown command")