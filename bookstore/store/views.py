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
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP


@staff_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()  # This saves to database
            messages.success(request, 'Book added successfully!')
            return redirect('admin_home')  # or wherever you want to redirect
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BookForm()
    
    return render(request, 'admin/add_book.html', {'form': form})
def home_view(request):
    # Redirect admins to admin dashboard
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('admin_home')

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
def view_promotions_admin(request):
    promotions = Promotion.objects.all().order_by('-created_at')
    promo_data = []

    for promo in promotions:
        sent_users = PromotionSent.objects.filter(promotion=promo).select_related('user')
        promo_data.append({
            'promo': promo,
            'users': [ps.user for ps in sent_users],
        })

    return render(request, 'admin/view_promotions.html', {'promo_data': promo_data})


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

    tax = (total * Decimal("0.07")).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_after_tax = (total + tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'tax': tax,
        'total_after_tax': total_after_tax,
        'is_guest': not request.user.is_authenticated
    })


from bookstore.accounts.models import Address, PaymentCard  # update if needed

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import localtime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def checkout_view(request):
    user = request.user

    # Try to preload address
    try:
        saved_address = user.address
    except Address.DoesNotExist:
        saved_address = None

    if request.method == 'POST':
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')

        shipping_address = f"{street}, {city}, {state} {zip_code}"

        # Save/update address
        if saved_address:
            saved_address.street = street
            saved_address.city = city
            saved_address.state = state
            saved_address.zip_code = zip_code
            saved_address.save()
        else:
            Address.objects.create(
                user=user,
                street=street,
                city=city,
                state=state,
                zip_code=zip_code
            )

        selected_card_id = request.POST.get('selected_card')
        card_number = request.POST.get('card_number')
        card_name = request.POST.get('card_name')
        card_type = request.POST.get('card_type')
        card_expiration = request.POST.get('card_expiration')
        card_cvv = request.POST.get('card_cvv')
        card_zipcode = request.POST.get('card_zipcode')

        if selected_card_id and selected_card_id != 'new':
            try:
                card = PaymentCard.objects.get(id=selected_card_id, user=user)
                card_last4 = card.last4
            except PaymentCard.DoesNotExist:
                messages.error(request, 'Selected payment card not found.')
                return redirect('checkout')
        elif card_number:
            card_last4 = card_number[-4:]
            
            # Hash the card number to check if it already exists
            import hashlib
            card_hash = hashlib.sha256(card_number.encode()).hexdigest()

            # Check if card already exists for this user
            existing_card = PaymentCard.objects.filter(user=user, card_number_hash=card_hash).first()
            if existing_card:
                card_last4 = existing_card.last4
            else:
                # Create new card with all the provided information
                cvv_hash = hashlib.sha256(card_cvv.encode()).hexdigest() if card_cvv else None
                
                card = PaymentCard.objects.create(
                    user=user,
                    card_type=card_type,
                    name=card_name,
                    card_number_hash=card_hash,
                    last4=card_last4,
                    expiration_date=card_expiration,
                    cvv_hash=cvv_hash,
                    zipcode=card_zipcode
                )
        else:
            messages.error(request, 'Please select a payment method.')
            return redirect('checkout')

        cart_items = CartItem.objects.filter(user=user).select_related('book')
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart_view')

        # **CRITICAL: Check stock availability before processing order**
        insufficient_stock_items = []
        for item in cart_items:
            if item.quantity > item.book.quantity_in_stock:
                insufficient_stock_items.append({
                    'title': item.book.title,
                    'requested': item.quantity,
                    'available': item.book.quantity_in_stock
                })

        if insufficient_stock_items:
            error_messages = []
            for item in insufficient_stock_items:
                if item['available'] == 0:
                    error_messages.append(f"'{item['title']}' is out of stock.")
                else:
                    error_messages.append(f"'{item['title']}': Only {item['available']} available, but you have {item['requested']} in cart.")
            
            messages.error(request, "Some items in your cart are no longer available: " + " ".join(error_messages))
            return redirect('cart_view')

        # Calculate totals
        subtotal = sum(item.book.selling_price * item.quantity for item in cart_items)
        
        # Apply promo code discount if exists
        promo_code = request.session.get('promo_code')
        discounted_total = request.session.get('discounted_total')
        
        if promo_code and discounted_total:
            total_after_tax = Decimal(discounted_total)
            total_before_tax = total_after_tax / Decimal('1.07')
        else:
            total_before_tax = subtotal
            total_after_tax = subtotal * Decimal('1.07')

        # Round to 2 decimal places
        total_before_tax = total_before_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_after_tax = total_after_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Use transaction to ensure data consistency
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Create the order
                order = Order.objects.create(
                    user=user,
                    shipping_address=shipping_address,
                    payment_card_last4=card_last4,
                    total_before_tax=total_before_tax,
                    total_after_tax=total_after_tax
                )

                ordered_books = []
                
                # Create order items and UPDATE STOCK QUANTITIES
                for item in cart_items:
                    # Double-check stock again within transaction
                    # Use select_for_update to prevent race conditions
                    book = Book.objects.select_for_update().get(id=item.book.id)
                    
                    if item.quantity > book.quantity_in_stock:
                        # Stock changed between checks, rollback transaction
                        raise ValueError(f"Insufficient stock for {book.title}. Only {book.quantity_in_stock} available.")
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        book=book,
                        quantity=item.quantity,
                        price_each=book.selling_price
                    )
                    
                    # **UPDATE BOOK STOCK QUANTITY**
                    book.quantity_in_stock -= item.quantity
                    book.save()
                    
                    # Store for email
                    ordered_books.append({
                        'title': book.title,
                        'quantity': item.quantity,
                        'price_each': book.selling_price,
                        'total': (book.selling_price * item.quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    })

                # Mark promo code as used if applicable
                if promo_code:
                    try:
                        promo = Promotion.objects.get(promo_code__iexact=promo_code, is_active=True)
                        PromotionUsage.objects.create(user=user, promotion=promo)
                        # Clear promo from session
                        request.session.pop('promo_code', None)
                        request.session.pop('discounted_total', None)
                    except Promotion.DoesNotExist:
                        pass  # Promo might have been deactivated, continue with order

                # Clear the cart AFTER successful order creation
                cart_items.delete()

                # Send confirmation email
                try:
                    subject = f"Order Confirmation - Order #{order.order_id}"
                    context = {
                        'name': f"{user.first_name} {user.last_name}",
                        'order_id': order.order_id,
                        'order_date': localtime(order.created_at).strftime('%B %d, %Y %I:%M %p'),
                        'shipping_address': shipping_address,
                        'items': ordered_books,
                        'total': f"{total_after_tax:.2f}",
                        'promo_applied': promo_code if promo_code else None
                    }

                    html_message = render_to_string('store/order_confirmation_email.html', context)
                    plain_message = strip_tags(html_message)

                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email='BookNest4050@gmail.com',
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=True  # Don't fail order if email fails
                    )
                except Exception as e:
                    # Log email error but don't fail the order
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send order confirmation email: {str(e)}")

                messages.success(request, f'Order #{order.order_id} placed successfully!')
                return redirect('order_confirmation', order_id=order.order_id)

        except ValueError as e:
            # Stock insufficient error
            messages.error(request, str(e))
            return redirect('cart_view')
        except Exception as e:
            # Any other error during order processing
            messages.error(request, 'An error occurred while processing your order. Please try again.')
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Order processing error: {str(e)}")
            return redirect('checkout')

    # GET request - show checkout form
    saved_cards = PaymentCard.objects.filter(user=user)
    cart_items = CartItem.objects.filter(user=user).select_related('book')
    
    if not cart_items.exists():
        messages.info(request, 'Your cart is empty.')
        return redirect('cart_view')

    # Check if any items are out of stock before showing checkout
    out_of_stock_items = []
    for item in cart_items:
        if item.quantity > item.book.quantity_in_stock:
            out_of_stock_items.append(item)

    if out_of_stock_items:
        messages.warning(request, 'Some items in your cart have insufficient stock. Please update your cart.')
        return redirect('cart_view')

    subtotal = sum(item.book.selling_price * item.quantity for item in cart_items)
    
    # Check for applied promo
    promo_code = request.session.get('promo_code')
    discounted_total = request.session.get('discounted_total')
    
    if promo_code and discounted_total:
        total_after_tax = Decimal(discounted_total)
        total_before_tax = total_after_tax / Decimal('1.07')
        applied_promo = promo_code
    else:
        total_before_tax = subtotal
        total_after_tax = subtotal * Decimal('1.07')
        applied_promo = None

    # Round totals
    total_before_tax = total_before_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_after_tax = total_after_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total_before': total_before_tax,
        'total_after_tax': total_after_tax,
        'saved_cards': saved_cards,
        'saved_address': saved_address,
        'applied_promo': applied_promo,
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
# Add these views to your Django cart views

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Book, CartItem
from django.db import models
@require_http_methods(["GET"])
def check_cart_availability(request, book_id):
    """Check if a book can be added to cart considering current cart quantity and stock"""
    try:
        book = get_object_or_404(Book, id=book_id)
        
        # Get current quantity in cart for this user
        current_in_cart = 0
        if request.user.is_authenticated:
            cart_item = CartItem.objects.filter(user=request.user, book=book).first()
            if cart_item:
                current_in_cart = cart_item.quantity
        else:
            # For anonymous users, check session cart
            session_cart = request.session.get('cart', {})
            current_in_cart = session_cart.get(str(book_id), 0)
        
        available_stock = book.quantity_in_stock
        can_add_more = current_in_cart < available_stock
        
        return JsonResponse({
            'success': True,
            'current_in_cart': current_in_cart,
            'available_stock': available_stock,
            'can_add_more': can_add_more,
            'book_title': book.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error checking availability: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def ajax_add_to_cart(request, book_id):
    """Add book to cart with proper stock and existing cart quantity validation"""
    try:
        book = get_object_or_404(Book, id=book_id)
        
        # Get current quantity in cart
        current_in_cart = 0
        cart_item = None
        if request.user.is_authenticated:
            cart_item = CartItem.objects.filter(user=request.user, book=book).first()
            if cart_item:
                current_in_cart = cart_item.quantity
        else:
            # Handle anonymous users with session cart
            session_cart = request.session.get('cart', {})
            current_in_cart = session_cart.get(str(book_id), 0)
        
        # Check if we can add one more
        if current_in_cart >= book.quantity_in_stock:
            if book.quantity_in_stock == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'out_of_stock',
                    'message': f'{book.title} is out of stock',
                    'current_in_cart': current_in_cart,
                    'available_stock': book.quantity_in_stock
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'already_at_max',
                    'message': f'You already have all available stock in your cart',
                    'current_in_cart': current_in_cart,
                    'available_stock': book.quantity_in_stock
                })
        
        # Check if stock is available
        if book.quantity_in_stock <= 0:
            return JsonResponse({
                'success': False,
                'error': 'out_of_stock',
                'message': f'{book.title} is out of stock',
                'available_stock': 0
            })
        
        # Add to cart
        if request.user.is_authenticated:
            if cart_item:
                cart_item.quantity += 1
                cart_item.save()
                new_cart_quantity = cart_item.quantity
            else:
                cart_item = CartItem.objects.create(
                    user=request.user,
                    book=book,
                    quantity=1
                )
                new_cart_quantity = 1
            
            # Get total cart count
            total_cart_count = CartItem.objects.filter(user=request.user).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            
        else:
            # Handle anonymous users
            session_cart = request.session.get('cart', {})
            session_cart[str(book_id)] = current_in_cart + 1
            request.session['cart'] = session_cart
            new_cart_quantity = session_cart[str(book_id)]
            total_cart_count = sum(session_cart.values())
        
        return JsonResponse({
            'success': True,
            'message': f'{book.title} added to cart',
            'cart_count': total_cart_count,
            'new_cart_quantity': new_cart_quantity,
            'remaining_stock': book.quantity_in_stock,
            'book_title': book.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'server_error',
            'message': f'Error adding to cart: {str(e)}'
        }, status=500)

# Alternative implementation if you want to prevent adding entirely when stock would be exceeded
@login_required
@require_http_methods(["POST"])
def ajax_add_to_cart_strict(request, book_id):
    """Strict version that won't add if it would exceed available stock"""
    try:
        book = get_object_or_404(Book, id=book_id)
        
        # Get current quantity in cart
        current_in_cart = 0
        cart_item = None
        if request.user.is_authenticated:
            cart_item = CartItem.objects.filter(user=request.user, book=book).first()
            if cart_item:
                current_in_cart = cart_item.quantity
        
        # Check if adding one more would exceed stock
        if (current_in_cart + 1) > book.quantity_in_stock:
            return JsonResponse({
                'success': False,
                'error': 'insufficient_stock',
                'message': f'Cannot add more. Only {book.quantity_in_stock} available, you have {current_in_cart} in cart',
                'current_in_cart': current_in_cart,
                'available_stock': book.quantity_in_stock
            })
        
        # Check if stock is available
        if book.quantity_in_stock <= 0:
            return JsonResponse({
                'success': False,
                'error': 'out_of_stock',
                'message': f'{book.title} is out of stock',
                'available_stock': 0
            })
        
        # Add to cart (same logic as above)
        if cart_item:
            cart_item.quantity += 1
            cart_item.save()
            new_cart_quantity = cart_item.quantity
        else:
            cart_item = CartItem.objects.create(
                user=request.user,
                book=book,
                quantity=1
            )
            new_cart_quantity = 1
        
        # Get total cart count
        total_cart_count = CartItem.objects.filter(user=request.user).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        return JsonResponse({
            'success': True,
            'message': f'{book.title} added to cart',
            'cart_count': total_cart_count,
            'new_cart_quantity': new_cart_quantity,
            'remaining_stock': book.quantity_in_stock,
            'book_title': book.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'server_error',
            'message': f'Error adding to cart: {str(e)}'
        }, status=500)


# Add these imports to your existing views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, date
from .models import Promotion, PromotionSent
from bookstore.accounts.models import Users

@staff_required
def create_promotion(request):
    if request.method == 'POST':
        # Get form data
        promo_code = request.POST.get('promo_code', '').strip().upper()
        percentage = request.POST.get('percentage')
        start_date = request.POST.get('start_date')
        expiration_date = request.POST.get('expiration_date')
        
        # Server-side validation
        errors = []
        
        # Validate promo code
        if not promo_code or len(promo_code) < 3:
            errors.append('Promo code must be at least 3 characters')
        elif not promo_code.replace(' ', '').isalnum():
            errors.append('Promo code can only contain letters and numbers')
        else:
            # Check if promo code already exists and is active
            existing_active_promo = Promotion.objects.filter(
                promo_code__iexact=promo_code, 
                is_active=True
            ).exists()
            if existing_active_promo:
                errors.append('This promo code is already active. Please choose a different one.')
        
        # Validate percentage
        try:
            percentage = int(percentage)
            if percentage < 1 or percentage > 100:
                errors.append('Percentage must be between 1 and 100')
        except (ValueError, TypeError):
            errors.append('Invalid percentage value')
        
        # Validate dates
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            expiration_date_obj = datetime.strptime(expiration_date, '%Y-%m-%d').date()
            
            today = date.today()
            if start_date_obj < today:
                errors.append('Start date cannot be in the past')
            if expiration_date_obj <= start_date_obj:
                errors.append('Expiration date must be after start date')
                
            # Check max duration (365 days)
            duration = (expiration_date_obj - start_date_obj).days
            if duration > 365:
                errors.append('Promotion duration cannot exceed 365 days')
                
        except ValueError:
            errors.append('Invalid date format')
        
        # If there are validation errors, return them as JSON for AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if errors:
                return JsonResponse({
                    'success': False,
                    'errors': errors
                })
            else:
                # Create the promotion
                try:
                    promo = Promotion.objects.create(
                        promo_code=promo_code,
                        percentage=percentage,
                        start_date=start_date_obj,
                        expiration_date=expiration_date_obj,
                        is_active=True
                    )
                    
                    # Email to opted-in users
                    recipients = Users.objects.filter(promotions_opt_in=True, status='Active')
                    email_count = 0
                    for user in recipients:
                        try:
                            PromotionSent.objects.create(promotion=promo, user=user)
                            body = render_to_string('email/promotion_email.html', {
                                'user': user,
                                'promo': promo,
                            })
                            send_mail(
                                subject=f"Exclusive {promo.percentage}% off – Promo Code Inside!",
                                message='',
                                html_message=body,
                                from_email='noreply@bookstore.com',
                                recipient_list=[user.email],
                                fail_silently=True
                            )
                            email_count += 1
                        except Exception as e:
                            continue  # Continue with other users if one fails
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Promotion "{promo.promo_code}" created successfully with {promo.percentage}% discount! Emails sent to {email_count} users.',
                        'promo_code': promo.promo_code,
                        'percentage': promo.percentage
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'errors': [f'Error creating promotion: {str(e)}']
                    })
        
        # Handle non-AJAX requests
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                promo = Promotion.objects.create(
                    promo_code=promo_code,
                    percentage=percentage,
                    start_date=start_date_obj,
                    expiration_date=expiration_date_obj,
                    is_active=True
                )
                messages.success(request, f'Promotion "{promo.promo_code}" created successfully!')
                return redirect('admin_home')
            except Exception as e:
                messages.error(request, f'Error creating promotion: {str(e)}')
    
    return render(request, 'admin/create_promotion.html')

@staff_required 
@require_http_methods(["GET"])
def check_promo_code_availability(request):
    """AJAX endpoint to check if promo code is available"""
    promo_code = request.GET.get('code', '').strip().upper()
    
    if not promo_code:
        return JsonResponse({'available': True})
        
    # Check if code exists and is active
    exists_and_active = Promotion.objects.filter(
        promo_code__iexact=promo_code,
        is_active=True
    ).exists()
    
    return JsonResponse({
        'available': not exists_and_active,
        'code': promo_code
    })
@login_required
def view_promotions(request):
    user = request.user

    used_promotions = Promotion.objects.filter(promotionusage__user=user)
    unused_promotions = Promotion.objects.filter(promotionsent__user=user).exclude(
        id__in=used_promotions.values_list('id', flat=True)
    )

    return render(request, 'store/promotions.html', {
        'used_promotions': used_promotions,
        'unused_promotions': unused_promotions,
    })

from django.http import JsonResponse
from django.utils.timezone import now
from decimal import Decimal
from django.views.decorators.http import require_GET
from bookstore.store.models import PromotionUsage
@login_required
@require_GET

def apply_promo(request):
    code = request.GET.get('code', '').strip()
    user = request.user
    cart_items = CartItem.objects.filter(user=user)

    if not cart_items.exists():
        return JsonResponse({'success': False, 'message': 'Cart is empty.'})

    if request.session.get('promo_code'):
        return JsonResponse({'success': False, 'message': 'A promo code is already applied.'})

    total = sum(item.book.selling_price * item.quantity for item in cart_items)
    tax = total * Decimal("0.07")
    total_after_tax = total + tax

    try:
        promo = Promotion.objects.get(promo_code__iexact=code, is_active=True)
        today = now().date()
        if promo.expiration_date < today or promo.start_date > today:
            return JsonResponse({'success': False, 'message': 'Promo is not valid today.'})

        if PromotionUsage.objects.filter(user=user, promotion=promo).exists():
            return JsonResponse({'success': False, 'message': 'You’ve already used this promo code.'})

        discount = total_after_tax * promo.percentage / Decimal("100")
        discounted_total = total_after_tax - discount

        request.session['promo_code'] = promo.promo_code
        request.session['discounted_total'] = str(discounted_total)

        return JsonResponse({
            'success': True,
            'new_total': str(discounted_total.quantize(Decimal("0.01"))),
})

    except Promotion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid promo code.'})


@login_required
@require_GET
def clear_promo(request):
    request.session.pop('promo_code', None)
    request.session.pop('discounted_total', None)
    return JsonResponse({'success': True})
