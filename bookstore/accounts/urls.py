from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('admin/', views.admin_home, name='admin'),
    path('profile/', views.profile_view, name='profile'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),
    path('logout/', views.logout_view, name='logout'),
]
