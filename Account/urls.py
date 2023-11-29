from django.urls import include, path

from .views import *
urlpatterns = [
    path('signup', SignupAPIView.as_view(), name='signup'),
    path('login', LoginAPIView.as_view(), name='login'),
    path('logout', LogoutAPIView.as_view(), name='logout'),
    path('listusers', ListAPIView.as_view(), name='listusers'),
    path('add_friend/<str:recipient_id>', FriendRequestView.as_view(), name='send-friend-request'),
    path('response/<str:friend_request_id>', AcceptRejectFriendRequestView.as_view(), name='accept-reject-friend-request'),
    path('friends', ListFriendsView.as_view(), name='list-friends'),
    path('pending-friend-requests', PendingFriendRequestListView.as_view(), name='pending-friend-requests')
]
