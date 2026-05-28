from django.contrib.auth import login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator

from .serializers import LoginSerializer


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
                'role': user.role,
                'phone': user.phone,
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
                'role': getattr(user, 'role', ''),
                'phone': getattr(user, 'phone', ''),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'detail': 'CSRF cookie set.'}, status=status.HTTP_200_OK)
