from django.contrib.auth import login
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import StudentRegistrationForm
from .serializers import StudentLoginSerializer


def register(request):
    if request.user.is_authenticated:
        return redirect("course_list")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("course_list")
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


class StudentLoginAPIView(APIView):
    """Issue a DRF token for valid student credentials."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )
