from django.shortcuts import render, get_object_or_404
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from ..models.product import Product
from ..models.category import ProductCategory
from ..models.brand import Brand
from django.utils import timezone
from datetime import timedelta
from django.db import models

class NewArrivalsView(View):
    """
    تازه‌ترین محصولات
    - ساده، بدون فیلتر اضافی
    - فقط جدیدترین محصولات
    """
    template_name = 'product_app/product/new_arrivals.html'

    def get(self, request):
        # تعداد روز پیش‌فرض
        days = 30

        # تاریخ شروع
        start_date = timezone.now() - timedelta(days=days)

        # ابتدا productgallery را import کنیم
        from ..models.gallery import ProductGallery

        # محصولات جدید (آخرین ۳۰ روز) - با prefetch صحیح
        new_products = Product.objects.filter(
            is_active=True,
            created_at__gte=start_date
        ).prefetch_related(
            models.Prefetch(
                'gallery_images',
                queryset=ProductGallery.objects.filter(is_active=True)
                .order_by('sort_order')
            )
        ).select_related(
            'brand'
        ).order_by('-created_at')[:20]

        # عنوان صفحه
        if days == 30:
            title = "تازه‌ترین محصولات (آخرین ۳۰ روز)"
        else:
            title = f"تازه‌ترین محصولات (آخرین {days} روز)"

        context = {
            'products': new_products,
            'total_products': new_products.count(),
            'days': days,
            'title': title,
            'meta_description': 'جدیدترین محصولات اضافه شده به فروشگاه',
        }

        return render(request, self.template_name, context)

# product_app/views/product_detail.py
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count
from ..models.product import Product
from ..models.comment import ProductComment


class ProductDetailView(View):
    """
    صفحه جزئیات محصول
    """
    template_name = 'product_app/product/product_detail.html'

    def get(self, request, slug):
        try:
            # دریافت محصول
            product = Product.objects.select_related('brand').get(
                slug=slug,
                is_active=True
            )
        except Product.DoesNotExist:
            return render(request, '404.html', status=404)

        # افزایش تعداد بازدید (در صورت نیاز)
        # product.increment_views()

        # اطلاعات محصول
        product_data = product.to_dict(include_related=True)

        # تصاویر گالری
        gallery_images = product.get_gallery_images()

        # ویژگی‌های محصول
        attributes = product.get_attributes(group_by_category=True)

        # محصولات مرتبط
        related_products = product.get_related_products(limit=8)

        # مسیر ناوبری
        breadcrumbs = product.get_breadcrumbs()

        # بررسی موجودی
        stock_available, stock_message = product.check_stock()

        # اطلاعات فروش عمده
        wholesale_info = None
        if product.is_wholesale_enabled:
            wholesale_info = {
                'min_quantity': product.wholesale_min_quantity,
                'discount_percent': product.wholesale_discount_percent,
            }

        # دریافت نظرات تأیید شده
        comments = ProductComment.objects.get_for_product(
            product_id=product.id,
            only_approved=True
        )

        # آمار نظرات
        comment_stats = ProductComment.objects.get_average_rating(product)

        # توزیع امتیازها
        rating_distribution = ProductComment.objects.filter(
            product=product,
            is_approved=True,
            is_active=True
        ).values('rating').annotate(
            count=Count('id')
        ).order_by('-rating')

        # فرمت کردن توزیع امتیاز
        rating_distribution_formatted = {}
        for i in range(1, 6):
            rating_distribution_formatted[i] = 0

        for item in rating_distribution:
            rating_distribution_formatted[item['rating']] = item['count']

        # اگر کاربر لاگین کرده، بررسی کن که آیا برای این محصول نظر داده یا نه
        user_has_commented = False
        if request.user.is_authenticated:
            user_has_commented = ProductComment.objects.filter(
                product=product,
                user=request.user,
                is_active=True
            ).exists()

        context = {
            # اطلاعات اصلی
            'product': product,
            'product_data': product_data,

            # گالری و ویژگی‌ها
            'gallery_images': gallery_images,
            'attributes': attributes,

            # محصولات مرتبط
            'related_products': related_products,

            # ناوبری
            'breadcrumbs': breadcrumbs,

            # موجودی و قیمت
            'stock_available': stock_available,
            'stock_message': stock_message,
            'wholesale_info': wholesale_info,
            'packaging_info': {
                'is_packaged': product.is_packaged,
                'items_per_package': product.items_per_package,
            },

            # نظرات
            'comments': comments,
            'comment_stats': comment_stats,
            'rating_distribution': rating_distribution_formatted,
            'user_has_commented': user_has_commented,
            'is_authenticated': request.user.is_authenticated,

            # SEO
            'title': product.get_seo_title(),
            'meta_description': product.get_seo_description(),
            'canonical_url': request.build_absolute_uri(),
        }

        return render(request, self.template_name, context)


class AddCommentView(View):
    """
    افزودن نظر جدید
    """
    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'محصول یافت نشد.'
            }, status=404)

        # دریافت داده‌های فرم
        content = request.POST.get('content', '').strip()
        rating = request.POST.get('rating', 5)

        # اعتبارسنجی
        if not content:
            return JsonResponse({
                'success': False,
                'message': 'لطفا متن نظر را وارد کنید.'
            })

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            rating = 5

        # ایجاد نظر
        try:
            comment = ProductComment.objects.create_comment(
                product=product,
                user=request.user,
                content=content,
                rating=rating
            )

            # اگر نیاز به تأیید دستی نیست
            # comment.approve()

            messages.success(
                request,
                'نظر شما با موفقیت ثبت شد. پس از تأیید نمایش داده می‌شود.'
            )

            return JsonResponse({
                'success': True,
                'message': 'نظر شما با موفقیت ثبت شد.',
                'comment_id': comment.id
            })

        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'خطایی در ثبت نظر رخ داده است.'
            })


class CommentListView(View):
    """
    لیست نظرات محصول (برای AJAX)
    """
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'محصول یافت نشد.'
            }, status=404)

        # دریافت پارامترها
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        offset = (page - 1) * per_page

        # دریافت نظرات
        comments = ProductComment.objects.get_for_product(
            product_id=product.id,
            only_approved=True
        )[offset:offset + per_page]

        # فرمت کردن نظرات
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'user': {
                    'display_name': comment.get_user_display_name(),
                    'avatar': comment.get_user_avatar(),
                },
                'content': comment.content,
                'rating': comment.rating,
                'rating_stars': comment.get_rating_stars(),
                'formatted_date': comment.get_formatted_date(),
                'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        # بررسی وجود صفحه بعدی
        has_next = ProductComment.objects.get_for_product(
            product_id=product.id,
            only_approved=True
        )[offset + per_page:offset + per_page + 1].exists()

        return JsonResponse({
            'success': True,
            'comments': comments_data,
            'has_next': has_next,
            'current_page': page
        })