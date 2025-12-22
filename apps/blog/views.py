from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from .models import BlogPost, BlogComment, BlogCategory


def get_latest_blogs():
    """
    دریافت ۱۰ پست آخر بلاگ برای صفحه اصلی
    """
    return BlogPost.objects.filter(
        isActive=True,
        publishedAt__isnull=False,
        publishedAt__lte=timezone.now()
    ).select_related('author', 'category').prefetch_related(
        'products', 'comments'
    ).order_by('-publishedAt')[:10]


def main_blog_section(request):
    """
    نمایش بخش مقالات در صفحه اصلی
    """
    # دریافت ۶ پست آخر بلاگ برای نمایش در صفحه اصلی
    latest_blogs = get_latest_blogs()[:6]

    context = {
        'latest_blogs': latest_blogs,
    }

    return render(request, 'blog_app/mainblog.html', context)


def blog_list(request):
    """
    لیست پست‌های بلاگ
    """
    # دریافت پارامترهای جستجو و فیلتر
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()

    # Query پایه
    blogs = BlogPost.objects.filter(
        isActive=True,
        publishedAt__isnull=False,
        publishedAt__lte=timezone.now()
    ).select_related('author', 'category').prefetch_related('products', 'comments')

    # فیلتر دسته‌بندی
    if category_slug:
        blogs = blogs.filter(category__slug=category_slug)

    # جستجو در عنوان و محتوا
    if search_query:
        blogs = blogs.filter(
            models.Q(title__icontains=search_query) |
            models.Q(content__icontains=search_query) |
            models.Q(excerpt__icontains=search_query)
        )

    # مرتب‌سازی
    blogs = blogs.order_by('-publishedAt')

    # صفحه‌بندی
    paginator = Paginator(blogs, 12)  # ۱۲ پست در هر صفحه
    page = request.GET.get('page', 1)
    blogs_page = paginator.get_page(page)

    # دسته‌بندی‌ها برای فیلتر
    categories = BlogCategory.objects.filter(isActive=True)

    context = {
        'blogs': blogs_page,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
    }

    return render(request, 'blog_app/blog_list.html', context)


def blog_detail(request, slug):
    """
    صفحه جزئیات پست بلاگ
    """
    # دریافت پست بلاگ
    blog = get_object_or_404(
        BlogPost.objects.select_related('author', 'category').prefetch_related(
            'products', 'comments__author'
        ),
        slug=slug,
        isActive=True,
        publishedAt__isnull=False,
        publishedAt__lte=timezone.now()
    )

    # افزایش تعداد بازدید
    blog.view_count += 1
    blog.save(update_fields=['view_count'])

    # کامنت‌های فعال
    comments = blog.comments.filter(isActive=True).order_by('createdAt')

    # محصولات مرتبط (در صورت وجود)
    related_products = blog.products.filter(isActive=True)[:6]

    # پست‌های مرتبط از همان دسته‌بندی
    related_blogs = BlogPost.objects.filter(
        isActive=True,
        publishedAt__isnull=False,
        publishedAt__lte=timezone.now(),
        category=blog.category
    ).exclude(id=blog.id).select_related('author').order_by('-publishedAt')[:4]

    # دسته‌بندی‌ها برای سایدبار
    categories = BlogCategory.objects.filter(isActive=True)

    context = {
        'blog': blog,
        'comments': comments,
        'related_products': related_products,
        'related_blogs': related_blogs,
        'categories': categories,
    }

    return render(request, 'blog_app/blog_detail.html', context)


@login_required
@require_POST
def add_blog_comment(request, blog_slug):
    """
    افزودن کامنت جدید به پست بلاگ
    """
    try:
        blog = get_object_or_404(BlogPost, slug=blog_slug, isActive=True)

        content = request.POST.get('content', '').strip()

        if not content:
            return JsonResponse({
                'success': False,
                'error': 'محتوای کامنت نمی‌تواند خالی باشد'
            })

        if len(content) < 10:
            return JsonResponse({
                'success': False,
                'error': 'کامنت باید حداقل ۱۰ کاراکتر باشد'
            })

        # ایجاد کامنت
        comment = BlogComment.objects.create(
            post=blog,
            author=request.user,
            content=content,
            parent=None  # کامنت‌های یک طرفه
        )

        return JsonResponse({
            'success': True,
            'message': 'کامنت با موفقیت ثبت شد',
            'comment': {
                'id': comment.id,
                'author': request.user.get_full_name() or request.user.username,
                'content': comment.content,
                'created_at': comment.createdAt.strftime('%Y/%m/%d %H:%M'),
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
