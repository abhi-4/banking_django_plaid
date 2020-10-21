from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('', views.index, name = 'index'),
    path('signup/', views.signup, name = 'signup'),
    path('login/', views.loginPage, name = 'login'),
    path('logout/', views.logoutUser, name = 'logout'),
    path('home/', views.home, name = 'home'),
    path('account/', views.account, name = 'account'),
    path('submitToken/', views.submitToken, name = 'submitToken'),
    path('getAccountData', views.getAccountData, name = 'getAccountData'),
    path('getTransactionData', views.getTransactionData, name = 'getTransactionData'),
]