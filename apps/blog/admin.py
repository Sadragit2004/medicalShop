from django.contrib import admin
from .models import BlogCategory, BlogPost, BlogComment


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'isActive', 'createdAt']
    list_filter = ['isActive', 'createdAt']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'isActive', 'publishedAt', 'view_count', 'createdAt']
    list_filter = ['isActive', 'publishedAt', 'category', 'author', 'createdAt']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author', 'products']
    filter_horizontal = ['products']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'category')


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'createdAt', 'isActive']
    list_filter = ['isActive', 'createdAt', 'author']
    search_fields = ['content', 'post__title', 'author__username']
    raw_id_fields = ['post', 'author', 'parent']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('post', 'author', 'parent')
