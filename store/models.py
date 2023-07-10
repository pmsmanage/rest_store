from django.db import models
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.urls import reverse
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist


class Product(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(default="")
    rate = models.FloatField(default=0)
    tags = TaggableManager()

    class Meta:
        ordering = ["-rate"]

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse('RUD-product', kwargs={'pk': self.pk})


class Cart(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'Draft', 'Draft'
        ORDERED = 'Ordered', 'Ordered'
        ON_WAY = 'On the way', 'On the way'
        REJECTED = 'Rejected', 'Rejected'
        RECEIVED = 'Received', 'Received'
        DELIVERED = 'Delivered', 'Delivered'
        APPROVED = 'Approved', 'Approved'
    products = models.ManyToManyField(Product, related_name='carts', through='CartItem')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    order_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    def __str__(self):
        return f"cart for {self.customer} at:{self.order_date}"

    def get_absolute_url(self):
        return reverse('RUD-cart', kwargs={'pk': self.pk})


@receiver(pre_save, sender=Cart)
def cart_pre_save(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        return

    old_status = old_instance.status
    new_status = instance.status

    if old_status == sender.Status.ORDERED and (new_status == Cart.Status.ON_WAY or new_status == Cart.Status.REJECTED):
        subject = f"Your cart status updated"
        message = f"Hello {instance.customer.username}\n" \
                  f"Your cart with id:{instance.pk} which is ordered at:{instance.order_date}" \
                  f" is {sender.Status(instance.status).label}"
        send_mail(subject, message, 'pmsmanage0@gmail.com', [instance.customer.email])


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    count = models.IntegerField(default=1)


class BlackListedToken(models.Model):
    token = models.CharField(max_length=500)
    user = models.ForeignKey(User, related_name="token_user", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("token", "user")
