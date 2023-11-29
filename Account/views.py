from .models import *
from django.db import models
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from .utils import *
from django.contrib.auth import authenticate,login
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .pagination import CustomPageNumberPagination
# Create your views here.


class SignupAPIView(CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny,]



class LoginAPIView(ObtainAuthToken):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            password = serializer.validated_data['password']
            user = authenticate(request=request, email=email, password=password)

            if user:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return JsonResponse({'token': token.key})
            else:
                return JsonResponse({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LogoutAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def post(self, request):
        request.auth.delete()
        return JsonResponse({'detail': 'Logout successful'}, status=status.HTTP_200_OK)
    


class ListAPIView(generics.ListAPIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        search_keyword = self.request.query_params.get('search', '').strip()
        users = Account.objects.exclude(id=user.id)
        if search_keyword:
            users = Account.objects.filter(
            models.Q(email__iexact=search_keyword) | models.Q(first_name__icontains=search_keyword) | models.Q(last_name__icontains=search_keyword)
        )
        return users

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        response_data = [
            {'email': query.email, 'name': f'{query.first_name} {query.last_name}'}
            for query in queryset
        ]

        page = self.paginate_queryset(response_data)
        if page is not None:
            return self.get_paginated_response(page)
        



User = get_user_model()

@method_decorator(ratelimit(key='user', rate='3/m', method='POST', block=True), name='dispatch')
class FriendRequestView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestSerializer

    def perform_create(self, serializer):
        requester = self.request.user
        recipient_id = self.kwargs['recipient_id']

        try:
            recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Recipient not found.'}, status=status.HTTP_404_NOT_FOUND, content_type='application/json')
        
        existing_request = FriendRequest.objects.filter(
            (models.Q(requester=requester, recipient=recipient) | models.Q(requester=recipient, recipient=requester)),
            status__in=['pending', 'accepted']
        ).first()

        if existing_request:
            return JsonResponse({'error': 'Friend request already exists.'}, status=status.HTTP_400_BAD_REQUEST, content_type='application/json')
        
        serializer.save(requester=requester, recipient=recipient)

        success_response = f'Sent Friend Request to {recipient.first_name} {recipient.last_name}'
        return JsonResponse({'message': success_response}, status=status.HTTP_201_CREATED, content_type='application/json')
    


    

class AcceptRejectFriendRequestView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, friend_request_id, *args, **kwargs):
        action = request.query_params.get('action', '').lower()

        try:
            friend_request = FriendRequest.objects.get(id=friend_request_id)
        except FriendRequest.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        if friend_request.recipient != request.user:
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'accept':
            if friend_request.status != 'pending':
                return Response({'error': 'This friend request cannot be accepted.'}, status=status.HTTP_400_BAD_REQUEST)

            friend_request.status = 'accepted'
            friend_request.save()

            return Response({'message': 'Friend request accepted.'}, status=status.HTTP_200_OK)
        
        elif action == 'reject':
            if friend_request.status != 'pending':
                return Response({'error': 'This friend request cannot be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

            friend_request.status = 'rejected'
            friend_request.save()

            return Response({'message': 'Friend request rejected.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid action parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        




class ListFriendsView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        friends = Friends.objects.filter(user=user).values('friend')
        friend_ids = [friend['friend'] for friend in friends]
        friends_details = User.objects.filter(id__in=friend_ids)
        return friends_details

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        all_friends=[]
        for query in queryset:
            all_friends.append({'email':query.email, 'Name': f'{query.first_name} {query.last_name}'})

        page = self.paginate_queryset(all_friends)
        if page is not None:
            return self.get_paginated_response(page)
        


        
class PendingFriendRequestListView(generics.ListAPIView):
    serializer_class = FriendRequestSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        pending_requests = FriendRequest.objects.filter(
            recipient=user,
            status='pending'
        )
        return pending_requests

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        all_pending_requests = []

        for query in queryset:
            requester = User.objects.get(id=query.requester_id)

            pending_request_data = {
                'email': requester.email,
                'Name': f'{requester.first_name} {requester.last_name}',
            }

            all_pending_requests.append(pending_request_data)

        return Response(all_pending_requests, status=status.HTTP_200_OK)
