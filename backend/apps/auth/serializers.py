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


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'full_name', 'first_name', 'last_name', 'phone', 'role', 'is_active']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    class Meta:
        model = get_user_model()
        fields = ['username', 'full_name', 'first_name', 'last_name', 'phone', 'role', 'password', 'is_active']

    def validate_role(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            return value

        # Managers can create only non-privileged users.
        if getattr(request.user, 'role', '') == 'manager' and value in ['admin', 'owner']:
            raise serializers.ValidationError('مدیر نمی‌تواند کاربر ادمین یا مالک ایجاد کند.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        user_model = get_user_model()
        first_name = str(validated_data.get('first_name', '') or '').strip()
        last_name = str(validated_data.get('last_name', '') or '').strip()
        full_name = str(validated_data.get('full_name', '') or '').strip()
        if not full_name:
            validated_data['full_name'] = f'{first_name} {last_name}'.strip()
        validated_data['tenant'] = tenant
        user = user_model(**validated_data)
        user.set_password(password)
        user.save()
        return user


class TenantRegisterSerializer(serializers.Serializer):
    carwash_name = serializers.CharField(max_length=150)
    carwash_slug = serializers.SlugField(max_length=160)
    manager_full_name = serializers.CharField(max_length=150)
    manager_username = serializers.CharField(max_length=150)
    manager_phone = serializers.CharField(max_length=20)
    manager_password = serializers.CharField(write_only=True, min_length=6)
