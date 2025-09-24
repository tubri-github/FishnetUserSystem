# app/api/v1/fishair.py - FishAIR代理接口
from typing import List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import BaseResponse
from app.dependencies import get_current_user_optional
from app.models.user import User
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# FishAIR API配置
FISHAIR_BASE_URL = settings.PROJECT_URLS.get("fishair", "http://127.0.0.1:8003")


@router.get("/fish-images")
async def get_fish_images(
    scientific_name: str = Query(..., description="Scientific name of the fish"),
    limit: int = Query(5, description="Maximum number of images to return", ge=1, le=10),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取鱼类图片代理接口
    通过scientific name从fishair API获取鱼类图片信息
    """
    try:
        # 调用fishair API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{FISHAIR_BASE_URL}/fish-images/",
                params={
                    "scientific_name": scientific_name,
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                fishair_data = response.json()
                
                # 包装返回数据
                return BaseResponse(
                    success=True,
                    message=fishair_data.get("message", f"Found images for {scientific_name}"),
                    data={
                        "scientific_name": scientific_name,
                        "total_images": len(fishair_data.get("data", [])),
                        "images": fishair_data.get("data", [])
                    }
                )
            elif response.status_code == 400:
                return BaseResponse(
                    success=False,
                    code=400,
                    message="Invalid scientific name parameter"
                )
            elif response.status_code == 404:
                return BaseResponse(
                    success=True,
                    message=f"No images found for scientific name: {scientific_name}",
                    data={
                        "scientific_name": scientific_name,
                        "total_images": 0,
                        "images": []
                    }
                )
            else:
                return BaseResponse(
                    success=False,
                    code=response.status_code,
                    message=f"FishAIR API error: {response.text}"
                )
                
    except httpx.TimeoutException:
        return BaseResponse(
            success=False,
            code=504,
            message="FishAIR API timeout"
        )
    except httpx.RequestError as e:
        return BaseResponse(
            success=False,
            code=503,
            message=f"Failed to connect to FishAIR API: {str(e)}"
        )
    except Exception as e:
        return BaseResponse(
            success=False,
            code=500,
            message=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def fishair_health_check():
    """
    检查FishAIR API连接状态
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{FISHAIR_BASE_URL}/docs")
            
            if response.status_code == 200:
                return BaseResponse(
                    success=True,
                    message="FishAIR API is healthy",
                    data={"status": "connected", "url": FISHAIR_BASE_URL}
                )
            else:
                return BaseResponse(
                    success=False,
                    code=response.status_code,
                    message="FishAIR API is not responding correctly"
                )
                
    except Exception as e:
        return BaseResponse(
            success=False,
            code=503,
            message=f"Cannot connect to FishAIR API: {str(e)}"
        )