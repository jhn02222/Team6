from django.shortcuts import render, redirect
from .forms import BookForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from bookstore.utils import custom_login_required, staff_required
from datetime import date
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Book, CartItem, Order, OrderItem
from django.views.decorators.http import require_POST
from django.db.models import Sum
from decimal import Decimal

@staff_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin') 
    else:
        form = BookForm()
    return render(request, 'admin/add_book.html', {'form': form})

def home_view(request):
    # Redirect admins to admin dashboard
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('admin')

    featured_books = Book.objects.filter(is_featured=True)[:10]
    coming_soon_books = Book.objects.filter(release_date__gt=date.today())[:10]
    cart_count = 0
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    return render(request, 'store/home.html', {
        'featured_books': featured_books,
        'coming_soon_books': coming_soon_books,
        'cart_count': cart_count,
    })
    
def search_books(request):
    query = request.GET.get('q', '')
    results = Book.objects.filter(
        Q(title__icontains=query) |
        Q(author__icontains=query) |
        Q(category__icontains=query)
    )
    return render(request, 'store/search_results.html', {
        'query': query,
        'results': results
    })
@staff_required
def manage_users(request):
    return HttpResponse("u Users Page (Coming Soon)")

@staff_required
def manage_promotions(request):
    return HttpResponse("Manage Promotions Page (Coming Soon)")


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'store/book_detail.html', {'book': book})


def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Always start at quantity 1
    cart_item, _ = CartItem.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'quantity': 1}
    )
    return redirect('cart_view')

from django.http import JsonResponse

@login_required
def cart_view(request):
    user = request.user

    # Handle cleanup request from "Back to Homepage" or "Proceed to Checkout"
    if request.method == 'POST' and request.POST.get('cleanup') == '1':
        CartItem.objects.filter(user=user, quantity=0).delete()
        next_url = request.POST.get('next', '/')
        return redirect(next_url)

    # Handle AJAX updates (quantity changes or removals)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 0))

        try:
            item = CartItem.objects.get(id=item_id, user=user)
            if quantity <= 0:
                item.delete()
                cart_total = sum(i.book.selling_price * i.quantity for i in CartItem.objects.filter(user=user))
                return JsonResponse({'success': True, 'deleted': True, 'cart_total': cart_total})
            elif quantity <= item.book.quantity_in_stock:
                item.quantity = quantity
                item.save()
                item_total = item.book.selling_price * item.quantity
                cart_total = sum(i.book.selling_price * i.quantity for i in CartItem.objects.filter(user=user))
                return JsonResponse({
                    'success': True,
                    'deleted': False,
                    'item_total': item_total,
                    'cart_total': cart_total
                })
            else:
                return JsonResponse({'success': False, 'error': 'Exceeds stock'})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})

    # Handle normal GET
    cart_items = CartItem.objects.filter(user=user)
    total = sum(item.book.selling_price * item.quantity for item in cart_items)
    tax = total * Decimal("0.07")

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'tax': tax,
    })
@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items.exists():
        return redirect('cart_view')

    saved_card = user.card_number[-4:] if user.card_number else None
    saved_address = user.shipping_address

    if request.method == 'POST':
        address = request.POST.get('address')
        card_last4 = request.POST.get('card_last4')

        # Update user info
        user.shipping_address = address
        user.card_number = card_last4
        user.save()

        # Calculate totals
        total_before = sum(item.book.selling_price * item.quantity for item in cart_items)
        tax = total_before * Decimal("0.07")
        total_after = total_before + tax

        order = Order.objects.create(
            user=user,
            shipping_address=address,
            payment_card_last4=card_last4,
            total_before_tax=total_before,
            total_after_tax=total_after
        )

        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                book=item.book,
                quantity=item.quantity,
                price_each=item.book.selling_price
            )

        # Clear cart
        cart_items.delete()

        # Redirect to confirmation
        return redirect('order_confirmation', order_id=order.order_id)

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'saved_card': saved_card,
        'saved_address': saved_address,
    })

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)  
    order_items = order.items.select_related('book')

    tax = order.total_after_tax - order.total_before_tax
    return render(request, 'store/order_confirmation.html', {
        'order': order,
        'order_items': order_items,
        'tax': tax
    })

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})
    
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    cart_item.delete()
    return redirect('cart_view')

from django.views.decorators.http import require_POST
from django.http import JsonResponse

@require_POST
def ajax_add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    # Get new cart count
    cart_count = CartItem.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    return JsonResponse({'success': True, 'cart_count': cart_count})


