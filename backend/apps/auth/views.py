from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator

from .models import CarWash
from .serializers import (
    LoginSerializer,
    TenantRegisterSerializer,
    UserCreateSerializer,
    UserListSerializer,
)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'phone': user.phone,
                'tenant_id': user.tenant_id,
                'tenant_name': user.tenant.name if user.tenant_id else '',
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'خروج انجام شد.'}, status=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'full_name': getattr(user, 'full_name', ''),
                'first_name': getattr(user, 'first_name', ''),
                'last_name': getattr(user, 'last_name', ''),
                'role': getattr(user, 'role', ''),
                'phone': getattr(user, 'phone', ''),
                'tenant_id': getattr(user, 'tenant_id', None),
                'tenant_name': getattr(getattr(user, 'tenant', None), 'name', ''),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'detail': 'CSRF cookie set.'}, status=status.HTTP_200_OK)


class UserManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') not in ['admin', 'manager']:
            return Response({'detail': 'شما دسترسی لازم را ندارید.'}, status=status.HTTP_403_FORBIDDEN)

        users = get_user_model().objects.filter(tenant=request.user.tenant).order_by('-id')
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, 'role', '') not in ['admin', 'manager']:
            return Response({'detail': 'شما دسترسی لازم را ندارید.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


class TenantRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = TenantRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if CarWash.objects.filter(slug=data['carwash_slug']).exists():
            return Response({'carwash_slug': ['این شناسه قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        user_model = get_user_model()
        if user_model.objects.filter(username=data['manager_username']).exists():
            return Response({'manager_username': ['این نام کاربری قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        if user_model.objects.filter(phone=data['manager_phone']).exists():
            return Response({'manager_phone': ['این شماره موبایل قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        tenant = CarWash.objects.create(
            name=data['carwash_name'],
            slug=data['carwash_slug'],
            is_active=True,
        )
        manager = user_model.objects.create(
            username=data['manager_username'],
            full_name=data['manager_full_name'],
            phone=data['manager_phone'],
            tenant=tenant,
            role='manager',
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        manager.set_password(data['manager_password'])
        manager.save(update_fields=['password'])

        return Response(
            {
                'tenant': {'id': tenant.id, 'name': tenant.name, 'slug': tenant.slug},
                'manager': {
                    'id': manager.id,
                    'username': manager.username,
                    'full_name': manager.full_name,
                    'role': manager.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )
