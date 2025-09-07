from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


FREQUENCY_ORDER = {
    "weekly": 1,
    "monthly": 2,
    "yearly": 3,
}

class Feature(models.Model):
    name = models.CharField(max_length=100 , unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    features = models.ManyToManyField(Feature, related_name='plans', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} - ${self.price}"


class Subscription(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('weekly', 'Weekly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='subscriptions', db_index=True)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE,
                             related_name='subscriptions', db_index=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES,
                                  default='monthly', db_index=True)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Ensure a user can only have one active subscription at a time
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_active=True),
                name='unique_active_subscription_per_user'
            )
        ]
    
        # Composite indexes for common query patterns
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_active', '-created_at']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def calculate_amount(self) -> Decimal:
        """Compute amount based on plan price and frequency."""
        multipliers = {
            "monthly": 1,
            "yearly": 12,
            "weekly": 1 / 4,  # assuming monthly price is the base
        }
        multiplier = Decimal(multipliers.get(self.frequency, 1))
        return self.plan.price * multiplier
    
    def calculate_end_date(self) -> timezone.datetime:
        """Calculate end_date based on start_date and frequency."""
        start = self.start_date or timezone.now()
        
        if self.frequency == 'weekly':
            return start + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Add 30 days for monthly
            return start + timedelta(days=30)
        elif self.frequency == 'yearly':
            return start + timedelta(days=365)
        else:
            # Default to monthly if frequency is not recognized
            return start + timedelta(days=30)

    def save(self, *args, **kwargs):
        # Set start_date if not already set (for manual creation)
        if not self.start_date:
            self.start_date = timezone.now()
            
        # Always recalculate amount and end_date before saving
        self.amount = self.calculate_amount()
        self.end_date = self.calculate_end_date()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({'Active' if self.is_active else 'Inactive'})"
