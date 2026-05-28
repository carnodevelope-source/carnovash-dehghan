from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_phone = attrs.get('username', '').strip()
        password = attrs.get('password')

        resolved_username = username_or_phone
        user_model = get_user_model()

        user_by_phone = user_model.objects.filter(phone=username_or_phone).first()
        if user_by_phone:
            resolved_username = user_by_phone.username

        user = authenticate(username=resolved_username, password=password)
        if not user:
            raise serializers.ValidationError('نام کاربری/شماره همراه یا رمز عبور اشتباه است.')
        if not user.is_active:
            raise serializers.ValidationError('حساب کاربری غیرفعال است.')

        attrs['user'] = user
        return attrs
