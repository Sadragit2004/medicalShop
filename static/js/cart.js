// Shopping Cart JavaScript Functionality
class ShoppingCartManager {
    constructor() {
        this.cartCounter = document.querySelector('.cart-counter');
        // Find the inner span that displays the actual number (the one with bg-red-500)
        this.cartCounterNumber = this.cartCounter ? this.cartCounter.querySelector('span.bg-red-500') : null;
        this.cartItemsContainer = document.querySelector('.cart .divide-y-2');
        this.cartTotalPrice = document.querySelector('.cart .font-DanaDemiBold');
        this.cartItemCount = document.querySelector('.cart h2 span');
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateCartDisplay();
    }

    bindEvents() {
        // Bind add to cart buttons (skip product detail pages - handled by ProductPageCartManager)
        document.addEventListener('click', (e) => {
            const addToCartBtn = e.target.closest('.add-to-cart-btn');
            if (addToCartBtn && !document.querySelector('#total-price')) {
                // Only handle add-to-cart buttons on non-product-detail pages
                e.preventDefault();
                const productId = addToCartBtn.dataset.productId;
                const quantity = addToCartBtn.dataset.quantity || 1;
                const detail = addToCartBtn.dataset.detail || '';
                this.addToCart(productId, quantity, detail);
            }
        });

        // Bind cart quantity update buttons (only for cart page, not product detail page)
        document.addEventListener('click', (e) => {
            // Only handle increment/decrement if it's in a cart context (has data-product-id)
            const incrementBtn = e.target.closest('.increment');
            const decrementBtn = e.target.closest('.decrement');

            if (incrementBtn) {
                const input = incrementBtn.closest('.flex')?.querySelector('input[data-product-id]');
                if (input && input.dataset.productId) {
                    e.preventDefault();
                    const currentValue = parseInt(input.value) || 1;
                    input.value = currentValue + 1;
                    this.updateCartQuantity(input.dataset.productId, currentValue + 1, input.dataset.detail, input.dataset.saleType);
                }
            }

            if (decrementBtn) {
                const input = decrementBtn.closest('.flex')?.querySelector('input[data-product-id]');
                if (input && input.dataset.productId) {
                    e.preventDefault();
                    const currentValue = parseInt(input.value) || 1;
                    if (currentValue > 1) {
                        input.value = currentValue - 1;
                        this.updateCartQuantity(input.dataset.productId, currentValue - 1, input.dataset.detail, input.dataset.saleType);
                    }
                }
            }
        });

        // Bind cart removal
        document.addEventListener('click', (e) => {
            if (e.target.closest('.remove-from-cart')) {
                e.preventDefault();
                const button = e.target.closest('.remove-from-cart');
                const productId = button.dataset.productId;
                const detail = button.dataset.detail || '';
                const saleType = button.dataset.saleType;
                this.removeFromCart(productId, detail, saleType);
            }
        });
    }

    async addToCart(productId, quantity = 1, detail = '') {
        try {
            const response = await fetch('/order/cart/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: parseInt(quantity),
                    detail: detail
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showMessage('محصول به سبد خرید اضافه شد', 'success');
                this.updateCartDisplay(data);
            } else {
                this.showMessage(data.error || 'خطا در اضافه کردن محصول', 'error');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showMessage('خطا در ارتباط با سرور', 'error');
        }
    }

    async updateCartQuantity(productId, quantity, detail = '', saleType = null) {
        try {
            const response = await fetch('/order/cart/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: parseInt(quantity),
                    detail: detail,
                    sale_type: saleType
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateCartDisplay(data);
            } else {
                this.showMessage(data.error || 'خطا در بروزرسانی تعداد', 'error');
            }
        } catch (error) {
            console.error('Error updating cart quantity:', error);
            this.showMessage('خطا در ارتباط با سرور', 'error');
        }
    }

    async removeFromCart(productId, detail = '', saleType = null) {
        try {
            const response = await fetch('/order/cart/remove/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    product_id: productId,
                    detail: detail,
                    sale_type: saleType
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showMessage('محصول از سبد خرید حذف شد', 'success');
                this.updateCartDisplay(data);
            } else {
                this.showMessage(data.error || 'خطا در حذف محصول', 'error');
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            this.showMessage('خطا در ارتباط با سرور', 'error');
        }
    }

    updateCartDisplay(data = null) {
        if (data) {
            // Update cart counter
            if (this.cartCounter && this.cartCounterNumber) {
                this.cartCounterNumber.textContent = data.cart_count;
                this.cartCounter.style.display = data.cart_count > 0 ? 'flex' : 'none';
            }

            // Update cart items count in header
            if (this.cartItemCount) {
                this.cartItemCount.textContent = `(${data.cart_count} مورد)`;
            }

            // Update total price
            if (this.cartTotalPrice && data.total_price) {
                this.cartTotalPrice.textContent = `${data.total_price.toLocaleString()} تومان`;
            }

            // Update cart items list
            if (this.cartItemsContainer && data.items) {
                this.updateCartItemsList(data.items);
            }
        } else {
            // Initial load - fetch cart data
            this.loadCartData();
        }
    }

    async loadCartData() {
        try {
            const response = await fetch('/order/cart/summary/');
            const data = await response.json();

            if (data.success) {
                this.updateCartDisplay(data);
            }
        } catch (error) {
            console.error('Error loading cart data:', error);
        }
    }

    updateCartItemsList(items) {
        if (!this.cartItemsContainer) return;

        if (items.length === 0) {
            this.cartItemsContainer.innerHTML = `
                <div class="py-8 text-center text-gray-500">
                    <svg class="w-16 h-16 mx-auto mb-4 text-gray-300">
                        <use href="#shopping-bag"></use>
                    </svg>
                    <p>سبد خرید شما خالی است</p>
                </div>
            `;
            return;
        }

        const itemsHtml = items.map(item => `
            <div class="grid grid-cols-12 gap-x-2 w-full py-4 cursor-pointer cart-item" data-product-id="${item.id}" data-detail="${item.detail}" data-sale-type="${item.sale_type || 1}">
                <!-- img -->
                <div class="col-span-4 w-24 h-20">
                    <img src="${item.image || '/static/images/placeholder.png'}" class="rounded-lg object-cover w-full h-full" alt="${item.name}">
                </div>
                <!-- detail -->
                <div class="col-span-8 flex flex-col justify-between">
                    <h2 class="font-DanaMedium line-clamp-2 text-sm">
                        ${item.name}
                    </h2>
                    <div class="flex items-center justify-between gap-x-2 mt-2">
                        <button class="w-20 flex items-center justify-between gap-x-1 rounded-lg border border-gray-200 dark:border-white/20 py-1 px-2 quantity-controls">
                            <svg class="size-4 increment text-green-600 cursor-pointer" data-product-id="${item.id}" data-detail="${item.detail}" data-sale-type="${item.sale_type || 1}">
                                <use href="#plus"></use>
                            </svg>
                            <input type="number" class="custom-input w-4 mr-2 text-sm text-center" min="1" max="20"
                                value="${item.quantity}" data-product-id="${item.id}" data-detail="${item.detail}" data-sale-type="${item.sale_type || 1}" readonly>
                            <svg class="size-4 decrement text-red-500 cursor-pointer" data-product-id="${item.id}" data-detail="${item.detail}" data-sale-type="${item.sale_type || 1}">
                                <use href="#minus"></use>
                            </svg>
                        </button>
                        <div class="flex flex-col items-end">
                            <p class="text-lg text-blue-500 dark:text-blue-400 font-DanaMedium">
                                ${item.total_price.toLocaleString()} تومان
                            </p>
                            <button class="remove-from-cart text-xs text-red-500 hover:text-red-700 mt-1" data-product-id="${item.id}" data-detail="${item.detail}" data-sale-type="${item.sale_type || 1}">
                                حذف
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        this.cartItemsContainer.innerHTML = itemsHtml;
    }

    getCSRFToken() {
        // Try to get CSRF token from cookie
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        // If not found in cookie, try to get from meta tag
        if (!csrfToken) {
            const metaToken = document.querySelector('meta[name="csrf-token"]');
            return metaToken ? metaToken.getAttribute('content') : '';
        }

        return csrfToken;
    }

    showMessage(message, type = 'info') {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 left-4 z-50 p-4 rounded-lg text-white ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize cart manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cartManager = new ShoppingCartManager();
});