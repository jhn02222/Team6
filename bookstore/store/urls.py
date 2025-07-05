from django.urls import path
from . import views

from .views import remove_from_cart

urlpatterns = [
    path('', views.home_view, name='store_home'),
    path("search/", views.search_books, name="search_books"),
    path('admin/add-book/', views.add_book, name='add_book'),
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/promotions/', views.manage_promotions, name='manage_promotions'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('cart/add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('order/confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/history/', views.order_history, name='order_history'),

    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
     path('cart/ajax-add/<int:book_id>/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
]
