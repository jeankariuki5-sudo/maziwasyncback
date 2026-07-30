from django.shortcuts import render
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated 
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from django.db.models import Sum
from collector.serializer import MilkCollectionSerializer
from cooperative.serializers import NoticeSerializer
from core.models import FarmerProfile, Feedback, MilkCollection, Notice
from farmer.serializers import FeedbackSerializer
from datetime import date
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from farmer.services import CattleAIService

# Create your views here.

# Farmer dashboard
class FarmerDashboard(APIView):
    permission_classes =[IsAuthenticated]
    def get(self, request):
        farmer = request.user.farmer_profile
        collection = MilkCollection.objects.filter(farmer = farmer)
        total_collections = collection.count()
        total_litres = collection.aggregate(total = Sum('litres'))['total'] or 0
        total_amount = collection.aggregate(total = Sum('total_amount'))['total'] or 0

        today_collection = collection.filter(collection_date = date.today()).aggregate(total = Sum('litres'))['total'] or 0

        monthly_litres = collection.filter(collection_date__month = timezone.now().month).aggregate(total = Sum('litres'))['total'] or 0

        monthly_earnings = collection.filter(collection_date__month = timezone.now().month).aggregate(total = Sum('total_amount'))['total'] or 0

        return Response({
            "total_collections" : total_collections,
            "total_litres" : total_litres,
            "total_amount" : total_amount,
            "today_collection" : today_collection,
            "monthly_earnings" : monthly_earnings,
            "monthly_litres" : monthly_litres
        })



# farmers collection
class FarmerCollection(generics.ListAPIView):
    serializer_class = MilkCollectionSerializer
    permission_classes = [IsAuthenticated]

    # Query set where we fetch data from the model in a class
    def get_queryset(self):
        try:
            farmer = self.request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            raise PermissionDenied(
                "Only farmers can access this endpoint"
            )
        colleections = (
            MilkCollection.objects
            .filter(farmer = farmer)
            .select_related('porter')
            .order_by('created_at')
        )
        return colleections
    
# Feedback CRUD viewsets
class FeedbackViewset(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        try:
            farmer = self.request.user.farmer_profile
        except:
            raise PermissionDenied("Only farmers can access this endpoint")
        
        feedback = (
            Feedback.objects
            .filter(farmer = farmer)
            .order_by('-created_at')
        )
        return feedback
    
    def perform_create(self, serializer):
        try:
            farmer = self.request.user.farmer_profile
        except:
            raise PermissionDenied("Only farmers can create feedback")
    
        serializer.save(farmer = farmer)

class FarmerNoticeView(generics.ListAPIView):
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        notices = (
            Notice.objects
            .filter(target__in = ['ALL', 'FARMERS'])
            .order_by('-created_at')
        )
        return notices
    

# Cattel Ai Function
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def PredictDisease(request):
    animal = request.data.get("Animal")
    age = request.data.get("Age")
    temp = request.data.get("Temperature")
    description = request.data.get("Dscription")

    # Create our AI object from the CattleAIService
    ai_service = CattleAIService()
    result = ai_service.predict(animal_type = animal, age = age, temp = temp, description = description)
    return Response(result)