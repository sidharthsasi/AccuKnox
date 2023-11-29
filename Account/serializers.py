from rest_framework import serializers
from .models import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import FriendRequest, Friends



class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['email', 'username', 'first_name','last_name','password']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def create(self, validated_data):
        user = Account.objects.create_user(email=validated_data['email'].lower(), password=validated_data['password'], first_name=validated_data['first_name'], last_name=validated_data['last_name'])
        try:
            validate_password(password=validated_data['password'], user=user)
        except ValidationError as err:
            user.delete()
            raise serializers.ValidationError({'password': err.messages})
        return user
    


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)





class FriendRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendRequest
        fields = []
