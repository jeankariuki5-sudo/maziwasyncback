from django.db import IntegrityError, transaction
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.authentication import authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import FarmerProfile, PorterProfile, User


# Create your views here.


@api_view(['POST'])
@permission_classes([IsAdminUser])
def Register(request):

    role = request.data.get("role", "").strip().lower()

    try:
        with transaction.atomic():

            user = User.objects.create_user(
                username=request.data["username"],
                email=request.data["email"],
                password=request.data["password"],
                role=role,
                phone_number=request.data.get("phone_number"),
            )

            if role == "farmer":
                FarmerProfile.objects.create(
                    user=user,
                    first_name=request.data.get("first_name"),
                    last_name=request.data.get("last_name"),
                    national_id=request.data.get("national_id"),
                    phone_number=request.data.get("phone_number"),
                    farm_name=request.data.get("farm_name"),
                )

            elif role == "porter":
                PorterProfile.objects.create(
                    user=user,
                    first_name=request.data.get("first_name"),
                    last_name=request.data.get("last_name"),
                    national_id=request.data.get("national_id"),
                    phone_number=request.data.get("phone_number"),
                    employee_id=request.data.get("employee_id"),
                    route_name=request.data.get("route_name"),
                )

        return Response({
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

# login
@api_view(['POST'])
@permission_classes([AllowAny])
def Login(request):
    username=request.data.get("username")
    password=request.data.get("password")
    # print(username, password)

    user=authenticate(username=username, password=password)
    if not user:
        return Response({"error": "Invalid Credentials"})
    
    refresh=RefreshToken.for_user(user)
    
    return Response({
        "username": username,
        "role": user.role,
        "refresh": str(refresh),
        "access_token" :str(refresh.access_token)
    })


# ===============================================
# Get user/profile ot the logged in user
# ===============================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def MyProfile(request):
    user = request.user
    print(user)

    profile_data = {}
    if user.role == 'farmer' and hasattr(user, 'farmer_profile'):
        p = user.farmer_profile
        profile_data = {
            'first_name' : p.first_name,
            'last_name' : p.last_name,
            'phone_number' : p.phone_number,
            'farm_name' : p.farm_name
        }
    elif user.role == 'porter' and hasattr (user, 'porter_profile'):
        p = user.porter_profile
        profile_data = {
            'first_name' : p.first_name,
            'last_name' : p.last_name,
            'employee_id' : p.employee_id,
            'route_name' : p.route_name
        }

    return Response({
        'id' : user.id,
        'username' : user.username,
        'role' : user.role,
        'profile' : profile_data
    })


# ==========================================
# Logout
# ==========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def Logout(request):
    try:
        refresh_token =  request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"messgae" : "Logout successfull"})
    except TokenError:
        return Response({'error' : 'Invalid or expired token'})
    except Exception as e:
        return Response({'error' : str(e)})