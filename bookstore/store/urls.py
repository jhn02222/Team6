from django.urls import path
from . import views
from .views import create_promotion
from .views import remove_from_cart

urlpatterns = [
    path('', views.home_view, name='store_home'),
    path("search/", views.search_books, name="search_books"),
    path('admin/add-book/', views.add_book, name='add_book'),
    path('admin/promotions/view/', views.view_promotions_admin, name='view_promos'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('cart/add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('store/order/confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/history/', views.order_history, name='order_history'),

    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/check-availability/<int:book_id>/', views.check_cart_availability, name='check_cart_availability'),
    path('cart/ajax-add/<int:book_id>/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    
    path('admin/promotions/create/', create_promotion, name='create_promotion'),
    path('promotions/', views.view_promotions, name='view_promotions'),
    path('apply-promo/', views.apply_promo, name='apply_promo'),
    path('clear-promo/', views.clear_promo, name='clear_promo'),
     path('admin/create-promotion/', views.create_promotion, name='create_promotion'),
    
    # AJAX endpoint to check promo code availability
    path('admin/check-promo-code/', views.check_promo_code_availability, name='check_promo_code'),
    
]
