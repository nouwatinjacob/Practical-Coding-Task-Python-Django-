from rest_framework import serializers
from .models import Feature, Plan, Subscription

class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ("id", "name")




class PlanSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = ("id", "name", "price", "features")




class SubscriptionCreateSerializer(serializers.ModelSerializer):
    plan_id = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all(), source="plan")
    frequency = serializers.ChoiceField(choices=Subscription.FREQUENCY_CHOICES, required=False, default='monthly')

    class Meta:
        model = Subscription
        fields = ("id", "plan_id", "frequency")
        read_only_fields = ("id",)

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        subscription = Subscription.objects.create(user=user, **validated_data)
        return subscription


class SubscriptionListSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ("id", "frequency", "amount", "plan", "is_active", "start_date", "end_date")