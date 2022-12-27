from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "tckn",
            "password",
            "third_party_app_password",
            "email",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "third_party_app_password": {"write_only": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            tckn=validated_data["tckn"],
            password=validated_data["password"],
            third_party_app_password=validated_data["third_party_app_password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["first_name"],
        )
        return user


# User serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "tckn", "id", "phone_number", "first_name", "last_name")
