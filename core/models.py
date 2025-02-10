from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    price = models.IntegerField()
    interval = models.CharField(max_length=50, default='month')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        if self.end_date:
            if now() < self.end_date:
                return True
            else:
                return False
        else:
            return True

    @property
    def tier(self):
        tier_mapping = {
            'Test_subs_1': 1, # The product name follows that of the Stripe product
            'Test_subs_2': 2,
        }
        tier = tier_mapping.get(self.product_name, None)
        return tier

    def __str__(self):
        return f"{self.user.username} - {self.product_name} - Active: {self.is_active}"

    def next_billing_date(self):
        if self.is_active:
            if self.interval == 'month':
                next_billing_date = self.start_date + relativedelta(months=1)
            elif self.interval == 'year':
                next_billing_date = self.start_date + relativedelta(years=1)
            else:
                next_billing_date = self.start_date + relativedelta(days=7)
        else:
            next_billing_date = None
        return next_billing_date