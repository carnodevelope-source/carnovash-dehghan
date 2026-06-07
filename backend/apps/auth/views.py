from datetime import datetime, time, timedelta
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import StockMovement
from apps.payments.models import CashflowTransaction, Payment, Wallet, WalletGatewayRequest
from apps.vehicles.models import VehicleEntry
from .models import CarWash, SupportTicket, SupportTicketMessage, User
from .serializers import (
    CarWashCreateSerializer,
    CarWashListSerializer,
    CarWashUpdateSerializer,
    HqSupportUserListSerializer,
    HqSupportUserCreateSerializer,
    LoginSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketFeedbackSerializer,
    SupportTicketListSerializer,
    SupportTicketMessageSerializer,
    SupportTicketReplySerializer,
    TenantRegisterSerializer,
    UserCreateSerializer,
    UserListSerializer,
)


def _parse_dt(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, '%Y-%m-%d')
    dt = datetime.combine(dt.date(), time.max if end_of_day else time.min)
    return timezone.make_aware(dt)


def _legacy_platform_role(user):
    if getattr(user, 'username', '') in {'karimi', 'dehestani'}:
        return User.PlatformRoles.HQ_ADMIN
    return User.PlatformRoles.NONE


def _platform_role(user):
    if not getattr(user, 'is_authenticated', False):
        return User.PlatformRoles.NONE
    return getattr(user, 'platform_role', None) or _legacy_platform_role(user)


def _is_hq_user(user):
    return _platform_role(user) in {User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT}


def _is_hq_admin(user):
    return _platform_role(user) == User.PlatformRoles.HQ_ADMIN


def _auth_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'platform_role': _platform_role(user),
        'phone': user.phone,
        'tenant_id': user.tenant_id,
        'tenant_name': user.tenant.name if user.tenant_id else '',
        'is_hq': _is_hq_user(user),
        'is_hq_admin': _is_hq_admin(user),
    }


def _response_status_score(status_value):
    return {
        SupportTicket.Status.CLOSED: Decimal('5.0'),
        SupportTicket.Status.ANSWERED: Decimal('4.4'),
        SupportTicket.Status.PENDING: Decimal('3.6'),
        SupportTicket.Status.OPEN: Decimal('3.0'),
    }.get(status_value, Decimal('3.0'))


def _response_length_score(body):
    size = len(str(body or '').strip())
    if size >= 280:
        return Decimal('5.0')
    if size >= 160:
        return Decimal('4.6')
    if size >= 80:
        return Decimal('4.2')
    if size >= 40:
        return Decimal('3.7')
    return Decimal('2.8')


def _response_quality_score(ticket, body):
    status_score = _response_status_score(ticket.status)
    length_score = _response_length_score(body)
    return ((status_score * Decimal('0.65')) + (length_score * Decimal('0.35'))).quantize(Decimal('0.01'))


def _response_speed_score(first_response_minutes):
    minutes = float(first_response_minutes or 0)
    if minutes <= 10:
        return Decimal('5.0')
    if minutes <= 30:
        return Decimal('4.7')
    if minutes <= 60:
        return Decimal('4.2')
    if minutes <= 180:
        return Decimal('3.6')
    if minutes <= 720:
        return Decimal('3.0')
    if minutes <= 1440:
        return Decimal('2.4')
    return Decimal('1.8')


def _average_decimal(values):
    if not values:
        return Decimal('0')
    total = sum((Decimal(str(value)) for value in values), Decimal('0'))
    return (total / Decimal(str(len(values)))).quantize(Decimal('0.01'))


def _recalculate_support_metrics(user):
    if not user or user.platform_role not in {User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT}:
        return

    tickets = list(
        SupportTicket.objects.filter(assigned_to=user, responded_at__isnull=False).only(
            'id',
            'status',
            'created_at',
            'first_response_at',
            'response_quality_score',
            'customer_satisfaction',
        )
    )
    satisfaction_values = [ticket.customer_satisfaction for ticket in tickets if ticket.customer_satisfaction]
    quality_values = [ticket.response_quality_score for ticket in tickets if Decimal(str(ticket.response_quality_score or 0)) > 0]
    response_minutes = []
    response_speed_values = []
    resolved_count = 0

    for ticket in tickets:
        if ticket.status == SupportTicket.Status.CLOSED:
            resolved_count += 1
        if ticket.first_response_at and ticket.created_at:
            minutes = max((ticket.first_response_at - ticket.created_at).total_seconds() / 60, 0)
            response_minutes.append(Decimal(str(round(minutes, 2))))
            response_speed_values.append(_response_speed_score(minutes))

    satisfaction_avg = _average_decimal(satisfaction_values)
    quality_avg = _average_decimal(quality_values)
    first_response_minutes_avg = _average_decimal(response_minutes)
    speed_avg = _average_decimal(response_speed_values)

    weighted_parts = []
    if satisfaction_values:
        weighted_parts.append((satisfaction_avg, Decimal('0.55')))
    if quality_values:
        weighted_parts.append((quality_avg, Decimal('0.30')))
    if response_speed_values:
        weighted_parts.append((speed_avg, Decimal('0.15')))

    if weighted_parts:
        total_weight = sum((weight for _, weight in weighted_parts), Decimal('0'))
        star_rating = (sum((value * weight for value, weight in weighted_parts), Decimal('0')) / total_weight).quantize(Decimal('0.01'))
    else:
        star_rating = Decimal('0')

    user.support_star_rating = star_rating
    user.support_rating_count = len(satisfaction_values)
    user.support_customer_satisfaction_avg = satisfaction_avg
    user.support_response_quality_avg = quality_avg
    user.support_first_response_minutes_avg = first_response_minutes_avg
    user.support_total_responses = len(tickets)
    user.support_resolved_tickets_count = resolved_count
    user.support_last_scored_at = timezone.now()
    user.save(
        update_fields=[
            'support_star_rating',
            'support_rating_count',
            'support_customer_satisfaction_avg',
            'support_response_quality_avg',
            'support_first_response_minutes_avg',
            'support_total_responses',
            'support_resolved_tickets_count',
            'support_last_scored_at',
        ]
    )


def _tenant_ticket_queryset():
    visible_messages = SupportTicketMessage.objects.filter(is_internal=False).select_related('sender').order_by('created_at', 'id')
    return (
        SupportTicket.objects.select_related('tenant', 'created_by', 'assigned_to', 'responded_by')
        .prefetch_related(Prefetch('messages', queryset=visible_messages))
    )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(_auth_payload(user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'خروج با موفقیت انجام شد.'}, status=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        return Response(_auth_payload(request.user), status=status.HTTP_200_OK)


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
        return Response(UserListSerializer(users, many=True).data, status=status.HTTP_200_OK)

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

        tenant = CarWash.objects.create(name=data['carwash_name'], slug=data['carwash_slug'], is_active=True)
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
                'manager': {'id': manager.id, 'username': manager.username, 'full_name': manager.full_name, 'role': manager.role},
            },
            status=status.HTTP_201_CREATED,
        )


class SupportTicketListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response([], status=status.HTTP_200_OK)
        tickets = _tenant_ticket_queryset().filter(tenant=tenant).order_by('-last_message_at', '-created_at')
        return Response(SupportTicketListSerializer(tickets, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ticket = SupportTicket.objects.create(
            tenant=tenant,
            created_by=request.user,
            subject=data['subject'],
            message=data['message'],
            category=data.get('category') or SupportTicket.Category.OTHER,
            priority=data.get('priority') or SupportTicket.Priority.MEDIUM,
            status=SupportTicket.Status.OPEN,
            last_message_at=timezone.now(),
        )
        SupportTicketMessage.objects.create(ticket=ticket, sender=request.user, body=data['message'])
        return Response(SupportTicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


class SupportTicketDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        ticket = _tenant_ticket_queryset().filter(pk=pk, tenant=request.user.tenant).first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupportTicketDetailSerializer(ticket).data, status=status.HTTP_200_OK)


class SupportTicketFeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        ticket = SupportTicket.objects.filter(pk=pk, tenant=request.user.tenant).select_related('assigned_to').first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if ticket.status not in {SupportTicket.Status.ANSWERED, SupportTicket.Status.CLOSED}:
            return Response({'detail': 'امتیازدهی فقط بعد از پاسخ پشتیبانی ممکن است.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ticket.assigned_to_id:
            return Response({'detail': 'پشتیبان این تیکت مشخص نشده است.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SupportTicketFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket.customer_satisfaction = data['customer_satisfaction']
        ticket.customer_feedback = (data.get('customer_feedback') or '').strip()
        ticket.save(update_fields=['customer_satisfaction', 'customer_feedback', 'updated_at'])
        _recalculate_support_metrics(ticket.assigned_to)
        refreshed_ticket = _tenant_ticket_queryset().filter(pk=ticket.pk, tenant=request.user.tenant).first()
        return Response(SupportTicketDetailSerializer(refreshed_ticket).data, status=status.HTTP_200_OK)


class SupportTicketMessageCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        ticket = SupportTicket.objects.filter(pk=pk, tenant=request.user.tenant).first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=data['body'],
            is_internal=False,
        )
        ticket.status = SupportTicket.Status.PENDING if ticket.responded_by_id else SupportTicket.Status.OPEN
        ticket.last_message_at = message.created_at
        ticket.save(update_fields=['status', 'last_message_at', 'updated_at'])
        return Response(SupportTicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class HqBaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def forbid_if_not_hq(self, request):
        if _is_hq_user(request.user):
            return None
        return Response({'detail': 'دسترسی فقط برای کاربران پنل مرکزی است.'}, status=status.HTTP_403_FORBIDDEN)

    def forbid_if_not_hq_admin(self, request):
        if _is_hq_admin(request.user):
            return None
        return Response({'detail': 'دسترسی فقط برای مدیرکل مجاز است.'}, status=status.HTTP_403_FORBIDDEN)


class HqOverviewView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        open_statuses = [SupportTicket.Status.OPEN, SupportTicket.Status.PENDING]
        summary = {
            'active_carwashes': CarWash.objects.filter(is_active=True).count(),
            'total_carwashes': CarWash.objects.count(),
            'open_tickets': SupportTicket.objects.filter(status__in=open_statuses).count(),
            'urgent_tickets': SupportTicket.objects.filter(status__in=open_statuses, priority=SupportTicket.Priority.URGENT).count(),
            'hq_support_users': User.objects.filter(platform_role=User.PlatformRoles.HQ_SUPPORT, is_active=True).count(),
            'today_vehicles': VehicleEntry.objects.filter(check_in_at__date=timezone.localdate()).count(),
        }

        recent_carwashes = CarWash.objects.order_by('-created_at')[:5]
        recent_tickets = SupportTicket.objects.select_related('tenant', 'created_by', 'assigned_to').order_by('-last_message_at', '-created_at')[:6]
        return Response(
            {
                'summary': summary,
                'recent_carwashes': CarWashListSerializer(recent_carwashes, many=True).data,
                'recent_tickets': SupportTicketListSerializer(recent_tickets, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class HqCarWashListCreateView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden
        rows = CarWash.objects.order_by('-id')
        return Response(CarWashListSerializer(rows, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        serializer = CarWashCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_model = get_user_model()
        if user_model.objects.filter(username=data['manager_username']).exists():
            return Response({'manager_username': ['این نام کاربری قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)
        if user_model.objects.filter(phone=data['manager_phone']).exists():
            return Response({'manager_phone': ['این شماره موبایل قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        base_slug = slugify(data['carwash_name']) or 'carwash'
        unique_slug = base_slug
        index = 1
        while CarWash.objects.filter(slug=unique_slug).exists():
            index += 1
            unique_slug = f'{base_slug}-{index}'
        tenant = CarWash.objects.create(
            name=data['carwash_name'],
            slug=unique_slug,
            address=(data.get('carwash_address') or '').strip(),
            is_active=True,
        )
        first_name = data['manager_first_name'].strip()
        last_name = data['manager_last_name'].strip()
        manager = user_model.objects.create(
            username=data['manager_username'],
            first_name=first_name,
            last_name=last_name,
            full_name=f'{first_name} {last_name}'.strip(),
            phone=data['manager_phone'],
            tenant=tenant,
            role='manager',
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        manager.set_password(data['manager_password'])
        manager.save(update_fields=['password'])
        return Response(CarWashListSerializer(tenant).data, status=status.HTTP_201_CREATED)


class HqCarWashUpdateView(HqBaseView):
    def patch(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        tenant = CarWash.objects.filter(pk=pk).first()
        if not tenant:
            return Response({'detail': 'کارواش یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CarWashUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        changed_fields = []
        if 'carwash_name' in data:
            tenant.name = data['carwash_name']
            changed_fields.append('name')
        if 'carwash_address' in data:
            tenant.address = (data.get('carwash_address') or '').strip()
            changed_fields.append('address')
        if 'is_active' in data:
            tenant.is_active = data['is_active']
            changed_fields.append('is_active')
        if changed_fields:
            changed_fields.append('updated_at')
            tenant.save(update_fields=changed_fields)

        manager = get_user_model().objects.filter(tenant=tenant, role='manager').order_by('id').first()
        if manager:
            first_name = data.get('manager_first_name', manager.first_name)
            last_name = data.get('manager_last_name', manager.last_name)
            manager.first_name = first_name
            manager.last_name = last_name
            manager.full_name = f'{first_name} {last_name}'.strip()
            if 'manager_phone' in data:
                manager.phone = data['manager_phone']
            if 'manager_password' in data:
                manager.set_password(data['manager_password'])
            manager.save()

        return Response(CarWashListSerializer(tenant).data, status=status.HTTP_200_OK)


class HqSupportUserListCreateView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden
        users = User.objects.filter(platform_role__in=[User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT]).order_by('platform_role', 'first_name', 'last_name')
        return Response(HqSupportUserListSerializer(users, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        forbidden = self.forbid_if_not_hq_admin(request)
        if forbidden:
            return forbidden

        serializer = HqSupportUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(HqSupportUserListSerializer(user).data, status=status.HTTP_201_CREATED)


class HqTicketListView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        q = str(request.query_params.get('q', '')).strip()
        status_filter = str(request.query_params.get('status', 'all')).strip().lower()
        priority_filter = str(request.query_params.get('priority', 'all')).strip().lower()
        tenant_id = request.query_params.get('tenant_id')

        queryset = (
            SupportTicket.objects.select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .prefetch_related('messages__sender')
            .order_by('-last_message_at', '-created_at')
        )
        if status_filter in {choice[0] for choice in SupportTicket.Status.choices}:
            queryset = queryset.filter(status=status_filter)
        if priority_filter in {choice[0] for choice in SupportTicket.Priority.choices}:
            queryset = queryset.filter(priority=priority_filter)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if q:
            queryset = queryset.filter(
                Q(subject__icontains=q)
                | Q(message__icontains=q)
                | Q(tenant__name__icontains=q)
                | Q(created_by__full_name__icontains=q)
                | Q(created_by__username__icontains=q)
            )

        return Response(SupportTicketListSerializer(queryset[:300], many=True).data, status=status.HTTP_200_OK)


class HqTicketDetailView(HqBaseView):
    def get(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        ticket = (
            SupportTicket.objects.filter(pk=pk)
            .select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .prefetch_related('messages__sender')
            .first()
        )
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupportTicketDetailSerializer(ticket).data, status=status.HTTP_200_OK)


class HqTicketMessageCreateView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        ticket = SupportTicket.objects.filter(pk=pk).select_related('assigned_to').first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        previous_assignee = ticket.assigned_to
        if data.get('assign_to_user_id'):
            assignee = User.objects.filter(
                id=data['assign_to_user_id'],
                platform_role__in=[User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT],
            ).first()
            if assignee:
                ticket.assigned_to = assignee
        elif not ticket.assigned_to_id:
            ticket.assigned_to = request.user

        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=data['body'],
            is_internal=bool(data.get('is_internal', False)),
        )
        ticket.last_message_at = message.created_at
        if not data.get('is_internal', False):
            ticket.response_text = data['body']
            ticket.responded_by = request.user
            ticket.responded_at = message.created_at
            if not ticket.first_response_at:
                ticket.first_response_at = message.created_at
            if data.get('status'):
                ticket.status = data['status']
                if data['status'] == SupportTicket.Status.CLOSED:
                    ticket.closed_at = message.created_at
            else:
                ticket.status = SupportTicket.Status.ANSWERED
            ticket.response_quality_score = _response_quality_score(ticket, data['body'])
        elif data.get('status'):
            ticket.status = data['status']
            if data['status'] == SupportTicket.Status.CLOSED:
                ticket.closed_at = message.created_at
        ticket.save(
            update_fields=[
                'assigned_to',
                'response_text',
                'responded_by',
                'first_response_at',
                'responded_at',
                'last_message_at',
                'status',
                'closed_at',
                'response_quality_score',
                'updated_at',
            ]
        )
        if previous_assignee and previous_assignee.id != ticket.assigned_to_id:
            _recalculate_support_metrics(previous_assignee)
        if ticket.assigned_to_id:
            _recalculate_support_metrics(ticket.assigned_to)
        return Response(SupportTicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)


def _build_hq_report_snapshot(start=None, end=None):
    tenants = list(CarWash.objects.order_by('name').only('id', 'name', 'is_active'))
    grouped = {
        tenant.id: {
            'tenant_id': tenant.id,
            'tenant_name': tenant.name,
            'tenant_is_active': tenant.is_active,
            'vehicles_count': 0,
            'released_count': 0,
            'cancelled_count': 0,
            'active_queue_count': 0,
            'payments_count': 0,
            'paid_amount': Decimal('0'),
            'pending_amount': Decimal('0'),
            'expense_total': Decimal('0'),
            'tips_total': Decimal('0'),
            'discount_total': Decimal('0'),
            'services_total': Decimal('0'),
            'products_total': Decimal('0'),
            'refunded_total': Decimal('0'),
            'wallet_balance': Decimal('0'),
            'wallet_regular_balance': Decimal('0'),
            'wallet_sms_balance': Decimal('0'),
            'wallet_deposit_total': Decimal('0'),
            'wallet_withdraw_total': Decimal('0'),
            'wallet_gateway_charge_total': Decimal('0'),
            'wallet_manual_charge_total': Decimal('0'),
            'wallet_transactions_count': 0,
            'wallet_charge_health': 'idle',
            'last_activity_at': None,
        }
        for tenant in tenants
    }
    trend_map = defaultdict(
        lambda: {
            'date': '',
            'vehicles_count': 0,
            'paid_amount': Decimal('0'),
            'expense_total': Decimal('0'),
            'wallet_deposit_total': Decimal('0'),
            'wallet_withdraw_total': Decimal('0'),
        }
    )

    vehicles = VehicleEntry.objects.select_related('tenant')
    if start:
        vehicles = vehicles.filter(check_in_at__gte=start)
    if end:
        vehicles = vehicles.filter(check_in_at__lte=end)

    active_statuses = {
        VehicleEntry.Status.ENTERED,
        VehicleEntry.Status.ASSIGNED,
        VehicleEntry.Status.IN_PROGRESS,
        VehicleEntry.Status.READY_TO_SETTLE,
    }
    for vehicle in vehicles:
        tenant = vehicle.tenant
        if not tenant or tenant.id not in grouped:
            continue
        row = grouped[tenant.id]
        row['vehicles_count'] += 1
        if vehicle.status == VehicleEntry.Status.RELEASED:
            row['released_count'] += 1
        if vehicle.status == VehicleEntry.Status.CANCELLED:
            row['cancelled_count'] += 1
        if vehicle.status in active_statuses:
            row['active_queue_count'] += 1
        if not row['last_activity_at'] or vehicle.check_in_at > row['last_activity_at']:
            row['last_activity_at'] = vehicle.check_in_at

        trend_key = timezone.localtime(vehicle.check_in_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        trend['vehicles_count'] += 1

    payments = Payment.objects.select_related('tenant', 'vehicle_entry')
    if start:
        payments = payments.filter(Q(paid_at__gte=start) | Q(paid_at__isnull=True, created_at__gte=start))
    if end:
        payments = payments.filter(Q(paid_at__lte=end) | Q(paid_at__isnull=True, created_at__lte=end))

    for payment in payments:
        tenant = payment.tenant or getattr(payment.vehicle_entry, 'tenant', None)
        if not tenant or tenant.id not in grouped:
            continue
        row = grouped[tenant.id]
        event_dt = payment.paid_at or payment.created_at
        amount = Decimal(str(payment.amount or 0))
        if payment.status == Payment.Status.SUCCESS:
            row['payments_count'] += 1
            row['paid_amount'] += amount
            row['tips_total'] += Decimal(str(payment.tip_amount or 0))
            row['discount_total'] += Decimal(str(payment.discount_amount or 0))
            row['services_total'] += Decimal(str(payment.service_amount or 0))
            row['products_total'] += Decimal(str(payment.product_amount or 0))
            if event_dt and (not row['last_activity_at'] or event_dt > row['last_activity_at']):
                row['last_activity_at'] = event_dt
            if event_dt:
                trend_key = timezone.localtime(event_dt).date().isoformat()
                trend = trend_map[trend_key]
                trend['date'] = trend_key
                trend['paid_amount'] += amount
        elif payment.status == Payment.Status.PENDING:
            row['pending_amount'] += amount
        elif payment.status == Payment.Status.REFUNDED:
            row['refunded_total'] += amount

    stock_movements = StockMovement.objects.select_related('tenant').filter(reference_type='manager_purchase')
    if start:
        stock_movements = stock_movements.filter(moved_at__gte=start)
    if end:
        stock_movements = stock_movements.filter(moved_at__lte=end)

    for movement in stock_movements:
        tenant = movement.tenant
        if not tenant or tenant.id not in grouped:
            continue
        cost_total = Decimal(str(movement.quantity or 0)) * Decimal(str(movement.unit_cost or 0))
        row = grouped[tenant.id]
        row['expense_total'] += cost_total
        if not row['last_activity_at'] or movement.moved_at > row['last_activity_at']:
            row['last_activity_at'] = movement.moved_at

        trend_key = timezone.localtime(movement.moved_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        trend['expense_total'] += cost_total

    wallets = Wallet.objects.filter(is_active=True).only('tenant_id', 'wallet_type', 'balance')
    for wallet in wallets:
        if not wallet.tenant_id or wallet.tenant_id not in grouped:
            continue
        row = grouped[wallet.tenant_id]
        balance = Decimal(str(wallet.balance or 0))
        row['wallet_balance'] += balance
        if wallet.wallet_type == Wallet.WalletType.SMS:
            row['wallet_sms_balance'] += balance
        else:
            row['wallet_regular_balance'] += balance

    wallet_transactions = CashflowTransaction.objects.select_related('wallet')
    if start:
        wallet_transactions = wallet_transactions.filter(transacted_at__gte=start)
    if end:
        wallet_transactions = wallet_transactions.filter(transacted_at__lte=end)

    for tx in wallet_transactions:
        tenant_id = tx.tenant_id
        if not tenant_id or tenant_id not in grouped:
            continue
        row = grouped[tenant_id]
        amount = Decimal(str(tx.amount or 0))
        row['wallet_transactions_count'] += 1
        if tx.direction == CashflowTransaction.Direction.IN:
            row['wallet_deposit_total'] += amount
            if tx.reference_type == 'wallet_gateway_deposit':
                row['wallet_gateway_charge_total'] += amount
            else:
                row['wallet_manual_charge_total'] += amount
        else:
            row['wallet_withdraw_total'] += amount
        if not row['last_activity_at'] or tx.transacted_at > row['last_activity_at']:
            row['last_activity_at'] = tx.transacted_at

        trend_key = timezone.localtime(tx.transacted_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        if tx.direction == CashflowTransaction.Direction.IN:
            trend['wallet_deposit_total'] += amount
        else:
            trend['wallet_withdraw_total'] += amount

    gateway_requests = WalletGatewayRequest.objects.filter(status=WalletGatewayRequest.Status.PAID)
    if start:
        gateway_requests = gateway_requests.filter(completed_at__gte=start)
    if end:
        gateway_requests = gateway_requests.filter(completed_at__lte=end)

    gateway_counts = defaultdict(int)
    for request in gateway_requests.only('tenant_id'):
        if request.tenant_id:
            gateway_counts[request.tenant_id] += 1

    rows = []
    for item in grouped.values():
        vehicles_count = item['vehicles_count']
        paid_amount = item['paid_amount']
        expense_total = item['expense_total']
        net_amount = paid_amount - expense_total
        average_ticket = (paid_amount / vehicles_count).quantize(Decimal('0.01')) if vehicles_count else Decimal('0')
        completion_rate = round((item['released_count'] / vehicles_count) * 100, 1) if vehicles_count else 0
        if net_amount < 0 or (paid_amount > 0 and item['pending_amount'] >= paid_amount * Decimal('0.35')):
            health = 'risk'
        elif vehicles_count and completion_rate >= 80 and net_amount > 0:
            health = 'strong'
        elif vehicles_count or paid_amount or expense_total or item['pending_amount']:
            health = 'stable'
        else:
            health = 'idle'

        item['net_amount'] = net_amount
        item['average_ticket'] = average_ticket
        item['completion_rate'] = completion_rate
        item['health'] = health
        item['wallet_gateway_charge_count'] = gateway_counts.get(item['tenant_id'], 0)
        if item['wallet_balance'] <= 0 and (item['wallet_withdraw_total'] or item['wallet_deposit_total']):
            item['wallet_charge_health'] = 'empty'
        elif item['wallet_sms_balance'] > item['wallet_regular_balance'] and item['wallet_balance'] > 0:
            item['wallet_charge_health'] = 'sms_heavy'
        elif item['wallet_gateway_charge_total'] >= item['wallet_manual_charge_total'] and item['wallet_deposit_total'] > 0:
            item['wallet_charge_health'] = 'gateway'
        elif item['wallet_balance'] > 0:
            item['wallet_charge_health'] = 'healthy'
        rows.append(item)

    rows.sort(
        key=lambda item: (
            Decimal(str(item['paid_amount'] or 0)),
            int(item['vehicles_count'] or 0),
            Decimal(str(item['net_amount'] or 0)),
        ),
        reverse=True,
    )
    for index, item in enumerate(rows, start=1):
        item['rank'] = index

    active_rows = [item for item in rows if item['vehicles_count'] or item['paid_amount'] or item['expense_total'] or item['pending_amount']]
    total_paid = sum((item['paid_amount'] for item in rows), Decimal('0'))
    total_expense = sum((item['expense_total'] for item in rows), Decimal('0'))
    total_net = sum((item['net_amount'] for item in rows), Decimal('0'))
    total_pending = sum((item['pending_amount'] for item in rows), Decimal('0'))
    total_wallet_balance = sum((item['wallet_balance'] for item in rows), Decimal('0'))
    total_wallet_regular = sum((item['wallet_regular_balance'] for item in rows), Decimal('0'))
    total_wallet_sms = sum((item['wallet_sms_balance'] for item in rows), Decimal('0'))
    total_wallet_deposits = sum((item['wallet_deposit_total'] for item in rows), Decimal('0'))
    total_wallet_withdraws = sum((item['wallet_withdraw_total'] for item in rows), Decimal('0'))
    total_wallet_gateway = sum((item['wallet_gateway_charge_total'] for item in rows), Decimal('0'))
    total_wallet_manual = sum((item['wallet_manual_charge_total'] for item in rows), Decimal('0'))
    total_vehicles = sum(item['vehicles_count'] for item in rows)
    total_released = sum(item['released_count'] for item in rows)
    total_cancelled = sum(item['cancelled_count'] for item in rows)

    summary = {
        'tenants_count': len(rows),
        'active_tenants_count': len(active_rows),
        'vehicles_count': total_vehicles,
        'released_count': total_released,
        'cancelled_count': total_cancelled,
        'paid_amount': total_paid,
        'expense_total': total_expense,
        'net_total': total_net,
        'pending_amount': total_pending,
        'payments_count': sum(item['payments_count'] for item in rows),
        'tips_total': sum((item['tips_total'] for item in rows), Decimal('0')),
        'discount_total': sum((item['discount_total'] for item in rows), Decimal('0')),
        'services_total': sum((item['services_total'] for item in rows), Decimal('0')),
        'products_total': sum((item['products_total'] for item in rows), Decimal('0')),
        'average_ticket': (total_paid / total_vehicles).quantize(Decimal('0.01')) if total_vehicles else Decimal('0'),
        'completion_rate': round((total_released / total_vehicles) * 100, 1) if total_vehicles else 0,
        'collection_rate': round((float(total_paid) / float(total_paid + total_pending)) * 100, 1) if (total_paid + total_pending) > 0 else 0,
        'wallet_balance_total': total_wallet_balance,
        'wallet_regular_balance_total': total_wallet_regular,
        'wallet_sms_balance_total': total_wallet_sms,
        'wallet_deposit_total': total_wallet_deposits,
        'wallet_withdraw_total': total_wallet_withdraws,
        'wallet_gateway_charge_total': total_wallet_gateway,
        'wallet_manual_charge_total': total_wallet_manual,
        'wallet_transactions_count': sum(item['wallet_transactions_count'] for item in rows),
    }

    trends = []
    for key in sorted(trend_map.keys()):
        entry = trend_map[key]
        entry['net_amount'] = entry['paid_amount'] - entry['expense_total']
        entry['wallet_net_flow'] = entry['wallet_deposit_total'] - entry['wallet_withdraw_total']
        trends.append(entry)

    top_revenue = max(rows, key=lambda item: Decimal(str(item['paid_amount'] or 0)), default=None)
    top_volume = max(rows, key=lambda item: int(item['vehicles_count'] or 0), default=None)
    top_margin = max(rows, key=lambda item: Decimal(str(item['net_amount'] or 0)), default=None)
    top_wallet_balance = max(rows, key=lambda item: Decimal(str(item['wallet_balance'] or 0)), default=None)
    top_wallet_deposit = max(rows, key=lambda item: Decimal(str(item['wallet_deposit_total'] or 0)), default=None)
    wallet_watchlist = min(
        [item for item in rows if item['wallet_balance'] or item['wallet_deposit_total'] or item['wallet_withdraw_total']],
        key=lambda item: (Decimal(str(item['wallet_balance'] or 0)), -Decimal(str(item['wallet_withdraw_total'] or 0))),
        default=None,
    )
    watchlist = min(
        [item for item in rows if item['vehicles_count'] or item['paid_amount'] or item['expense_total'] or item['pending_amount']],
        key=lambda item: (Decimal(str(item['net_amount'] or 0)), -Decimal(str(item['pending_amount'] or 0))),
        default=None,
    )

    return {
        'summary': summary,
        'rows': rows,
        'trends': trends,
        'highlights': {
            'top_revenue': top_revenue,
            'top_volume': top_volume,
            'top_margin': top_margin,
            'top_wallet_balance': top_wallet_balance,
            'top_wallet_deposit': top_wallet_deposit,
            'wallet_watchlist': wallet_watchlist,
            'watchlist': watchlist,
        },
    }


def _percent_change(current, previous):
    current_value = Decimal(str(current or 0))
    previous_value = Decimal(str(previous or 0))
    if previous_value == 0:
        if current_value == 0:
            return 0
        return None
    return round(float(((current_value - previous_value) / previous_value) * Decimal('100')), 1)


class HqReportsView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq_admin(request)
        if forbidden:
            return forbidden

        start = _parse_dt(request.query_params.get('start'))
        end = _parse_dt(request.query_params.get('end'), end_of_day=True)
        payload = _build_hq_report_snapshot(start=start, end=end)
        payload['summary']['date_start'] = request.query_params.get('start') or ''
        payload['summary']['date_end'] = request.query_params.get('end') or ''

        if start and end and end >= start:
            previous_span = end - start
            previous_end = start - timedelta(seconds=1)
            previous_start = previous_end - previous_span
            previous_payload = _build_hq_report_snapshot(start=previous_start, end=previous_end)
            payload['summary']['revenue_change_percent'] = _percent_change(
                payload['summary']['paid_amount'],
                previous_payload['summary']['paid_amount'],
            )
            payload['summary']['vehicles_change_percent'] = _percent_change(
                payload['summary']['vehicles_count'],
                previous_payload['summary']['vehicles_count'],
            )
            payload['summary']['net_change_percent'] = _percent_change(
                payload['summary']['net_total'],
                previous_payload['summary']['net_total'],
            )
        else:
            payload['summary']['revenue_change_percent'] = None
            payload['summary']['vehicles_change_percent'] = None
            payload['summary']['net_change_percent'] = None

        return Response(payload, status=status.HTTP_200_OK)
