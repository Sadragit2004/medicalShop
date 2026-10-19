
import json
import re

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.views.decorators.http import require_POST

from .models import BlogPost, BlogComment, BlogCategory


def _plain_text(value):
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        strip_tags(str(value)),
    ).strip()


def _blog_meta_description(blog):
    description = (
        _plain_text(blog.meta_description)
        or _plain_text(blog.description)
        or _plain_text(blog.content)
    )

    return Truncator(description).chars(160)


def _absolute_url(request, path):
    return request.build_absolute_uri(path)


def _blog_seo_context(request, blog):
    canonical_url = _absolute_url(
        request,
        blog.get_absolute_url()
        if hasattr(blog, "get_absolute_url")
        else request.path,
    )

    seo_title = (
        (blog.meta_title or "").strip()
        or blog.title
    )

    seo_description = _blog_meta_description(blog)

    seo_image = (
        _absolute_url(request, blog.mainImage.url)
        if blog.mainImage
        else ""
    )

    author = blog.author

    author_name = (
        getattr(author, "full_name", "")
        or author.get_full_name()
        or getattr(author, "name", "")
        or getattr(author, "username", "")
        or "تیم تحریریه"
    )

    published_at = blog.publishedAt or blog.createdAt
    modified_at = blog.updatedAt or published_at

    breadcrumb_items = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "صفحه اصلی",
            "item": _absolute_url(request, "/"),
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "مقالات",
            "item": _absolute_url(request, "/blog/"),
        },
    ]

    if blog.category:
        breadcrumb_items.append({
            "@type": "ListItem",
            "position": len(breadcrumb_items) + 1,
            "name": blog.category.title,
            "item": _absolute_url(
                request,
                f"/blog/?category={blog.category.slug}",
            ),
        })

    breadcrumb_items.append({
        "@type": "ListItem",
        "position": len(breadcrumb_items) + 1,
        "name": blog.title,
        "item": canonical_url,
    })

    article_schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "@id": f"{canonical_url}#article",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": canonical_url,
        },
        "headline": blog.title,
        "name": seo_title,
        "description": seo_description,
        "datePublished": published_at.isoformat(),
        "dateModified": modified_at.isoformat(),
        "author": {
            "@type": "Person",
            "name": author_name,
        },
        "publisher": {
            "@type": "Organization",
            "name": request.get_host().split(":")[0],
        },
        "inLanguage": "fa-IR",
    }

    if seo_image:
        article_schema["image"] = [seo_image]

    if blog.category:
        article_schema["articleSection"] = blog.category.title

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "@id": f"{canonical_url}#breadcrumb",
        "itemListElement": breadcrumb_items,
    }

    schemas = [
        article_schema,
        breadcrumb_schema,
    ]

    return {
        "seo_title": seo_title,
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "seo_image": seo_image,
        "seo_author": author_name,
        "seo_published_at": published_at,
        "seo_modified_at": modified_at,
        "json_ld": json.dumps(
            schemas,
            ensure_ascii=False,
            separators=(",", ":"),
        ).replace("<", "\\u003c"),
    }


def _published_blogs():
    return BlogPost.objects.filter(
        isActive=True,
        publishedAt__isnull=False,
        publishedAt__lte=timezone.now(),
    )


def get_latest_blogs():
    return (
        _published_blogs()
        .select_related("author", "category")
        .prefetch_related("products")
        .order_by("-publishedAt", "-id")[:10]
    )


def main_blog_section(request):
    return render(
        request,
        "blog_app/mainblog.html",
        {
            "latest_blogs": get_latest_blogs()[:6],
        },
    )


def blog_list(request):
    category_slug = request.GET.get(
        "category", ""
    ).strip()

    search_query = request.GET.get(
        "q", ""
    ).strip()

    blogs = _published_blogs().select_related(
        "author",
        "category",
    )

    if category_slug:
        blogs = blogs.filter(
            category__slug=category_slug,
        )

    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(meta_description__icontains=search_query)
        )

    paginator = Paginator(
        blogs.order_by("-publishedAt", "-id"),
        12,
    )

    blogs_page = paginator.get_page(
        request.GET.get("page", 1),
    )

    categories = (
        BlogCategory.objects.filter(isActive=True)
        .annotate(
            published_post_count=Count(
                "posts",
                filter=Q(
                    posts__isActive=True,
                    posts__publishedAt__isnull=False,
                    posts__publishedAt__lte=timezone.now(),
                ),
            ),
        )
        .order_by("title")
    )

    return render(
        request,
        "blog_app/blog_list.html",
        {
            "blogs": blogs_page,
            "categories": categories,
            "selected_category": category_slug,
            "search_query": search_query,
        },
    )


def blog_detail(request, slug):
    blog = get_object_or_404(
        _published_blogs()
        .select_related("author", "category")
        .prefetch_related("products"),
        slug=slug,
    )

    BlogPost.objects.filter(
        pk=blog.pk,
    ).update(
        view_count=F("view_count") + 1,
    )

    blog.refresh_from_db(
        fields=["view_count"],
    )

    comments = (
        blog.comments.filter(isActive=True)
        .select_related("author")
        .order_by("createdAt")
    )

    related_products = blog.products.filter(
        isActive=True,
    )[:6]

    if blog.category_id:
        related_blogs = (
            _published_blogs()
            .filter(category_id=blog.category_id)
            .exclude(pk=blog.pk)
            .select_related("author", "category")
            .order_by("-publishedAt", "-id")[:4]
        )
    else:
        related_blogs = BlogPost.objects.none()

    categories = (
        BlogCategory.objects.filter(isActive=True)
        .annotate(
            published_post_count=Count(
                "posts",
                filter=Q(
                    posts__isActive=True,
                    posts__publishedAt__isnull=False,
                    posts__publishedAt__lte=timezone.now(),
                ),
            ),
        )
        .order_by("title")
    )

    context = {
        "blog": blog,
        "comments": comments,
        "related_products": related_products,
        "related_blogs": related_blogs,
        "categories": categories,
        **_blog_seo_context(request, blog),
    }

    return render(
        request,
        "blog_app/blog_detail.html",
        context,
    )


@login_required
@require_POST
def add_blog_comment(request, blog_slug):
    blog = get_object_or_404(
        _published_blogs(),
        slug=blog_slug,
    )

    content = request.POST.get(
        "content", ""
    ).strip()

    if not content:
        return JsonResponse(
            {
                "success": False,
                "error": "محتوای کامنت نمی‌تواند خالی باشد",
            },
            status=400,
        )

    if len(content) < 10:
        return JsonResponse(
            {
                "success": False,
                "error": "کامنت باید حداقل ۱۰ کاراکتر باشد",
            },
            status=400,
        )

    comment = BlogComment.objects.create(
        post=blog,
        author=request.user,
        content=content,
    )

    author_name = (
        request.user.get_full_name()
        or getattr(request.user, "name", "")
        or request.user.username
    )

    return JsonResponse(
        {
            "success": True,
            "message": "کامنت با موفقیت ثبت شد",
            "comment": {
                "id": comment.pk,
                "author": author_name,
                "content": comment.content,
                "created_at": comment.createdAt.strftime(
                    "%Y/%m/%d %H:%M"
                ),
            },
        },
        status=201,
    )
