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
from django.contrib import messages

@staff_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_home') 
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


from django.contrib.sessions.backends.db import SessionStore

def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.user.is_authenticated:
        # Authenticated: use the database
        cart_item, _ = CartItem.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={'quantity': 1}
        )
    else:
        # Anonymous user: use session
        cart = request.session.get('cart', {})
        book_id_str = str(book_id)
        cart[book_id_str] = cart.get(book_id_str, 0) + 1
        request.session['cart'] = cart

    return redirect('cart_view')

from django.http import JsonResponse


from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme

@require_http_methods(["GET", "POST"])
def cart_view(request):
    cart_items = []
    total = 0
    next_url = request.POST.get('next') or request.GET.get('next')

    # Handle POST requests: update or remove items or clean up
    if request.method == 'POST':
        item_id = request.POST.get("item_id")
        quantity = request.POST.get("quantity")
        cleanup = request.POST.get("cleanup")

        # Update or remove item quantity
        if item_id is not None and quantity is not None:
            try:
                book = Book.objects.get(id=int(item_id))
                quantity = int(quantity)

                if request.user.is_authenticated:
                    if quantity > 0:
                        CartItem.objects.update_or_create(
                            user=request.user,
                            book=book,
                            defaults={'quantity': quantity}
                        )
                    else:
                        CartItem.objects.filter(user=request.user, book=book).delete()
                else:
                    cart = request.session.get('cart', {})
                    if quantity > 0:
                        cart[str(book.id)] = quantity
                    elif str(book.id) in cart:
                        del cart[str(book.id)]
                    request.session['cart'] = cart

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({'success': True})

            except Book.DoesNotExist:
                pass

        # Handle "cleanup" form (e.g. on proceed to checkout or continue shopping)
        elif cleanup:
            # Save updated cart or do nothing for now
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('cart_view')

    # Handle GET request or POST fallback
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
        total = sum(item.book.selling_price * item.quantity for item in cart_items)
    else:
        session_cart = request.session.get('cart', {})
        for book_id_str, quantity in session_cart.items():
            try:
                book = Book.objects.get(id=int(book_id_str))
                subtotal = book.selling_price * quantity
                total += subtotal
                cart_items.append(type('SessionCartItem', (), {
                    'book': book,
                    'quantity': quantity,
                    'subtotal': subtotal
                })())
            except Book.DoesNotExist:
                continue

    tax = total * Decimal("0.07")

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'tax': tax,
        'is_guest': not request.user.is_authenticated
    })


from bookstore.accounts.models import Address, PaymentCard  # update if needed

@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    if not cart_items.exists():
        return redirect('cart_view')

    # Retrieve saved address if it exists
    if hasattr(user, 'address'):
        address = user.address
        saved_address = {
            'street': address.street,
            'city': address.city,
            'state': address.state,
            'zip_code': address.zip_code,
        }
    else:
        saved_address = {}

    # Retrieve saved card info if available
    user_cards = user.cards.all()  # assuming related_name="cards"
    saved_card = user_cards[0].last4 if user_cards.exists() else None

    # Stock check
    for item in cart_items:
        if item.quantity > item.book.quantity_in_stock:
            messages.error(request, f"Not enough stock for '{item.book.title}'. Only {item.book.quantity_in_stock} left.")
            return redirect('cart_view')

    if request.method == 'POST':
        # Collect shipping info from form
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        card_last4 = request.POST.get('card_last4')

        # Save or update address
        Address.objects.update_or_create(
            user=user,
            defaults={
                'street': street,
                'city': city,
                'state': state,
                'zip_code': zip_code
            }
        )

        # Optional: Save last 4 digits to Order only (not to user model for security)
        total_before = sum(item.book.selling_price * item.quantity for item in cart_items)
        tax = total_before * Decimal("0.07")
        total_after = total_before + tax

        # Create Order
        order = Order.objects.create(
            user=user,
            shipping_address=f"{street}, {city}, {state} {zip_code}",
            payment_card_last4=card_last4,
            total_before_tax=total_before,
            total_after_tax=total_after
        )

        # Order items and stock update
        for item in cart_items:
            item.book.quantity_in_stock -= item.quantity
            item.book.save()

            OrderItem.objects.create(
                order=order,
                book=item.book,
                quantity=item.quantity,
                price_each=item.book.selling_price
            )

        cart_items.delete()
        return redirect('order_confirmation', order_id=order.order_id)

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'saved_address': saved_address,
        'saved_card': saved_card,
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

    if request.user.is_authenticated:
        # Add to DB cart
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={'quantity': 1}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        # Get updated count
        cart_count = CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    else:
        # Add to session cart
        session_cart = request.session.get('cart', {})
        book_id_str = str(book_id)
        session_cart[book_id_str] = session_cart.get(book_id_str, 0) + 1
        request.session['cart'] = session_cart

        cart_count = sum(session_cart.values())

    return JsonResponse({'success': True, 'cart_count': cart_count})



