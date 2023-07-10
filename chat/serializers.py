from rest_framework import serializers
from .models import Chat, Msg
from django.contrib.auth.models import User


class ChatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'name', 'users', 'group', 'admin']
        read_only_fields = ['id']
        write_only_fields = ['group', 'admin']
        optional_fields = ['group', 'name']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # adding msgs
        users = instance.users.all()
        data['users'] = [user.username for user in users]
        return data

    def get_usernames(self, obj):
        return [user.username for user in obj.users.all()]

    def validate_users(self, value):
        if not self.initial_data.get('group'):
            if len(value)!= 1:
                raise serializers.ValidationError('in private chat you have to provide one and and only one user')
            user2 = User.objects.get(username=value[0])
            user = self.context['request'].user
            if user2.id == user.id:
                raise serializers.ValidationError("you can't make a private chat with yourself, make an empty group for the same functionality")
            if Chat.objects.filter(group=False).filter(users__in=([user2.id] + [user.id])):
                raise serializers.ValidationError('there is already a private chat between this users!')
        return [user.id for user in User.objects.filter(username__in=value)]

    def create(self, validated_data):
        if validated_data.get('group', False):
            chat = Chat(name=validated_data['name'], group=True, admin=validated_data.get('admin', None))
        else:

            chat = Chat(name=validated_data.get('name', validated_data['users']))
        chat.save()
        chat.users.set(validated_data['users'] + [self.context['request'].user.id])
        chat.save()
        return chat


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'name', 'users']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # adding msgs
        msgs = Msg.objects.filter(chat_id=data['id'])[:5]
        data['msgs'] = [MsgSerializer(msg).data for msg in msgs]
        return data


class MsgSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Msg
        fields = ['id', 'sender', 'msg', 'image', 'time_sent', 'last_change']


