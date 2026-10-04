from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.product.models import Product, Category
from apps.blog.models import BlogPost


class StaticSitemap(Sitemap):
    """URLهای عادی سایت"""
    priority = 1.0
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'main:index',    # صفحه اصلی
            'main:about',    # درباره ما
            'main:contact',  # تماس با ما
            'main:faq',      # سوالات متداول
            'main:law',      # قوانین
        ]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    """دسته‌بندی‌های محصولات"""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return Category.objects.filter(isActive=True)

    def lastmod(self, obj):
        return obj.updatedAt

    def location(self, obj):
        return reverse('product:show_by_filter', args=[obj.slug])


class ProductSitemap(Sitemap):
    """محصولات"""
    priority = 0.6
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return Product.objects.filter(isActive=True)

    def lastmod(self, obj):
        return obj.updatedAt

    def location(self, obj):
        return obj.get_absolute_url()


class BlogPostSitemap(Sitemap):
    """پست‌های بلاگ"""
    priority = 0.7
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return BlogPost.objects.filter(isActive=True, publishedAt__isnull=False)

    def lastmod(self, obj):
        return obj.updatedAt

    def location(self, obj):
        return reverse('blog:blog_detail', args=[obj.slug])


class BlogListSitemap(Sitemap):
    """لیست بلاگ"""
    priority = 0.6
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['blog_list']

    def location(self, item):
        return reverse(f'blog:{item}')