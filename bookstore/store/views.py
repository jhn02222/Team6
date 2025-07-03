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
    cart_items = CartItem.objects.select_related('book').filter(user=request.user)

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        try:
            item = CartItem.objects.get(id=item_id, user=request.user)
            if quantity > 0:
                item.quantity = quantity
                item.save()
                total_price = item.quantity * item.book.selling_price
                cart_total = sum(ci.book.selling_price * ci.quantity for ci in cart_items)
                return JsonResponse({
                    'success': True,
                    'item_total': round(total_price, 2),
                    'cart_total': round(cart_total, 2),
                })
            else:
                item.delete()
                cart_total = sum(ci.book.selling_price * ci.quantity for ci in CartItem.objects.filter(user=request.user))
                return JsonResponse({'success': True, 'deleted': True, 'cart_total': round(cart_total, 2)})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)

    total = sum(item.book.selling_price * item.quantity for item in cart_items)
    tax = total * Decimal(0.07)
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'tax': tax + total,
    })

@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items:
        return redirect('cart_view')

    # Assume user.profile has card_last4 and shipping_address fields (adjust as needed)
    saved_card = user.card_number[-4:] if user.card_number else None
    saved_address = user.shipping_address
    if request.method == 'POST':
        address = request.POST.get('address')
        card_last4 = request.POST.get('card_last4')
        user.shipping_address = address
        user.card_number = card_last4  # or use a separate field if you have one for last 4 digits
        user.save()

        total_before = sum(item.book.selling_price * item.quantity for item in cart_items)
        tax = total_before * Decimal('0.07')
        total_after = total_before + tax

        order = Order.objects.create(
            user=user,
            shipping_address=address,
            payment_card_last4=card_last4,
            total_before_tax=total_before,
            total_after_tax=total_after
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                book=item.book,
                quantity=item.quantity,
                price_each=item.book.selling_price
            )
        cart_items.delete()
        # TODO: send confirmation email here
        return redirect('order_confirmation', order_id=order.id)

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'saved_card': saved_card,
        'saved_address': saved_address,
    })
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.select_related('book')
    return render(request, 'store/order_confirmation.html', {
        'order': order,
        'order_items': order_items,
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

