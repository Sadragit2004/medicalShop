from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from django.db import models
from datetime import date, timedelta
from django.http import JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
import json

from .models import UniqueVisit, DailyStat, PageVisit


class UniqueVisitMiddleware:
    """
    میدلور ثبت بازدید یکتا
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # فقط برای صفحات GET و غیر از پنل ادمین و API
        if request.method == 'GET' and not request.path.startswith('/admin/') and not request.path.startswith('/api/'):
            self.record_visit(request)

        return response

    def record_visit(self, request):
        """ثبت بازدید یکتا"""
        try:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key

            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            referer = request.META.get('HTTP_REFERER', '')

            user = None
            if request.user.is_authenticated:
                user = request.user

            visit, created = UniqueVisit.objects.get_or_create(
                session_key=session_key,
                defaults={
                    'ip_address': ip_address,
                    'user': user,
                    'user_agent': user_agent,
                    'referer': referer,
                }
            )

            if not created:
                visit.last_visit = timezone.now()
                visit.visit_count += 1
                if user and not visit.user:
                    visit.user = user
                visit.save()

            PageVisit.objects.create(
                visit=visit,
                url=request.build_absolute_uri(),
                path=request.path,
                method=request.method,
            )

            self.update_daily_stats(date.today())

        except Exception as e:
            print(f"Error recording visit: {e}")

    def update_daily_stats(self, today_date):
        """به‌روزرسانی آمار روزانه"""
        today_start = timezone.make_aware(
            timezone.datetime.combine(today_date, timezone.datetime.min.time())
        )
        today_end = timezone.make_aware(
            timezone.datetime.combine(today_date, timezone.datetime.max.time())
        )

        unique_count = UniqueVisit.objects.filter(
            first_visit__date=today_date
        ).count()

        total_visits = UniqueVisit.objects.filter(
            last_visit__range=(today_start, today_end)
        ).aggregate(total=models.Sum('visit_count'))['total'] or 0

        page_views_count = PageVisit.objects.filter(
            created_at__date=today_date
        ).count()

        DailyStat.objects.update_or_create(
            date=today_date,
            defaults={
                'unique_visitors': unique_count,
                'total_visits': total_visits,
                'page_views': page_views_count,
            }
        )


# ======================== API های آمار ========================

class APIStatsMixin:
    """میکسین برای بررسی superuser در API ها"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'لطفا وارد حساب کاربری خود شوید',
                'error_code': 'unauthorized'
            }, status=401)

        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({
                'success': False,
                'error': 'دسترسی غیرمجاز. فقط ادمین می‌تواند به این بخش دسترسی داشته باشد',
                'error_code': 'forbidden'
            }, status=403)

        return super().dispatch(request, *args, **kwargs)


class GetOverviewStatsAPI(APIStatsMixin, View):
    """
    API دریافت آمار کلی
    GET /api/stats/overview/
    """
    def get(self, request):
        today = date.today()

        # آمار امروز
        today_stats = DailyStat.objects.filter(date=today).first()

        # آمار کل
        total_unique = UniqueVisit.objects.count()
        total_page_views = PageVisit.objects.count()

        # آمار هفته جاری
        week_ago = today - timedelta(days=7)
        week_stats = DailyStat.objects.filter(date__gte=week_ago).order_by('date')

        # آمار ماه جاری
        month_ago = today - timedelta(days=30)
        month_stats = DailyStat.objects.filter(date__gte=month_ago).order_by('date')

        # میانگین روزانه
        avg_daily = DailyStat.objects.aggregate(
            avg_visitors=models.Avg('unique_visitors'),
            avg_views=models.Avg('page_views')
        )

        data = {
            'success': True,
            'data': {
                'today': {
                    'unique_visitors': today_stats.unique_visitors if today_stats else 0,
                    'total_visits': today_stats.total_visits if today_stats else 0,
                    'page_views': today_stats.page_views if today_stats else 0,
                },
                'total': {
                    'unique_visitors': total_unique,
                    'page_views': total_page_views,
                },
                'weekly': [
                    {
                        'date': stat.date.strftime('%Y-%m-%d'),
                        'unique_visitors': stat.unique_visitors,
                        'total_visits': stat.total_visits,
                        'page_views': stat.page_views
                    }
                    for stat in week_stats
                ],
                'monthly': [
                    {
                        'date': stat.date.strftime('%Y-%m-%d'),
                        'unique_visitors': stat.unique_visitors,
                        'total_visits': stat.total_visits,
                        'page_views': stat.page_views
                    }
                    for stat in month_stats
                ],
                'averages': {
                    'daily_unique_visitors': round(avg_daily['avg_visitors'] or 0, 2),
                    'daily_page_views': round(avg_daily['avg_views'] or 0, 2),
                }
            }
        }

        return JsonResponse(data, status=200)


class GetTopPagesAPI(APIStatsMixin, View):
    """
    API دریافت پربازدیدترین صفحات
    GET /api/stats/top-pages/?limit=10
    """
    def get(self, request):
        limit = int(request.GET.get('limit', 10))

        top_pages = PageVisit.objects.values('path').annotate(
            count=models.Count('id'),
            last_visit=models.Max('created_at')
        ).order_by('-count')[:limit]

        data = {
            'success': True,
            'data': [
                {
                    'path': item['path'],
                    'visit_count': item['count'],
                    'last_visit': item['last_visit'].strftime('%Y-%m-%d %H:%M:%S') if item['last_visit'] else None
                }
                for item in top_pages
            ]
        }

        return JsonResponse(data, status=200)


class GetRecentVisitsAPI(APIStatsMixin, View):
    """
    API دریافت آخرین بازدیدها
    GET /api/stats/recent-visits/?limit=20
    """
    def get(self, request):
        limit = int(request.GET.get('limit', 20))

        recent_visits = UniqueVisit.objects.select_related('user').all()[:limit]

        data = {
            'success': True,
            'data': [
                {
                    'session_key': visit.session_key[:20] + '...',
                    'ip_address': visit.ip_address,
                    'user': {
                        'mobile': visit.user.mobileNumber if visit.user else None,
                        'name': f"{visit.user.name or ''} {visit.user.family or ''}".strip() if visit.user else None,
                    } if visit.user else None,
                    'first_visit': visit.first_visit.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_visit': visit.last_visit.strftime('%Y-%m-%d %H:%M:%S'),
                    'visit_count': visit.visit_count,
                    'user_agent': visit.user_agent[:100] + '...' if visit.user_agent and len(visit.user_agent) > 100 else visit.user_agent,
                }
                for visit in recent_visits
            ]
        }

        return JsonResponse(data, status=200)


class GetDailyStatsAPI(APIStatsMixin, View):
    """
    API دریافت آمار روزانه در بازه زمانی
    GET /api/stats/daily/?start=2024-01-01&end=2024-01-31
    """
    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        if not start_date or not end_date:
            return JsonResponse({
                'success': False,
                'error': 'پارامترهای start و end الزامی هستند',
                'error_code': 'missing_parameters'
            }, status=400)

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'فرمت تاریخ اشتباه است. فرمت صحیح: YYYY-MM-DD',
                'error_code': 'invalid_date_format'
            }, status=400)

        stats = DailyStat.objects.filter(date__gte=start, date__lte=end).order_by('date')

        data = {
            'success': True,
            'data': {
                'start_date': start_date,
                'end_date': end_date,
                'statistics': [
                    {
                        'date': stat.date.strftime('%Y-%m-%d'),
                        'unique_visitors': stat.unique_visitors,
                        'total_visits': stat.total_visits,
                        'page_views': stat.page_views
                    }
                    for stat in stats
                ],
                'summary': {
                    'total_unique_visitors': sum(stat.unique_visitors for stat in stats),
                    'total_visits': sum(stat.total_visits for stat in stats),
                    'total_page_views': sum(stat.page_views for stat in stats),
                }
            }
        }

        return JsonResponse(data, status=200)


class GetVisitorDetailsAPI(APIStatsMixin, View):
    """
    API دریافت جزئیات یک بازدیدکننده خاص
    GET /api/stats/visitor/?session_key=xxxxx
    """
    def get(self, request):
        session_key = request.GET.get('session_key')

        if not session_key:
            return JsonResponse({
                'success': False,
                'error': 'پارامتر session_key الزامی است',
                'error_code': 'missing_parameters'
            }, status=400)

        try:
            visit = UniqueVisit.objects.select_related('user').get(session_key=session_key)
            page_visits = PageVisit.objects.filter(visit=visit).order_by('-created_at')[:50]

            data = {
                'success': True,
                'data': {
                    'visitor': {
                        'session_key': visit.session_key,
                        'ip_address': visit.ip_address,
                        'user': {
                            'mobile': visit.user.mobileNumber if visit.user else None,
                            'name': f"{visit.user.name or ''} {visit.user.family or ''}".strip() if visit.user else None,
                            'email': visit.user.email if visit.user else None,
                        } if visit.user else None,
                        'first_visit': visit.first_visit.strftime('%Y-%m-%d %H:%M:%S'),
                        'last_visit': visit.last_visit.strftime('%Y-%m-%d %H:%M:%S'),
                        'visit_count': visit.visit_count,
                        'user_agent': visit.user_agent,
                        'referer': visit.referer,
                    },
                    'page_visits': [
                        {
                            'url': pv.url,
                            'path': pv.path,
                            'created_at': pv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            'status_code': pv.status_code,
                        }
                        for pv in page_visits
                    ]
                }
            }

            return JsonResponse(data, status=200)

        except UniqueVisit.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'بازدیدکننده یافت نشد',
                'error_code': 'not_found'
            }, status=404)


class GetChartDataAPI(APIStatsMixin, View):
    """
    API دریافت داده برای نمودارها
    GET /api/stats/chart/?period=week (week, month, year)
    """
    def get(self, request):
        period = request.GET.get('period', 'week')
        today = date.today()

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            return JsonResponse({
                'success': False,
                'error': 'period باید یکی از مقادیر week, month, year باشد',
                'error_code': 'invalid_period'
            }, status=400)

        stats = DailyStat.objects.filter(date__gte=start_date, date__lte=today).order_by('date')

        data = {
            'success': True,
            'data': {
                'period': period,
                'labels': [stat.date.strftime('%Y-%m-%d') for stat in stats],
                'datasets': {
                    'unique_visitors': [stat.unique_visitors for stat in stats],
                    'total_visits': [stat.total_visits for stat in stats],
                    'page_views': [stat.page_views for stat in stats],
                }
            }
        }

        return JsonResponse(data, status=200)


class ExportStatsAPI(APIStatsMixin, View):
    """
    API خروجی گرفتن از آمار (JSON)
    GET /api/stats/export/?format=json&start=2024-01-01&end=2024-01-31
    """
    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')

        if not start_date or not end_date:
            today = date.today()
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'فرمت تاریخ اشتباه است',
                'error_code': 'invalid_date_format'
            }, status=400)

        daily_stats = DailyStat.objects.filter(date__gte=start, date__lte=end).order_by('date')

        data = {
            'success': True,
            'data': {
                'export_date': date.today().isoformat(),
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'daily_stats': [
                    {
                        'date': stat.date.isoformat(),
                        'unique_visitors': stat.unique_visitors,
                        'total_visits': stat.total_visits,
                        'page_views': stat.page_views
                    }
                    for stat in daily_stats
                ],
                'summary': {
                    'total_unique_visitors': sum(stat.unique_visitors for stat in daily_stats),
                    'total_visits': sum(stat.total_visits for stat in daily_stats),
                    'total_page_views': sum(stat.page_views for stat in daily_stats),
                    'average_daily_visitors': round(sum(stat.unique_visitors for stat in daily_stats) / max(len(daily_stats), 1), 2)
                }
            }
        }

        return JsonResponse(data, status=200)


class ResetStatsAPI(APIStatsMixin, View):
    """
    API بازنشانی آمار (فقط superuser)
    POST /api/stats/reset/
    """
    def post(self, request):
        # فقط superuser واقعی میتونه این کار رو بکنه
        if not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'این عملیات فقط برای superuser مجاز است',
                'error_code': 'superuser_required'
            }, status=403)

        try:
            # حذف همه داده‌ها
            PageVisit.objects.all().delete()
            DailyStat.objects.all().delete()
            UniqueVisit.objects.all().delete()

            return JsonResponse({
                'success': True,
                'message': 'تمام آمار با موفقیت بازنشانی شد'
            }, status=200)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'error_code': 'reset_failed'
            }, status=500)