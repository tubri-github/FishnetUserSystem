# app/api/v1/sso.py - SSO单点登录API
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode, parse_qs, urlparse

from app.database import get_async_session
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import BaseResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.rbac_service import RBACService
from app.dependencies import get_current_active_user
from app.models.user import User
from app.config import get_settings

router = APIRouter()
auth_service = AuthService()
user_service = UserService()
rbac_service = RBACService()
settings = get_settings()


@router.get("/login")
async def sso_login_redirect(
    redirect_uri: str = Query(..., description="登录成功后的重定向URI"),
    project: str = Query(..., description="请求登录的项目代码"),
    state: Optional[str] = Query(None, description="状态参数，用于防止CSRF攻击")
):
    """
    SSO登录重定向端点
    其他项目通过此端点重定向用户到统一登录页面
    """
    # 验证项目是否在允许列表中
    if project not in settings.ALLOWED_PROJECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"项目 '{project}' 未在允许列表中"
        )
    
    # 验证重定向URI是否合法
    parsed_uri = urlparse(redirect_uri)
    if project not in settings.PROJECT_URLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"项目 '{project}' URL配置不存在"
        )
    
    expected_host = urlparse(settings.PROJECT_URLS[project]).netloc
    if parsed_uri.netloc != expected_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重定向URI不匹配项目配置"
        )
    
    # 构建登录页面URL，包含重定向参数
    login_params = {
        "redirect_uri": redirect_uri,
        "project": project
    }
    if state:
        login_params["state"] = state
    
    login_url = f"/sso/login-page?{urlencode(login_params)}"
    return RedirectResponse(url=login_url, status_code=302)


@router.get("/login-page", response_class=HTMLResponse)
async def sso_login_page(
    request: Request,
    redirect_uri: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    state: Optional[str] = Query(None)
):
    """
    统一登录页面
    """
    # 检查用户是否已经登录
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_token and redirect_uri and project:
        # 用户已登录且有重定向参数，直接处理回调
        return RedirectResponse(
            url=f"/api/v1/sso/callback?redirect_uri={redirect_uri}&project={project}&state={state or ''}"
        )
    
    # 返回登录页面HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unified Auth Center - Sign In</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif;
                background: #f8fafc;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1rem;
            }}
            .login-container {{
                background: white;
                padding: 2.5rem;
                border-radius: 16px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                width: 100%;
                max-width: 420px;
                border: 1px solid #e2e8f0;
            }}
            .logo {{
                text-align: center;
                margin-bottom: 2rem;
            }}
            .logo h1 {{
                color: #1a202c;
                font-size: 1.875rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                letter-spacing: -0.025em;
            }}
            .logo p {{
                color: #64748b;
                font-size: 0.95rem;
                font-weight: 400;
            }}
            .project-info {{
                text-align: center;
                color: #475569;
                margin-bottom: 2rem;
                padding: 0.875rem;
                background: #f1f5f9;
                border-radius: 12px;
                border-left: 4px solid #3b82f6;
            }}
            .form-group {{
                margin-bottom: 1.25rem;
            }}
            label {{
                display: block;
                margin-bottom: 0.5rem;
                color: #374151;
                font-weight: 500;
                font-size: 0.95rem;
            }}
            input[type="text"], input[type="password"] {{
                width: 100%;
                padding: 0.875rem;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                font-size: 1rem;
                transition: all 0.2s ease;
                background: #fff;
            }}
            input[type="text"]:focus, input[type="password"]:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
                background: #fff;
            }}
            input[type="text"]::placeholder, input[type="password"]::placeholder {{
                color: #9ca3af;
            }}
            .login-btn {{
                width: 100%;
                padding: 0.875rem;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .login-btn:hover:not(:disabled) {{
                background: #2563eb;
                transform: translateY(-1px);
            }}
            .login-btn:active {{
                transform: translateY(0);
            }}
            .login-btn:disabled {{
                background: #9ca3af;
                cursor: not-allowed;
                transform: none;
            }}
            .error-message {{
                margin-top: 1rem;
                padding: 0.75rem;
                font-size: 0.9rem;
                border-radius: 8px;
                text-align: center;
            }}
            .divider {{
                display: flex;
                align-items: center;
                margin: 2rem 0 1.5rem;
            }}
            .divider::before,
            .divider::after {{
                content: '';
                flex: 1;
                height: 1px;
                background: #e5e7eb;
            }}
            .divider span {{
                padding: 0 1rem;
                color: #6b7280;
                font-size: 0.9rem;
                font-weight: 500;
            }}
            .oauth-section {{
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }}
            .oauth-btn {{
                width: 100%;
                padding: 0.875rem;
                border: 1.5px solid #e5e7eb;
                border-radius: 8px;
                background: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.75rem;
                font-size: 0.95rem;
                font-weight: 500;
                transition: all 0.2s ease;
                color: #374151;
            }}
            .oauth-btn:hover {{
                background: #f9fafb;
                border-color: #d1d5db;
                transform: translateY(-1px);
            }}
            .oauth-btn:active {{
                transform: translateY(0);
            }}
            .google-btn:hover {{
                border-color: #ea4335;
            }}
            .orcid-btn:hover {{
                border-color: #a6ce39;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>Auth Center</h1>
                <p>Secure access to your applications</p>
            </div>
            
            <div class="project-info">
                <p>Signing in to <strong>{project.upper() if project else 'Auth Center'}</strong></p>
            </div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Email or Username</label>
                    <input type="text" id="username" name="username" placeholder="Enter your email or username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter your password" required>
                </div>
                
                <button type="submit" class="login-btn" id="loginBtn">Sign In</button>
                <div id="errorMessage" class="error-message" style="display: none;"></div>
            </form>
            
            <div class="divider">
                <span>or continue with</span>
            </div>
            
            <div class="oauth-section">
                <button class="oauth-btn google-btn" onclick="loginWithGoogle()">
                    <svg width="18" height="18" viewBox="0 0 24 24">
                        <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Continue with Google
                </button>
                <button class="oauth-btn orcid-btn" onclick="loginWithOrcid()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#a6ce39">
                        <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947 0 .525-.422.947-.947.947-.525 0-.946-.422-.946-.947 0-.516.421-.947.946-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.016-5.325 5.016h-3.919V7.416zm1.444 1.303v7.444h2.297c2.359 0 3.988-1.323 3.988-3.722 0-2.397-1.616-3.722-3.988-3.722h-2.297z"/>
                    </svg>
                    Continue with ORCID
                </button>
            </div>
        </div>

        <script>
            const form = document.getElementById('loginForm');
            const loginBtn = document.getElementById('loginBtn');
            const errorMessage = document.getElementById('errorMessage');
            
            // 获取URL参数
            const urlParams = new URLSearchParams(window.location.search);
            const redirectUri = urlParams.get('redirect_uri');
            const project = urlParams.get('project');
            const state = urlParams.get('state');
            
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                if (!username || !password) {{
                    showError('Please enter both email/username and password');
                    return;
                }}
                
                loginBtn.disabled = true;
                loginBtn.textContent = 'Signing in...';
                
                try {{
                    const response = await fetch('/api/v1/auth/login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            username: username,
                            password: password
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        // 登录成功
                        if (redirectUri && project) {{
                            // 有重定向参数，进行SSO回调处理
                            const callbackParams = new URLSearchParams({{
                                redirect_uri: redirectUri,
                                project: project
                            }});
                            if (state) {{
                                callbackParams.append('state', state);
                            }}
                            window.location.href = `/api/v1/sso/callback?${{callbackParams.toString()}}`;
                        }} else {{
                            // 直接登录，跳转到认证中心首页或仪表板
                            showSuccess('Sign in successful!');
                            setTimeout(() => {{
                                window.location.href = '/api/v1/auth/me'; // 或其他合适的页面
                            }}, 1000);
                        }}
                    }} else {{
                        showError(result.message || 'Sign in failed');
                    }}
                }} catch (error) {{
                    showError('Network error. Please try again.');
                }} finally {{
                    loginBtn.disabled = false;
                    loginBtn.textContent = 'Sign In';
                }}
            }});
            
            function showError(message) {{
                errorMessage.textContent = message;
                errorMessage.style.display = 'block';
                errorMessage.style.color = '#e74c3c';
            }}
            
            function showSuccess(message) {{
                errorMessage.textContent = message;
                errorMessage.style.display = 'block';
                errorMessage.style.color = '#27ae60';
            }}
            
            function loginWithGoogle() {{
                const callbackParams = new URLSearchParams({{
                    redirect_uri: redirectUri,
                    project: project
                }});
                if (state) {{
                    callbackParams.append('state', state);
                }}
                
                window.location.href = `/api/v1/auth/google?${{callbackParams.toString()}}`;
            }}
            
            function loginWithOrcid() {{
                const callbackParams = new URLSearchParams({{
                    redirect_uri: redirectUri,
                    project: project
                }});
                if (state) {{
                    callbackParams.append('state', state);
                }}
                
                window.location.href = `/api/v1/auth/orcid?${{callbackParams.toString()}}`;
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/callback")
async def sso_callback(
    request: Request,
    response: Response,
    redirect_uri: str = Query(...),
    project: str = Query(...),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session)
):
    """
    SSO登录回调处理
    用户登录成功后，生成临时授权码并重定向回原项目
    """
    try:
        # 检查用户是否已登录
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_token:
            # 用户未登录，重定向到登录页面
            login_params = {
                "redirect_uri": redirect_uri,
                "project": project
            }
            if state:
                login_params["state"] = state
            
            login_url = f"/api/v1/sso/login-page?{urlencode(login_params)}"
            return RedirectResponse(url=login_url)
        
        # 验证会话并获取用户信息
        user = await auth_service.get_user_by_session(db, session_token)
        if not user:
            # 会话无效，重定向到登录页面
            response.delete_cookie(settings.SESSION_COOKIE_NAME)
            login_params = {
                "redirect_uri": redirect_uri,
                "project": project
            }
            if state:
                login_params["state"] = state
            
            login_url = f"/api/v1/sso/login-page?{urlencode(login_params)}"
            return RedirectResponse(url=login_url)
        
        # 检查用户对该项目的权限
        has_access = await rbac_service.check_user_project_access(db, user.id, project)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有访问项目 '{project}' 的权限"
            )
        
        # 生成临时授权码（5分钟有效）
        auth_code = await auth_service.generate_auth_code(
            db, user.id, project, redirect_uri
        )
        
        # 构建重定向URL，包含授权码
        callback_params = {
            "code": auth_code,
            "project": project
        }
        if state:
            callback_params["state"] = state
        
        # 解析重定向URI并添加参数
        parsed_uri = urlparse(redirect_uri)
        existing_params = parse_qs(parsed_uri.query)
        
        # 合并参数
        for key, value in callback_params.items():
            existing_params[key] = [value]
        
        # 重建查询字符串
        new_query = urlencode(existing_params, doseq=True)
        final_redirect_uri = f"{parsed_uri.scheme}://{parsed_uri.netloc}{parsed_uri.path}?{new_query}"
        
        return RedirectResponse(url=final_redirect_uri)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SSO回调处理失败: {str(e)}"
        )


@router.post("/exchange-token")
async def exchange_auth_code(
    code: str,
    project: str,
    redirect_uri: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    授权码换取访问令牌
    其他项目使用授权码换取用户的访问令牌
    """
    try:
        # 验证并消费授权码
        token_data = await auth_service.exchange_auth_code(
            db, code, project, redirect_uri
        )
        
        return BaseResponse(
            success=True,
            message="授权码交换成功",
            data=token_data
        )
        
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.get("/user-info")
async def get_sso_user_info(
    request: Request,
    project: str = Query(..., description="请求项目代码"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取SSO用户信息
    其他项目通过访问令牌获取用户信息和权限
    """
    try:
        # 从请求头获取访问令牌
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少访问令牌"
            )
        
        access_token = authorization[7:]  # 移除 "Bearer " 前缀
        
        # 验证令牌并获取用户信息
        user_info = await auth_service.get_user_by_access_token(
            db, access_token, project
        )
        
        # 获取用户在该项目的权限
        permissions = await rbac_service.get_user_project_permissions(
            db, user_info["user_id"], project
        )
        
        # 构建响应数据
        response_data = {
            **user_info,
            "permissions": permissions,
            "project_access": True
        }
        
        return BaseResponse(
            success=True,
            message="获取用户信息成功",
            data=response_data
        )
        
    except HTTPException as e:
        return BaseResponse(
            success=False,
            code=e.status_code,
            message=e.detail
        )


@router.post("/logout")
async def sso_logout(
    request: Request,
    response: Response,
    redirect_uri: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    SSO全局登出
    用户从任一项目登出时，清除所有项目的登录状态
    """
    try:
        # 获取会话令牌
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_token:
            # 清除服务器端会话
            await auth_service.logout(db, session_token)
        
        # 清除Cookie
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        
        if redirect_uri:
            return RedirectResponse(url=redirect_uri)
        
        return BaseResponse(
            success=True,
            message="全局登出成功",
            data="success"
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            message=f"登出失败: {str(e)}"
        )


@router.get("/check-session")
async def check_sso_session(
    request: Request,
    project: str = Query(..., description="请求项目代码"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    检查SSO会话状态
    其他项目可以通过此接口检查用户的登录状态
    """
    try:
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_token:
            return BaseResponse(
                success=False,
                code=401,
                message="未找到会话令牌"
            )
        
        # 验证会话
        user = await auth_service.get_user_by_session(db, session_token)
        if not user:
            return BaseResponse(
                success=False,
                code=401,
                message="会话已失效"
            )
        
        # 检查项目访问权限
        has_access = await rbac_service.check_user_project_access(db, user.id, project)
        
        return BaseResponse(
            success=True,
            message="会话有效",
            data={
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "has_project_access": has_access
            }
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            code=500,
            message=f"会话检查失败: {str(e)}"
        )