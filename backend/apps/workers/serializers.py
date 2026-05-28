from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import WorkerProfile


class WorkerProfileListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone', read_only=True)

    def get_full_name(self, obj):
        return obj.user.full_name or obj.user.username

    def get_role(self, obj):
        return obj.user.get_role_display() if obj.user else ''

    def get_avatar(self, obj):
        name = self.get_full_name(obj).strip()
        if not name:
            return '---'
        parts = [part for part in name.split(' ') if part]
        if len(parts) >= 2:
            return f'{parts[0][0]}‌{parts[1][0]}'
        return name[:2]

    class Meta:
        model = WorkerProfile
        fields = ['id', 'full_name', 'phone', 'role', 'avatar', 'is_available', 'load_status', 'active_jobs_count']
        



class WorkerProfileCreateUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    is_available = serializers.BooleanField(default=True)
    
    def create(self, validated_data):
        user_model = get_user_model()
        phone = validated_data['phone']
        full_name = validated_data['full_name']
        user = user_model.objects.filter(phone=phone).first()
        if not user:
            username = phone
            base = username
            counter = 1
            while user_model.objects.filter(username=username).exists():
                counter += 1
                username = f'{base}_{counter}'
            user = user_model.objects.create(
                username=username,
                full_name=full_name,
                phone=phone,
                role='worker',
                is_active=True,
            )
            user.set_password('Worker@12345')
            user.save()
        else:
            user.full_name = full_name
            if user.role != 'worker':
                user.role = 'worker'
            user.save(update_fields=['full_name', 'role'])

        profile, _ = WorkerProfile.objects.get_or_create(user=user)
        profile.is_available = validated_data.get('is_available', True)
        profile.save(update_fields=['is_available', 'updated_at'])
        
        return profile

    def update(self, instance, validated_data):
        instance.user.full_name = validated_data.get('full_name', instance.user.full_name)
        instance.user.phone = validated_data.get('phone', instance.user.phone)
        instance.user.save(update_fields=['full_name', 'phone'])
        instance.is_available = validated_data.get('is_available', instance.is_available)
        instance.save(update_fields=['is_available', 'updated_at'])
        
        return instance
