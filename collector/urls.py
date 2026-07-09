from django.urls import path
from collector import views
from .views import MyCollections


urlpatterns = [
    path('dashboard/', views.PorterDashboard),
    path('milk-collections/add/',views.AddMilkCollection),
    path('collections/my/', MyCollections.as_view()),
]