"""
This Python file is part of a FastAPI application, demonstrating user management functionalities including creating, reading,
updating, and deleting (CRUD) user information. It uses OAuth2 with Password Flow for security, ensuring that only authenticated
users can perform certain operations. Additionally, the file showcases the integration of FastAPI with SQLAlchemy for asynchronous
database operations, enhancing performance by non-blocking database calls.

The implementation emphasizes RESTful API principles, with endpoints for each CRUD operation and the use of HTTP status codes
and exceptions to communicate the outcome of operations. It introduces the concept of HATEOAS (Hypermedia as the Engine of
Application State) by including navigational links in API responses, allowing clients to discover other related operations dynamically.

OAuth2PasswordBearer is employed to extract the token from the Authorization header and verify the user's identity, providing a layer
of security to the operations that manipulate user data.

Key Highlights:
- Use of FastAPI's Dependency Injection system to manage database sessions and user authentication.
- Demonstrates how to perform CRUD operations in an asynchronous manner using SQLAlchemy with FastAPI.
- Implements HATEOAS by generating dynamic links for user-related actions, enhancing API discoverability.
- Utilizes OAuth2PasswordBearer for securing API endpoints, requiring valid access tokens for operations.
"""

from builtins import dict, int, len, str
from datetime import timedelta
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, logger, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user, get_db, get_email_service, require_role
from app.schemas.pagination_schema import EnhancedPagination
from app.schemas.token_schema import TokenResponse
from app.schemas.user_schemas import LoginRequest, UserBase, UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.services.jwt_service import create_access_token
from app.utils.link_generation import create_user_links, generate_pagination_links
from app.dependencies import get_settings
from app.services.email_service import EmailService
import urllib.parse

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
settings = get_settings()
@router.get("/users/{user_id}", response_model=UserResponse, name="get_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def get_user(user_id: UUID, request: Request, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Endpoint to fetch a user by their unique identifier (UUID).

    Utilizes the UserService to query the database asynchronously for the user and constructs a response
    model that includes the user's details along with HATEOAS links for possible next actions.

    Args:
        user_id: UUID of the user to fetch.
        request: The request object, used to generate full URLs in the response.
        db: Dependency that provides an AsyncSession for database access.
        token: The OAuth2 access token obtained through OAuth2PasswordBearer dependency.
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_construct(
        id=user.id,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        bio=user.bio,
        profile_picture_url=user.profile_picture_url,
        github_profile_url=user.github_profile_url,
        linkedin_profile_url=user.linkedin_profile_url,
        role=user.role,
        email=user.email,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        links=create_user_links(user.id, request)  
    )

# Additional endpoints for update, delete, create, and list users follow a similar pattern, using
# asynchronous database operations, handling security with OAuth2PasswordBearer, and enhancing response
# models with dynamic HATEOAS links.

# This approach not only ensures that the API is secure and efficient but also promotes a better client
# experience by adhering to REST principles and providing self-discoverable operations.

@router.put("/users/{user_id}", response_model=UserResponse, name="update_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def update_user(user_id: UUID, user_update: UserUpdate, request: Request, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Update user information.

    - **user_id**: UUID of the user to update.
    - **user_update**: UserUpdate model with updated user information.
    """
    user_data = user_update.model_dump(exclude_unset=True)
    updated_user = await UserService.update(db, user_id, user_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_construct(
        id=updated_user.id,
        bio=updated_user.bio,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        nickname=updated_user.nickname,
        email=updated_user.email,
        role=updated_user.role,
        last_login_at=updated_user.last_login_at,
        profile_picture_url=updated_user.profile_picture_url,
        github_profile_url=updated_user.github_profile_url,
        linkedin_profile_url=updated_user.linkedin_profile_url,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        links=create_user_links(updated_user.id, request)
    )

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Delete a user by their ID.

    - **user_id**: UUID of the user to delete.
    """
    success = await UserService.delete(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["User Management Requires (Admin or Manager Roles)"], name="create_user")
async def create_user(user: UserCreate, request: Request, db: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Create a new user.

    This endpoint creates a new user with the provided information. If the email
    already exists, it returns a 400 error. On successful creation, it returns the
    newly created user's information along with links to related actions.

    Parameters:
    - user (UserCreate): The user information to create.
    - request (Request): The request object.
    - db (AsyncSession): The database session.

    Returns:
    - UserResponse: The newly created user's information along with navigation links.
    """
    existing_user = await UserService.get_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
    created_user = await UserService.create(db, user.model_dump(), email_service)
    if not created_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    
    return UserResponse.model_construct(
        id=created_user.id,
        bio=created_user.bio,
        first_name=created_user.first_name,
        last_name=created_user.last_name,
        profile_picture_url=created_user.profile_picture_url,
        nickname=created_user.nickname,
        email=created_user.email,
        role=created_user.role,
        last_login_at=created_user.last_login_at,
        created_at=created_user.created_at,
        updated_at=created_user.updated_at,
        links=create_user_links(created_user.id, request)
    )

@router.get("/users/", response_model=UserListResponse, tags=["User Management Requires (Admin or Manager Roles)"])
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))
):
    total_users = await UserService.count(db)
    users = await UserService.list_users(db, skip, limit)

    user_responses = [
        UserResponse.model_validate(user) for user in users
    ]
    
    pagination_links = generate_pagination_links(request, skip, limit, total_users)
    
    # Construct the final response with pagination details
    return UserListResponse(
        items=user_responses,
        total=total_users,
        page=skip // limit + 1,
        size=len(user_responses),
        links=pagination_links  # Ensure you have appropriate logic to create these links
    )

@router.post("/register/", response_model=UserResponse, tags=["Login and Registration"])
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service)):
    user = await UserService.register_user(session, user_data.model_dump(), email_service)
    if user:
        return user
    raise HTTPException(status_code=400, detail="Email already exists")

@router.post("/login/", response_model=TokenResponse, tags=["Login and Registration"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    if await UserService.is_account_locked(session, form_data.username):
        raise HTTPException(status_code=400, detail="Account locked due to too many failed login attempts.")

    user = await UserService.login_user(session, form_data.username, form_data.password)
    if user:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

        access_token = create_access_token(
            data={"sub": user.email, "role": str(user.role.name)},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect email or password.")

@router.post("/login/", include_in_schema=False, response_model=TokenResponse, tags=["Login and Registration"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    if await UserService.is_account_locked(session, form_data.username):
        raise HTTPException(status_code=400, detail="Account locked due to too many failed login attempts.")

    user = await UserService.login_user(session, form_data.username, form_data.password)
    if user:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

        access_token = create_access_token(
            data={"sub": user.email, "role": str(user.role.name)},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect email or password.")

@router.get("/verify-email/{user_id}/{token}", status_code=status.HTTP_200_OK, name="verify_email", tags=["Login and Registration"])
async def verify_email(user_id: UUID, token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify user's email with a provided token.
    
    - **user_id**: UUID of the user to verify.
    - **token**: Verification token sent to the user's email.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to verify email for user_id: {user_id}, token: {token}")
    
    try:
        # First, check if user exists
        user = await UserService.get_by_id(db, user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found during email verification")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "User not found. The verification link may be invalid or the user account has been deleted."}
            )
        
        # Log the stored verification token for debugging
        logger.info(f"Found user: {user.email}, stored token: {user.verification_token}")
        
        # Try to verify with the token
        verification_result = await UserService.verify_email_with_token(db, user_id, token)
        
        if verification_result:
            logger.info(f"Email verified successfully for user {user_id}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Email verified successfully!",
                    "details": "Your account has been activated. You can now log in to your account."
                }
            )
        else:
            # If verification failed but user exists, the token must be invalid
            logger.warning(f"Invalid token for user {user_id}. Expected: {user.verification_token}, Got: {token}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid verification token",
                    "details": "The verification link may be expired or has already been used."
                }
            )
            
    except Exception as e:
        logger.error(f"Exception during email verification: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Server error",
                "details": "An unexpected error occurred while processing your verification request."
            }
        )

@router.put("/profile/", response_model=UserResponse, tags=["User Profile"])
async def update_own_profile(
    profile_update: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the authenticated user's profile information.
    
    This endpoint allows users to update their own profile fields such as 
    name, bio, and social media links.
    
    Args:
        profile_update: UserUpdate model with updated profile information.
        request: The request object.
        db: Database session.
        current_user: The authenticated user's information.
    
    Returns:
        UserResponse: The updated user profile with navigation links.
    """
    user_id = current_user.get("user_id")
    logger = logging.getLogger(__name__)
    logger.info(f"Updating profile for user with ID/email: {user_id}")
    
    # Convert email to user ID if necessary
    if "@" in user_id:  # If user_id is actually an email
        user = await UserService.get_by_email(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user_id = user.id
    
    # Exclude role from update data for security
    update_data = profile_update.model_dump(exclude_unset=True)
    if "role" in update_data:
        del update_data["role"]
    
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    logger.info(f"Found user: {user.email}, ID: {user.id}, is_professional: {user.is_professional}")
    
    updated_user = await UserService.update(db, user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Ensure we have the latest data
    await db.refresh(updated_user)
    logger.info(f"Updated user: {updated_user.email}, is_professional: {updated_user.is_professional}")
    
    return UserResponse.model_construct(
        id=updated_user.id,
        nickname=updated_user.nickname,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        bio=updated_user.bio,
        profile_picture_url=updated_user.profile_picture_url,
        github_profile_url=updated_user.github_profile_url,
        linkedin_profile_url=updated_user.linkedin_profile_url,
        role=updated_user.role,
        email=updated_user.email,
        is_professional=updated_user.is_professional,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        links=create_user_links(updated_user.id, request)
    )

@router.put("/users/{user_id}/professional-status", response_model=UserResponse, tags=["User Management Requires (Admin or Manager Roles)"])
async def update_professional_status(
    user_id: UUID, 
    request: Request,
    professional_status: bool = True,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))
):
    """
    Update a user's professional status.
    
    This endpoint allows managers and admins to upgrade users to professional status.
    
    Args:
        user_id: UUID of the user to update.
        request: The request object.
        professional_status: Boolean indicating the professional status (True for professional).
        db: Database session.
        email_service: Email service for sending notifications.
        current_user: The authenticated manager or admin's information.
    
    Returns:
        UserResponse: The updated user profile with navigation links.
    """
    # Fetch the user
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Only update if status is different
    if user.is_professional != professional_status:
        # Update the professional status
        user.update_professional_status(professional_status)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Send email notification if upgraded to professional
        if professional_status:
            try:
                # Prepare user data for email
                user_data = {
                    "name": user.first_name or user.nickname,
                    "email": user.email,
                    "verification_url": f"{settings.server_base_url}/users/{user.id}",
                }
                # Send the professional status upgrade email
                await email_service.send_user_email(user_data, 'professional_upgrade')
            except Exception as e:
                # Log the error but don't fail the request
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send professional upgrade email: {str(e)}")
    
    # Return the updated user
    return UserResponse.model_construct(
        id=user.id,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        bio=user.bio,
        profile_picture_url=user.profile_picture_url,
        github_profile_url=user.github_profile_url,
        linkedin_profile_url=user.linkedin_profile_url,
        role=user.role,
        email=user.email,
        is_professional=user.is_professional,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        links=create_user_links(user.id, request)
    )