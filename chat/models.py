from django.db import models
from django.contrib.auth.models import User


class Chat (models.Model):
    name = models.CharField(max_length=50)
    users = models.ManyToManyField(User, related_name="chats")
    group = models.BooleanField(default=False)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)


class Msg (models.Model):
    chat_id = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="msgs")
    msg = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="msgs")
    time_sent = models.DateTimeField(auto_now_add=True)
    last_change = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='chat/images/', blank=True, null=True)
    file = models.FileField(upload_to='chat/files/', blank=True, null=True)

    class Meta:
        ordering = ["-time_sent"]

    def __str__(self):
        return f"{self.time_sent} {self.sender}: {self.msg}"
