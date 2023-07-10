import json
import asyncio
from django.http import HttpResponse
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.uploadedfile import InMemoryUploadedFile
import re

from . import serializers
from .models import Chat, Msg
from . import permissions
from .consumers import listeners_dic, PracticeConsumer


class ChatListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ChatListSerializer

    def get_queryset(self):
        user = self.request.user
        return user.chats.all()


class ChatView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, permissions.IsChatMember]
    serializer_class = serializers.ChatSerializer
    queryset = Chat.objects.all()

    def post(self, request, pk):
        chat = Chat()
        chat.pk = pk
        msg = Msg(chat_id=chat, sender=request.user, msg=request.POST['msg'])
        msg.save()
        image = request.data['image']
        image.name = f"{pk}-{msg.pk}-{image.name}"
        msg.image = image
        msg.save()
        asyncio.run(PracticeConsumer.broadcast(json.dumps({'type': 'new', 'msg': serializers.MsgSerializer(msg).data}), pk))
        return Response(status=status.HTTP_201_CREATED)


class ImageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, name):
        if not re.fullmatch(r'[0-9]+-[0-9]+-.+', name):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        i = name.find('-')
        chat_id = name[:i]
        if not request.user.chats.contains(Chat(pk=chat_id)):
            return Response(status=status.HTTP_404_NOT_FOUND)

        with open(f"media/chat/images/{name}", "rb") as f:
            image_data = f.read()
        return HttpResponse(image_data, content_type="image/png")

