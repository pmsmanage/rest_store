import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer


from channels.db import database_sync_to_async

from .models import Chat, Msg
from . import serializers
from multiprocessing import Lock


listeners_dic = {}


class PracticeConsumer(AsyncWebsocketConsumer):

    def __init__(self):
        self.msgs_number = 0  # to keep tracking on how many msgs are loaded, so it know what to load more if requested
        self.chat_id = None
        self.listeners_dic_id = None
        super().__init__()

    @database_sync_to_async
    def get_chat(self):
        return json.dumps(serializers.ChatSerializer(Chat.objects.get(pk=self.chat_id)).data).encode('utf-8')

    @database_sync_to_async
    def send_new_msg(self, msg):
        msg_obj = Msg(chat_id=Chat(id=self.chat_id), msg=msg, sender=self.scope['user'])
        msg_obj.save()
        response = {
            'type': 'new',
            'msg': serializers.MsgSerializer(msg_obj).data}
        return json.dumps(response)

    @database_sync_to_async
    def update_msg(self, msg_id, msg):
        msg_obj = Msg.objects.get(id=msg_id)
        if msg_obj.sender.id != self.scope['user'].id:
            raise Exception('user not allow to change this msg!')
        msg_obj.msg = msg
        msg_obj.save()
        response = {
            'type': 'update',
            'msg': serializers.MsgSerializer(msg_obj).data}
        return json.dumps(response)

    @database_sync_to_async
    def delete_msg(self, msg_id):
        msg_obj = Msg.objects.get(id=msg_id)
        if msg_obj.sender.id != self.scope['user'].id:
            raise Exception('user not allow to change this msg!')
        msg_obj.delete()
        response = {
            'type': 'delete',
            'id': msg_id}
        return json.dumps(response)

    @database_sync_to_async
    def is_user_allowed(self):
        return self.scope['user'].chats.contains(Chat(pk=self.chat_id))

    @staticmethod
    async def broadcast(msg, chat_id):
        for listener in listeners_dic[chat_id]['listeners'].values():
            await listener.send(msg)

    @database_sync_to_async
    def get_chat_as_str(self):
        return json.dumps(serializers.ChatSerializer(Chat.objects.get(pk=self.chat_id)).data)

    async def websocket_connect(self, event):
        self.chat_id = self.scope['url_route']['kwargs']['id']

        if not await self.is_user_allowed():
            await self.close()
            return

        if self.chat_id in listeners_dic:
            with listeners_dic[self.chat_id]['lock']:
                self.listeners_dic_id = listeners_dic[self.chat_id]['serial_id']
                listeners_dic[self.chat_id]['serial_id'] += 1
                listeners_dic[self.chat_id]['listeners'][self.listeners_dic_id] = self
        else:
            listeners_dic[self.chat_id] = {}
            listeners_dic[self.chat_id]['lock'] = Lock()
            with listeners_dic[self.chat_id]['lock']:
                self.listeners_dic_id = 1
                listeners_dic[self.chat_id]['serial_id'] = 2
                listeners_dic[self.chat_id]['listeners'] = {self.listeners_dic_id: self}

        await self.accept()

        await self.send(await self.get_chat_as_str())

    async def websocket_receive(self, event):

        my_obj = json.loads(event['text'])
        method = my_obj['method']
        msg = ''
        if method=='new':
            msg = await self.send_new_msg(my_obj['msg'])
        elif method=='update':
            msg = await self.update_msg(my_obj['id'], my_obj['msg'])
        elif method=='delete':
            msg = await self.delete_msg(my_obj['id'])
        await self.broadcast(msg, self.chat_id)

    async def websocket_disconnect(self, event):
        listeners_dic[self.chat_id]['listeners'].pop(self.listeners_dic_id)
        if len(listeners_dic[self.chat_id]['listeners']) == 0:
            with listeners_dic[self.chat_id]['lock']:
                listeners_dic.pop(self.chat_id)
