from django.db import transaction
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


from .models import Subscription, FREQUENCY_ORDER
from .serializers import (
SubscriptionCreateSerializer,
SubscriptionListSerializer,
)

# Create your views here.
class SubscriptionViewSet(viewsets.GenericViewSet,
                          mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin):
    permission_classes = (IsAuthenticated,)
    lookup_field = "pk"

    def get_queryset(self):
        return (
            Subscription.objects.filter(user=self.request.user)
            .select_related("plan")
            .prefetch_related("plan__features")
        )

    def get_serializer_class(self) -> SubscriptionListSerializer | SubscriptionCreateSerializer:
        if self.action == "create":
            return SubscriptionCreateSerializer
        return SubscriptionListSerializer
    
    def create(self, request, *args, **kwargs) -> Response:
        """Override create to return full subscription details."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()

        output_serializer = SubscriptionListSerializer(
            subscription, 
            context=self.get_serializer_context()
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer) -> None:
        serializer.save()  # user is set in serializer.create()

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="switch-plan")
    def switch_plan(self, request):
        # Validate the new subscription data first
        create_serializer = SubscriptionCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        create_serializer.is_valid(raise_exception=True)
        new_plan = create_serializer.validated_data['plan']
        new_frequency = create_serializer.validated_data['frequency']

        try:
            old_subscription = Subscription.objects.select_for_update().get(
                user=request.user,
                is_active=True
            )
        except Subscription.DoesNotExist:
            # No active subscription — allow creation
            new_subscription = create_serializer.save()
            list_serializer = SubscriptionListSerializer(new_subscription)
            return Response(list_serializer.data, status=status.HTTP_201_CREATED)

        # --- Upgrade/Downgrade rules ---
        old_frequency = old_subscription.frequency

        if not FREQUENCY_ORDER[new_frequency] > FREQUENCY_ORDER[old_frequency] and new_plan == old_subscription.plan:
            return Response(
                {"detail": "You can only switch to a longer frequency."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deactivate old subscription
        old_subscription.is_active = False
        old_subscription.save(update_fields=['is_active'])

        # Create new subscription
        new_subscription = create_serializer.save()

        # Return response
        list_serializer = SubscriptionListSerializer(new_subscription)
        return Response(list_serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None) -> Response:
        """Deactivate a subscription."""
        updated_count = (
            Subscription.objects
            .filter(pk=pk, user=request.user, is_active=True)
            .update(is_active=False)
        )
        
        if not updated_count:
            return Response(
                {"detail": "Subscription not found or already inactive"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Fetch the updated subscription for response
        subscription = get_object_or_404(
            self.get_queryset(),
            pk=pk
        )
        
        serializer = SubscriptionListSerializer(subscription)
        return Response(serializer.data)
