from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Feature, Plan, Subscription


class SubscriptionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.feature = Feature.objects.create(name='Test Feature')
        self.basic_plan = Plan.objects.create(name='Basic', price=Decimal('10.00'))
        self.premium_plan = Plan.objects.create(name='Premium', price=Decimal('20.00'))
        self.basic_plan.features.add(self.feature)

    def test_create_subscription(self):
        """Test subscription creation with nested plan/feature data."""
        data = {'plan_id': self.basic_plan.id, 'frequency': 'monthly'}
        response = self.client.post(reverse('subscription-list'), data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Subscription.objects.count(), 1)
        
        # Verify nested data
        self.assertIn('plan', response.data)
        self.assertEqual(response.data['plan']['name'], 'Basic')
        self.assertIn('features', response.data['plan'])
        self.assertEqual(len(response.data['plan']['features']), 1)

    def test_create_subscription_invalid_plan(self):
        """Test creation with invalid plan ID."""
        data = {'plan_id': 99999, 'frequency': 'monthly'}
        response = self.client.post(reverse('subscription-list'), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Subscription.objects.count(), 0)

    # === PLAN SWITCHING TESTS ===
    def test_switch_plan_different_plan(self):
        """Test switching to different plan."""
        # Create existing subscription
        old_sub = Subscription.objects.create(
            user=self.user, plan=self.basic_plan, frequency='monthly'
        )
        
        data = {'plan_id': self.premium_plan.id, 'frequency': 'monthly'}
        response = self.client.post(reverse('subscription-switch-plan'), data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify old deactivated, new created
        old_sub.refresh_from_db()
        self.assertFalse(old_sub.is_active)
        
        new_sub = Subscription.objects.get(is_active=True)
        self.assertEqual(new_sub.plan, self.premium_plan)

    def test_switch_plan_longer_frequency_same_plan(self):
        """Test switching to longer frequency on same plan."""
        Subscription.objects.create(
            user=self.user, plan=self.basic_plan, frequency='weekly'
        )
        
        data = {'plan_id': self.basic_plan.id, 'frequency': 'monthly'}
        response = self.client.post(reverse('subscription-switch-plan'), data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_switch_plan_shorter_frequency_fails(self):
        """Test switching to shorter frequency fails."""
        Subscription.objects.create(
            user=self.user, plan=self.basic_plan, frequency='monthly'
        )
        
        data = {'plan_id': self.basic_plan.id, 'frequency': 'weekly'}
        response = self.client.post(reverse('subscription-switch-plan'), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_subscriptions_with_nested_data(self):
        """Test retrieving subscription list with nested plan and feature data."""
        subscription = Subscription.objects.create(
            user=self.user, plan=self.basic_plan, frequency='monthly'
        )
        
        response = self.client.get(reverse('subscription-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # Verify nested data structure
        sub_data = response.data[0]
        self.assertEqual(sub_data['id'], subscription.id)
        self.assertIn('plan', sub_data)
        self.assertEqual(sub_data['plan']['name'], 'Basic')
        self.assertIn('features', sub_data['plan'])
        self.assertEqual(len(sub_data['plan']['features']), 1)

    def test_list_only_user_subscriptions(self):
        """Test users only see their own subscriptions."""
        other_user = User.objects.create_user(username='other', password='test123')
        
        # Create subscription for current user
        Subscription.objects.create(
            user=self.user, plan=self.basic_plan, frequency='monthly'
        )
        
        # Create subscription for other user
        Subscription.objects.create(
            user=other_user, plan=self.premium_plan, frequency='yearly'
        )
        
        response = self.client.get(reverse('subscription-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only current user's subscription