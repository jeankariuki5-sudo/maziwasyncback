from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import viewsets
from django.utils import timezone
from rest_framework.views import APIView
from datetime import timedelta
from django.db.models import Sum
from rest_framework.response import Response


from collector.serializer import MilkCollectionSerializer
from cooperative.serializers import FarmerSerializer, NoticeSerializer, PorterSerializer
from cooperative.services import MpesaPayment
from core.models import FarmerProfile, Feedback, MilkCollection, Notice, Payment, PorterProfile
# Create your views here.
# Admin /cooperative dashboard
class AdminDashboardViewset(APIView):
    # Only admin can view this dashboard
    permission_classes = [IsAdminUser]

    # Method to get analytics
    def get(self, request):
        # Define the dates according to Django timezone settings
        # Used for daily, weekly and monthly calculation
        today = timezone.localdate()
        # Calculate the weekly which is 7 days
        week_start = today-timedelta(days=7)

        # farmer and porter stats
        total_farmers = FarmerProfile.objects.count()
        total_porters = PorterProfile.objects.count()

        # milk collection stats
        # We retrieve all the collections so that we can reuse
        collections = MilkCollection.objects.all()

        total_litres = collections.aggregate(total=Sum('litres'))['total'] or 0
        today_litres = collections.filter(collection_date=today).aggregate(
            total = Sum('litres')
        )['total'] or 0

        # Weekly collection
        weekly_litres = collections.filter(collection_date__gte=week_start).aggregate(
            total = Sum('litres')
        )['total'] or 0

        # monthly collection
        monthly_litres = collections.filter(
            collection_date__year=today.year,
            collection_date__month=today.month).aggregate(
            total = Sum('litres')
        )['total'] or 0

        # total revenue
        total_revenue = collections.aggregate(total = Sum('total_amount'))['total'] or 0

        # today revenue
        today_revenue = collections.filter(collection_date=today).aggregate(
            total = Sum('total_amount')
        )['total'] or 0

        # Weekly revenue
        weekly_revenue = collections.filter(collection_date__gte=week_start).aggregate(
            total = Sum('total_amount')
        )['total'] or 0

        # monthly revenue
        monthly_revenue = collections.filter(
            collection_date__year=today.year,
            collection_date__month=today.month).aggregate(
            total = Sum('total_amount')
        )['total'] or 0


        # feedback analytics
        feedbacks = Feedback.objects.all()

        total_feedbacks = feedbacks.count()

        pending_feedbacks = feedbacks.filter(status='PENDING').count()
        resolved_feedbacks = feedbacks.filter(status='RESOLVED').count()
        rejected_feedbacks = feedbacks.filter(status='REJECTED').count()

        # Top farmers
        top_farmers = FarmerProfile.objects.order_by(
            '-total_milk_delivered'
        )[:5]

        # Convert the farmer profile objects into Json
        # Response cannot directly return the message model objects
        top_farmers_data = FarmerSerializer(
            top_farmers,
            many = True
        ).data

        # Top ten latest milk collections
        recent_collections = MilkCollection.objects.select_related(
            'farmer',
            'porter'
        ).order_by('-created_at')[:10]

        # convert the collecion objects into JSON data
        recent_collection_data = MilkCollectionSerializer(
            recent_collections,
            many = True
        ).data

        # Dashboard response
        return Response({
            'total_farmers': total_farmers,
            'total_porters': total_porters,
            'total_litres': total_litres,
            'today_litres': today_litres,
            'weekly_litres': weekly_litres,
            'monthly_litres': monthly_litres,
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'weekly_revenue': weekly_revenue,
            'monthly_revenue': monthly_revenue,
            'total_feedbacks': total_feedbacks,
            'pending_feedbacks': pending_feedbacks,
            'resolved_feedbacks': resolved_feedbacks,
            'rejected_feedbacks': rejected_feedbacks,
            'top_farmers': top_farmers_data,
            'recent_collections': recent_collection_data,
        })







class FarmerViewSet(viewsets.ModelViewSet):
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerSerializer
    permission_classes = [IsAdminUser]

    http_method_names = ['put', 'patch', 'delete', 'get']


class PorterViewSet(viewsets.ModelViewSet):
    queryset = PorterProfile.objects.all()
    serializer_class = PorterSerializer
    permission_classes = [IsAdminUser]

    http_method_names = ['put', 'patch', 'delete', 'get']

class MilkCollectionViewSet(viewsets.ModelViewSet):
    queryset = MilkCollection.objects.select_related(
        'farmer',
        'porter',
    )
    serializer_class = MilkCollectionSerializer
    permission_classes = [IsAdminUser]

    http_method_names = ['put', 'patch', 'delete', 'get']


class NoticeViewset (viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [IsAdminUser]

    # method that offers flexibility when you are making a post request
    def perform_create(self, serializer):
        serializer.save(created_by = self.request.user)


# Get farmer with outstanding balances
@api_view(['GET'])
@permission_classes ([IsAdminUser])
def FarmersWithBalance(request):
    farmers = FarmerProfile.objects.all()
    data = []
    for farmer in farmers:
        # Amount earned by farmer
        earned = MilkCollection.objects.filter(farmer=farmer).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Amount paid by the cooperation
        paid = Payment.objects.filter(farmer=farmer, status = 'COMPLETED'). aggregate(
        total=Sum('amount')
        )['total'] or 0


        balance = earned - paid
        if balance > 0 :
            data.append({
                "farmer_id" : farmer.id,
                "farmer" : f"{farmer.first_name} {farmer.last_name}",
                "phone" : farmer.phone_number,
                "earned" : earned,
                "paid" : paid,
                "balance" : balance
        })
    return Response(data)


# Initiate the disbursment to the farmer
@api_view(["POST"])
@permission_classes([IsAdminUser])
def PayFarmer(request):
    farmer_id = request.data.get("farmer_id")
    amount = request.data.get("amount")

    farmer = FarmerProfile.objects.get(id = farmer_id)

    earned = MilkCollection.objects.filter(farmer = farmer).aggregate(
        total = Sum('total_amount')
    )['total'] or 0

    paid = Payment.objects.filter(farmer = farmer).aggregate(
        total = Sum('amount')
    )['total'] or 0

    balance = earned - paid

    # Preventing paying a farmer who has no pending balance
    if balance <= 0:
        return Response({"message" : "No pending Payment"})
    
    # Creating object from MpesaPayment class in services.py
    payment = MpesaPayment()
    result = payment.pay_farmer(farmer.phone_number, amount)

    # Create the Payment Record
    Payment.objects.create(
        farmer = farmer,
        amount = amount,
        payment_method = "MPESA",
        originator_conversation_id = result['OriginatorConversationID'],
        transaction_ref = result['ConversationID'],
        payment_date = timezone.now()
    )

    return Response ({
        "farmer" : f"{farmer.first_name}  {farmer.last_name}",
        "prev_balance" : balance,
        "mpesa_response" : result
    })

# Asynchronous call back processing webhok
@api_view(["POST"])
@permission_classes([AllowAny])
def MpesaCallback(request):
    print("==============call back==================")

    data = request.data

    # Print the response fron safaricom to see it in the terminal
    print("Data", data)
    result = data["Result"]

    originator_conversation_id = result["OriginatorConversationID"]

    # retrieve the matching payment record with the originator convo id
    payment = Payment.objects.get(originator_conversation_id = originator_conversation_id)

    # Check if the transaction was successfull
    if result["ResultCode"]==0:
        payment.status="COMPLETED"
        payment.transaction_ref=result['TransactionID']
    else:
        payment.status="FAILED"

    payment.save()
    return Response({"received" : True})