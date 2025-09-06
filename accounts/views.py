from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserRegistrationSerializer

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]  # anyone can register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # generate JWT tokens for the new user
        refresh = RefreshToken.for_user(user)

        data = {
            "username": user.username,
            "email": user.email,
            "token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
        return Response(data, status=status.HTTP_201_CREATED)