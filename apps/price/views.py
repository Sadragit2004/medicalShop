from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Q, Avg, Count
import json
from decimal import Decimal

from .models import ProductPriceHistory, ProductStockHistory
from apps.user.models.user import CustomUser
from apps.product.models import Product, ProductSaleType, Category, TypeProductTitle
from django.shortcuts import render


# توابع کمکی برای بررسی دسترسی
def is_superuser(user):
    """بررسی سوپریوزر بودن کاربر"""
    return user.is_authenticated and user.is_superuser

def is_staff_or_superuser(user):
    """بررسی staff یا superuser بودن کاربر"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_superuser)
def showUiPrice(request):
    """نمایش UI قیمت‌ها"""
    return render(request, 'price_app/price.html')


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_superuser)
def get_products_list(request):
    """دریافت لیست محصولات با قیمت‌ها - فقط سوپریوزر"""
    products = Product.objects.filter(isActive=True).prefetch_related('saleTypes', 'typetitle')

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category__id=category_id)

    search = request.GET.get('search', '')
    if search:
        products = products.filter(title__icontains=search)

    data = []
    for product in products:
        sale_types = []
        for sale in product.saleTypes.filter(isActive=True):
            sale_types.append({
                'id': sale.id,
                'typeSale': sale.typeSale,
                'typeSale_display': sale.get_typeSale_display(),
                'price': sale.price,
                'finalPrice': sale.finalPrice,
                'memberCarton': sale.memberCarton,
                'limitedSale': sale.limitedSale,
                'title': sale.title or 'پایه',
            })

        last_price = ProductPriceHistory.objects.filter(
            product=product, is_current=True
        ).first()

        product_type_title = product.typetitle.title if product.typetitle else 'فیزیکی'

        data.append({
            'id': product.id,
            'title': product.title,
            'slug': product.slug,
            'mainImage': product.mainImage.url if product.mainImage else None,
            'stock': product.stock,
            'isActive': product.isActive,
            'category': [{'id': cat.id, 'title': cat.title} for cat in product.category.all()],
            'brand': product.brand.title if product.brand else None,
            'sale_types': sale_types,
            'product_type_title': product_type_title,
            'last_price': {
                'price_old': last_price.price_old if last_price else None,
                'price_new': last_price.price_new if last_price else sale_types[0]['price'] if sale_types else 0,
                'percent_change': float(last_price.percent_change) if last_price and last_price.percent_change else 0,
            } if last_price or sale_types else None
        })

    return JsonResponse({'success': True, 'count': len(data), 'products': data})


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_product_detail(request, product_id):
    """دریافت جزئیات یک محصول - staff یا superuser"""
    try:
        product = Product.objects.get(id=product_id, isActive=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    sale_types = []
    for sale in product.saleTypes.filter(isActive=True):
        sale_types.append({
            'id': sale.id,
            'typeSale': sale.typeSale,
            'typeSale_display': sale.get_typeSale_display(),
            'price': sale.price,
            'finalPrice': sale.finalPrice,
            'memberCarton': sale.memberCarton,
            'limitedSale': sale.limitedSale,
            'title': sale.title or 'پایه',
        })

    price_history = ProductPriceHistory.objects.filter(product=product).order_by('-created_at')[:20]
    stock_history = ProductStockHistory.objects.filter(product=product).order_by('-created_at')[:10]

    history_data = []
    for hist in price_history:
        history_data.append({
            'id': hist.id,
            'price_old': hist.price_old,
            'price_new': hist.price_new,
            'percent_change': float(hist.percent_change) if hist.percent_change else 0,
            'change_type': hist.change_type,
            'created_at': hist.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'source': hist.get_source_display(),
            'note': hist.note,
        })

    stock_history_data = []
    for stock in stock_history:
        stock_history_data.append({
            'id': stock.id,
            'stock_old': stock.stock_old,
            'stock_new': stock.stock_new,
            'change_type': stock.get_change_type_display(),
            'created_at': stock.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'changed_by': stock.changed_by_name,
        })

    return JsonResponse({
        'success': True,
        'product': {
            'id': product.id,
            'title': product.title,
            'slug': product.slug,
            'mainImage': product.mainImage.url if product.mainImage else None,
            'description': product.description,
            'shortDescription': product.shortDescription,
            'stock': product.stock,
            'isActive': product.isActive,
            'sale_types': sale_types,
            'price_history': history_data,
            'stock_history': stock_history_data,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def update_product_price(request):
    """به روز رسانی قیمت محصول - فقط سوپریوزر"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

    product_id = data.get('product_id')
    sale_type_id = data.get('sale_type_id')
    new_price = data.get('price')
    source = data.get('source', 'manual_phone')
    source_detail = data.get('source_detail', '')
    note = data.get('note', '')

    if not product_id or not new_price:
        return JsonResponse({'success': False, 'error': 'product_id و price الزامی هستند'}, status=400)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    if not sale_type_id:
        sale_type = product.saleTypes.filter(isActive=True).first()
        if not sale_type:
            return JsonResponse({'success': False, 'error': 'نوع فروشی برای این محصول تعریف نشده'}, status=400)
    else:
        try:
            sale_type = ProductSaleType.objects.get(id=sale_type_id, product=product)
        except ProductSaleType.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'نوع فروش یافت نشد'}, status=404)

    old_price = sale_type.price
    new_price_int = int(new_price)

    if old_price == new_price_int:
        return JsonResponse({
            'success': True,
            'message': 'قیمت تغییری نکرده است',
            'data': {'product_id': product_id, 'old_price': old_price, 'new_price': new_price_int, 'percent_change': 0}
        })

    sale_type.price = new_price_int
    sale_type.finalPrice = new_price_int
    sale_type.updatedAt = timezone.now()
    sale_type.save()

    ProductPriceHistory.objects.filter(product=product, sale_type=sale_type, is_current=True).update(is_current=False)

    percent_change = round(((new_price_int - old_price) / old_price) * 100, 2) if old_price > 0 else 0
    change_type = 'increase' if new_price_int > old_price else 'decrease'

    user = request.user
    user_name = str(user.mobileNumber) or user.username

    price_history = ProductPriceHistory.objects.create(
        product=product, sale_type=sale_type,
        price_old=old_price, price_new=new_price_int,
        percent_change=Decimal(str(percent_change)), change_type=change_type,
        changed_by=user, changed_by_name=user_name,
        source=source, source_detail=source_detail, note=note,
        is_current=True, created_at=timezone.now()
    )

    return JsonResponse({
        'success': True, 'message': 'قیمت با موفقیت به روز شد',
        'data': {
            'id': price_history.id, 'product_id': product_id, 'product_title': product.title,
            'sale_type_id': sale_type.id, 'old_price': old_price, 'new_price': new_price_int,
            'percent_change': float(percent_change), 'change_type': change_type,
            'created_at': price_history.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def toggle_product_with_stock_management(request, product_id):
    """
    مدیریت دکمه خاموش/روشن - فقط موجودی را مدیریت می‌کند:
    - اگر موجودی > 0: موجودی را ذخیره و صفر می‌کند (خاموش)
    - اگر موجودی == 0: آخرین موجودی ذخیره شده را بازیابی می‌کند (روشن)

    isActive محصول هرگز تغییر نمی‌کند - دست نمی‌زنیم بهش
    """
    try:
        product = Product.objects.get(id=product_id)
        old_stock = product.stock
        user = request.user
        user_name = str(user.mobileNumber) or user.username

        if old_stock > 0:
            # ====== خاموش کردن (موجودی را صفر کن) ======
            ProductStockHistory.objects.create(
                product=product,
                stock_old=old_stock,
                stock_new=0,
                change_type='stock_off',
                saved_stock_before_disable=old_stock,
                changed_by=user,
                changed_by_name=user_name,
                note=f"موجودی از {old_stock} به صفر تنظیم شد."
            )

            product.stock = 0
            product.save()

            return JsonResponse({
                'success': True,
                'product_id': product_id,
                'isActive': product.isActive,
                'stock': 0,
                'old_stock': old_stock,
                'message': f"موجودی به صفر رسید"
            })

        else:
            # ====== روشن کردن (موجودی را بازیابی کن) ======
            last_record = ProductStockHistory.objects.filter(
                product=product,
                change_type='stock_off',
                saved_stock_before_disable__isnull=False,
                saved_stock_before_disable__gt=0
            ).order_by('-created_at').first()

            restored_stock = last_record.saved_stock_before_disable if last_record else 1

            ProductStockHistory.objects.create(
                product=product,
                stock_old=old_stock,
                stock_new=restored_stock,
                change_type='stock_on',
                saved_stock_before_disable=None,
                changed_by=user,
                changed_by_name=user_name,
                note=f"موجودی از {old_stock} به {restored_stock} بازیابی شد"
            )

            product.stock = restored_stock
            product.save()

            return JsonResponse({
                'success': True,
                'product_id': product_id,
                'isActive': product.isActive,
                'stock': restored_stock,
                'old_stock': old_stock,
                'restored_from': restored_stock,
                'message': f"موجودی به {restored_stock} بازگشت"
            })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def set_product_stock_to_zero(request, product_id):
    """تنظیم موجودی محصول به صفر بدون تغییر وضعیت فعال/غیرفعال - فقط سوپریوزر"""
    try:
        product = Product.objects.get(id=product_id)
        old_stock = product.stock

        if old_stock == 0:
            return JsonResponse({
                'success': True,
                'message': 'موجودی محصول در حال حاضر صفر است',
                'product_id': product_id,
                'stock': product.stock,
                'isActive': product.isActive
            })

        user = request.user
        user_name = str(user.mobileNumber) or user.username

        ProductStockHistory.objects.create(
            product=product,
            stock_old=old_stock,
            stock_new=0,
            change_type='set_to_zero',
            saved_stock_before_disable=old_stock,
            changed_by=user,
            changed_by_name=user_name,
            note=f"موجودی از {old_stock} به صفر تنظیم شد. محصول فعال باقی ماند."
        )

        product.stock = 0
        product.save()

        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'isActive': product.isActive,
            'stock': product.stock,
            'old_stock': old_stock,
            'message': f"موجودی محصول با موفقیت به صفر رسید"
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def restore_product_stock(request, product_id):
    """بازیابی موجودی محصول از آخرین مقدار ذخیره شده - فقط سوپریوزر"""
    try:
        product = Product.objects.get(id=product_id)
        old_stock = product.stock

        last_zero_record = ProductStockHistory.objects.filter(
            product=product,
            change_type='set_to_zero',
            saved_stock_before_disable__isnull=False,
            saved_stock_before_disable__gt=0
        ).order_by('-created_at').first()

        if not last_zero_record:
            return JsonResponse({
                'success': False,
                'error': 'هیچ موجودی قبلی برای بازیابی یافت نشد'
            }, status=400)

        restored_stock = last_zero_record.saved_stock_before_disable

        user = request.user
        user_name = str(user.mobileNumber) or user.username

        ProductStockHistory.objects.create(
            product=product,
            stock_old=old_stock,
            stock_new=restored_stock,
            change_type='restore_stock',
            saved_stock_before_disable=None,
            changed_by=user,
            changed_by_name=user_name,
            note=f"موجودی از {old_stock} به {restored_stock} بازیابی شد"
        )

        product.stock = restored_stock
        product.save()

        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'isActive': product.isActive,
            'stock': product.stock,
            'old_stock': old_stock,
            'restored_from': restored_stock,
            'message': f"موجودی محصول با موفقیت به {restored_stock} بازیابی شد"
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def update_product_stock(request, product_id):
    """به روز رسانی موجودی محصول با ثبت در تاریخچه - فقط سوپریوزر"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

    new_stock = data.get('stock')
    change_type = data.get('change_type', 'manual')
    note = data.get('note', '')

    if new_stock is None:
        return JsonResponse({'success': False, 'error': 'مقدار stock الزامی است'}, status=400)

    try:
        product = Product.objects.get(id=product_id)
        old_stock = product.stock

        if old_stock == int(new_stock):
            return JsonResponse({'success': True, 'message': 'موجودی تغییری نکرده است'})

        user = request.user
        user_name = str(user.mobileNumber) or user.username

        ProductStockHistory.objects.create(
            product=product,
            stock_old=old_stock,
            stock_new=int(new_stock),
            change_type=change_type,
            saved_stock_before_disable=None,
            changed_by=user,
            changed_by_name=user_name,
            note=note
        )

        product.stock = int(new_stock)
        product.save()

        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'product_title': product.title,
            'old_stock': old_stock,
            'new_stock': product.stock,
            'message': 'موجودی با موفقیت به روز شد'
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_product_stock_history(request, product_id):
    """دریافت تاریخچه موجودی محصول - staff یا superuser"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    limit = int(request.GET.get('limit', 20))
    stock_history = ProductStockHistory.objects.filter(product=product).order_by('-created_at')[:limit]

    history_data = []
    for hist in stock_history:
        history_data.append({
            'id': hist.id,
            'stock_old': hist.stock_old,
            'stock_new': hist.stock_new,
            'saved_stock_before_disable': hist.saved_stock_before_disable,
            'change_type': hist.change_type,
            'change_type_display': hist.get_change_type_display(),
            'changed_by': hist.changed_by_name,
            'note': hist.note,
            'created_at': hist.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({
        'success': True,
        'product_id': product_id,
        'product_title': product.title,
        'current_stock': product.stock,
        'isActive': product.isActive,
        'history': history_data,
        'count': len(history_data)
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_price_history(request, product_id):
    """دریافت تاریخچه قیمت یک محصول - staff یا superuser"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    limit = int(request.GET.get('limit', 30))
    sale_type_id = request.GET.get('sale_type_id')

    query = ProductPriceHistory.objects.filter(product=product)
    if sale_type_id:
        query = query.filter(sale_type_id=sale_type_id)
    query = query.order_by('-created_at')[:limit]

    history_data = []
    for hist in query:
        history_data.append({
            'id': hist.id,
            'price_old': hist.price_old,
            'price_new': hist.price_new,
            'percent_change': float(hist.percent_change) if hist.percent_change else 0,
            'change_type': hist.change_type,
            'change_type_display': hist.get_change_type_display(),
            'source': hist.get_source_display(),
            'source_detail': hist.source_detail,
            'changed_by': hist.changed_by_name,
            'note': hist.note,
            'created_at': hist.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })

    stats = {
        'total_changes': ProductPriceHistory.objects.filter(product=product).count(),
        'last_change': history_data[0]['created_at'] if history_data else None,
        'avg_percent_change': 0,
        'increase_count': ProductPriceHistory.objects.filter(product=product, change_type='increase').count(),
        'decrease_count': ProductPriceHistory.objects.filter(product=product, change_type='decrease').count(),
    }

    avg_result = ProductPriceHistory.objects.filter(product=product, percent_change__isnull=False).aggregate(avg=models.Avg('percent_change'))
    stats['avg_percent_change'] = float(avg_result['avg'] or 0)

    return JsonResponse({
        'success': True,
        'product_id': product_id,
        'product_title': product.title,
        'stats': stats,
        'history': history_data,
        'count': len(history_data)
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_superuser)
def get_dashboard_stats(request):
    """دریافت آمار داشبورد - فقط سوپریوزر"""
    total_products = Product.objects.filter(isActive=True).count()
    out_of_stock = Product.objects.filter(isActive=True, stock=0).count()

    today = timezone.now().date()
    today_changes = ProductPriceHistory.objects.filter(created_at__date=today).count()

    avg_change_today = ProductPriceHistory.objects.filter(
        created_at__date=today, percent_change__isnull=False
    ).aggregate(avg=Avg('percent_change'))

    biggest_increase = ProductPriceHistory.objects.filter(
        created_at__date=today, change_type='increase'
    ).order_by('-percent_change').first()

    biggest_decrease = ProductPriceHistory.objects.filter(
        created_at__date=today, change_type='decrease'
    ).order_by('percent_change').first()

    latest_changes = ProductPriceHistory.objects.all().order_by('-created_at')[:10]
    latest_data = []
    for change in latest_changes:
        latest_data.append({
            'id': change.id,
            'product_title': change.product.title,
            'old_price': change.price_old,
            'new_price': change.price_new,
            'percent_change': float(change.percent_change) if change.percent_change else 0,
            'change_type': change.change_type,
            'created_at': change.created_at.strftime('%H:%M %Y/%m/%d'),
            'source': change.get_source_display(),
        })

    categories = []
    for cat in Category.objects.filter(isActive=True, parent__isnull=True):
        product_count = Product.objects.filter(category=cat, isActive=True).count()
        if product_count > 0:
            categories.append({
                'id': cat.id,
                'title': cat.title,
                'product_count': product_count,
                'parent': None,
            })

    return JsonResponse({
        'success': True,
        'stats': {
            'total_products': total_products,
            'out_of_stock': out_of_stock,
            'today_changes': today_changes,
            'avg_change_today': float(avg_change_today['avg'] or 0),
            'biggest_increase': {
                'product': biggest_increase.product.title if biggest_increase else None,
                'percent': float(biggest_increase.percent_change) if biggest_increase else 0,
            } if biggest_increase else None,
            'biggest_decrease': {
                'product': biggest_decrease.product.title if biggest_decrease else None,
                'percent': float(biggest_decrease.percent_change) if biggest_decrease else 0,
            } if biggest_decrease else None,
        },
        'latest_changes': latest_data,
        'categories': categories
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_categories_with_stats(request):
    """دریافت دسته بندی‌های سطح دو - staff یا superuser"""
    categories = Category.objects.filter(isActive=True, parent__isnull=False)

    data = []
    for cat in categories:
        product_count = Product.objects.filter(category=cat, isActive=True).count()

        parent_info = None
        if cat.parent:
            parent_info = {
                'id': cat.parent.id,
                'title': cat.parent.title
            }

        data.append({
            'id': cat.id,
            'title': cat.title,
            'parent': parent_info,
            'image': cat.image.url if cat.image else None,
            'product_count': product_count,
        })

    return JsonResponse({'success': True, 'categories': data})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def bulk_update_prices(request):
    """به روز رسانی چند قیمت همزمان - فقط سوپریوزر"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

    updates = data.get('updates', [])
    if not updates:
        return JsonResponse({'success': False, 'error': 'لیست به‌روزرسانی خالی است'}, status=400)

    results = []
    errors = []

    for update in updates:
        product_id = update.get('product_id')
        new_price = update.get('price')
        sale_type_id = update.get('sale_type_id')

        try:
            product = Product.objects.get(id=product_id)

            if not sale_type_id:
                sale_type = product.saleTypes.filter(isActive=True).first()
            else:
                sale_type = ProductSaleType.objects.get(id=sale_type_id, product=product)

            if not sale_type:
                errors.append({'product_id': product_id, 'error': 'نوع فروش یافت نشد'})
                continue

            old_price = sale_type.price
            new_price_int = int(new_price)

            if old_price == new_price_int:
                results.append({'product_id': product_id, 'status': 'skipped', 'message': 'قیمت تغییری نکرد'})
                continue

            sale_type.price = new_price_int
            sale_type.finalPrice = new_price_int
            sale_type.updatedAt = timezone.now()
            sale_type.save()

            ProductPriceHistory.objects.filter(product=product, sale_type=sale_type, is_current=True).update(is_current=False)

            percent_change = round(((new_price_int - old_price) / old_price) * 100, 2) if old_price > 0 else 0
            change_type = 'increase' if new_price_int > old_price else 'decrease'

            user = request.user
            user_name = str(user.mobileNumber) or user.username

            price_history = ProductPriceHistory.objects.create(
                product=product, sale_type=sale_type,
                price_old=old_price, price_new=new_price_int,
                percent_change=Decimal(str(percent_change)), change_type=change_type,
                changed_by=user, changed_by_name=user_name, source='manual_excel',
                is_current=True, created_at=timezone.now()
            )

            results.append({
                'product_id': product_id, 'product_title': product.title, 'status': 'success',
                'old_price': old_price, 'new_price': new_price_int,
                'percent_change': float(percent_change), 'history_id': price_history.id
            })

        except Product.DoesNotExist:
            errors.append({'product_id': product_id, 'error': 'محصول یافت نشد'})
        except Exception as e:
            errors.append({'product_id': product_id, 'error': str(e)})

    return JsonResponse({
        'success': True,
        'total': len(updates),
        'success_count': len([r for r in results if r.get('status') == 'success']),
        'results': results,
        'errors': errors
    })