from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from pydantic import BaseModel
from ninja.errors import HttpError

router = Router()

class RegisterSchema(BaseModel):
    username: str
    password: str

class LoginSchema(RegisterSchema):
    pass

class TokenOut(BaseModel):
    access: str
    refresh: str

@router.post("register")
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        return {"error": "User already exists"}
    User.objects.create_user(username=data.username, password=data.password)
    return {"success": True}

@router.post("login", response={200: TokenOut, 401: dict})
def login(request, data: LoginSchema):
    user = authenticate(username=data.username, password=data.password)
    if not user:
        raise HttpError(401, {"error": "Invalid credentials"})

    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}

@router.get("me")
def get_current_user(request):
    user = request.auth
    return {
        "username": user.username,
        "is_superuser": user.is_superuser,
        "id": user.id,
    }
