from django.contrib import admin
from django.urls import path, include
 
urlpatterns = [
    path('', include('bookstore.store.urls')), 
    path('accounts/', include('bookstore.accounts.urls')),
    path('store/', include('bookstore.store.urls')),  # Correct!
]