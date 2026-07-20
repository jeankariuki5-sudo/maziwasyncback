from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cooperative import views

router = DefaultRouter()
router.register('farmer', views.FarmerViewSet, basename='farmers')
router.register('porter', views.PorterViewSet, basename='porters' )
router.register('milkcollection', views.MilkCollectionViewSet, basename='milkcollections')
router.register('notice', views.NoticeViewset, basename='notice')
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.AdminDashboardViewset.as_view()),
    path('farmer_balance/', views.FarmersWithBalance),
    path('pay_farmer/', views.PayFarmer),
    path('callback', views.MpesaCallback),
    path('', include(router.urls)),
]