from django.db.models import Count
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.urls import reverse
from taggit.models import Tag
from multiprocessing import Lock

from .models import Product, Cart
from django.utils.timezone import now
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password


class LockManager:
    my_dict = {}
    dic_lock = Lock()

    def __init__(self, cart_id):
        self.cart_id = cart_id
        self.lock_data = None

    def __enter__(self):
        with self.dic_lock:
            self.lock_data = self.my_dict.get(self.cart_id, None)
            if self.lock_data is None:
                self.lock_data = [Lock(), 1]
            else:
                self.lock_data[1]+=1
            self.my_dict[self.cart_id] = self.lock_data
        self.lock_data[0].__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock_data[0].__exit__()
        with self.dic_lock:
            self.lock_data = self.my_dict.get(self.cart_id, None)
            if self.lock_data is not None:
                if self.lock_data[1] == 1:
                    self.my_dict.pop(self.cart_id)
                else:
                    self.lock_data[1] -= 1


class ProductSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(write_only=True, required=False)
    url = serializers.SerializerMethodField('get_url', read_only=True)
    recommend = serializers.SerializerMethodField('get_recommend', read_only=True)
    tags_read = serializers.SerializerMethodField('get_tags', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'rate', 'description', 'tags', 'tags_read', 'url', 'recommend']
        read_only_fields = ['id', 'url']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if self.context['request'].method != 'GET':
            data.pop('recommend', None)

        data['tags'] = data.pop('tags_read')

        return data

    def create(self, validated_data):
        tags_names = validated_data.pop('tags', [])
        instance = Product.objects.create(**validated_data)
        for tag_name in tags_names:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            instance.tags.add(tag)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        tags_names = validated_data.pop('tags', [])
        Product.objects.update(**validated_data)
        instance = Product.objects.get(pk=instance.id)
        if tags_names:
            instance.tags.clear()
            for tag_name in tags_names:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)
        instance.save()
        return instance

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_recommend(self, obj):
        instance = Product.objects.get(pk=obj.id)
        tags_ids = instance.tags.values_list('id', flat=True)
        my_query_set = Product.objects.filter(tags__in=tags_ids).exclude(id=obj.id)
        my_query_set = my_query_set.annotate(same_tags=Count('tags')).order_by('-same_tags', '-rate')[:3]
        result = []
        for product in my_query_set:
            serializer = ProductListSerializer(product)
            result.append(serializer.data)
        return result

    def get_tags(self, obj):
        instance = Product.objects.get(pk=obj.id)
        return [tag.name for tag in instance.tags.all()]


class CartSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), write_only=True, required=False)
    new_products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), write_only=True, required=False)
    products_with_count = serializers.SerializerMethodField('get_products_with_count', read_only=True)
    url = serializers.SerializerMethodField('get_url', read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'products', 'status', 'order_date', 'products_with_count', 'url', 'new_products']
        read_only_fields = ['id', 'order_date', 'products_with_count']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['products'] = data.pop('products_with_count')
        return data

    def validate_status(self, value):
        if value == Cart.Status.DELIVERED:
            if self.context['request'].method.POST:
                raise serializers.ValidationError('customer can\'t change this/to this status')
        if value in [Cart.Status.DRAFT, Cart.Status.ORDERED]:
            return value
        raise serializers.ValidationError('customer can\'t change this/to this status')

    def validate(self, attrs):
        user = self.context['request'].user
        if self.context['request'].method == 'post' and Cart.objects.all().filter(customer=user).filter(status=Cart.Status.DRAFT):
            raise serializers.ValidationError('there is already a draft cart, you can\'t make new one')
        return attrs

    def create(self, validated_data):
        cart = Cart()
        user = self.context['request'].user
        cart.customer = user
        cart.save()
        products = validated_data.get('products', [])
        if not products:
            raise serializers.ValidationError({'products': 'at least 1 product must be add'})
        for product in products:
            cart_item = cart.cartitem_set.all().filter(product=product)
            if cart_item:
                cart_item = cart_item[0]
                cart_item.count += 1
                cart_item.save()
            else:
                cart.products.add(product)
        cart.status = Cart.Status(validated_data.get('status', Cart.Status.DRAFT.value))
        if cart.status == Cart.Status.ORDERED:
            cart.order_date = now()
        cart.save()
        return cart

    def update(self, instance, validated_data):
        with LockManager(f'cart_{instance.pk}'):
            if validated_data.get('status', None) == Cart.Status.RECEIVED:
                if instance.status == Cart.Status.DELIVERED:
                    instance.status = Cart.Status.APPROVED
                    instance.save()
                elif instance.status == Cart.Status.ON_WAY:
                    instance.status = Cart.Status.RECEIVED
                    instance.save()
                else:
                    raise serializers.ValidationError({'details': 'customer can\'t change current this status'})
            if instance.status != Cart.Status.DRAFT:
                raise serializers.ValidationError({'details': 'customer can only change cart if status is draft'})
            products = validated_data.get('products', [])
            if products:
                instance.products.clear()
                for product in products:
                    cart_item = instance.cartitem_set.all().filter(product=product)
                    if cart_item:
                        cart_item = cart_item[0]
                        cart_item.count += 1
                        cart_item.save()
                    else:
                        instance.products.add(product)
            new_products = validated_data.get('new_products', [])
            if new_products:
                for product in new_products:
                    cart_item = instance.cartitem_set.all().filter(product=product)
                    if cart_item:
                        cart_item = cart_item[0]
                        cart_item.count += 1
                        cart_item.save()
                    else:
                        instance.products.add(product)
            instance.status = validated_data.get('status', instance.status)
            if instance.status == Cart.Status.ORDERED:
                instance.order_date = now()
            instance.save()
        return instance

    def get_products_with_count(self, obj):
        cart_item_list = obj.cartitem_set.all()
        cart_item_dic_list = []
        for cart_item in cart_item_list:
            cart_item_dic_list.append({'id': cart_item.product.id, 'name': cart_item.product.name,
                                       'count': cart_item.count, 'url': cart_item.product.get_absolute_url()})
        return cart_item_dic_list

    def get_url(self, obj):
        return obj.get_absolute_url()


class ProductListSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField('get_url', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'rate', 'url']

    def get_url(self, obj):
        return obj.get_absolute_url()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    type = serializers.ChoiceField(choices=['admin', 'delivery', 'costumer'], required=False, write_only=True)
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'type']
        write_only_fields = ['password', 'password2', 'type']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "password fields didn't match"})
        return attrs

    def create(self, validated_data):
        if self.context['request'].user.is_superuser:
            user_type = validated_data.get('type', None)
            if user_type == 'admin':
                user = User.objects.create_superuser(username=validated_data['username'])
            elif user_type == 'delivery':
                user = User.objects.create_user(username=validated_data['username'])
                group, _ = Group.objects.get_or_create(name='delivery')
                user.groups.add(group)
            else:
                user = User.objects.create_user(username=validated_data['username'])
        else:
            user = User.objects.create_user(username=validated_data['username'])
        user.set_password(validated_data['password'])
        user.email = validated_data['email']
        user.save()
        return user


class CartAdminSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), write_only=True, required=False)
    url = serializers.SerializerMethodField('get_url', read_only=True)
    products_with_count = serializers.SerializerMethodField('get_products_with_count', read_only=True)
    customer = serializers.PrimaryKeyRelatedField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = Cart
        fields = ['id', 'customer', 'products', 'status', 'order_date', 'products_with_count', 'url']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['products'] = data.pop('products_with_count')
        return data

    def validate(self, attrs):
        if self.context['request'].method == 'post' and attrs.get('customer', None) is None:
            raise serializers.ValidationError('customer field is required for post requests')
        return attrs

    def create(self, validated_data):
        cart = Cart()
        user = validated_data['customer']
        cart.customer = user
        cart.save()
        products = validated_data.get('products', [])
        if not products:
            raise serializers.ValidationError({'products': 'at least 1 product must be add'})
        for product in products:
            cart_item = cart.cartitem_set.all().filter(product=product)
            if cart_item:
                cart_item = cart_item[0]
                cart_item.count += 1
                cart_item.save()
            else:
                cart.products.add(product)
        cart.status = Cart.Status(validated_data.get('status', Cart.Status.DRAFT.value))
        if cart.status == Cart.Status.ORDERED:
            cart.order_date = now()
        cart.save()
        return cart

    def update(self, instance, validated_data):
        with LockManager(f'cart_{instance.pk}'):
            products = validated_data.get('products', [])
            if products:
                instance.products.clear()
                for product in products:
                    cart_item = instance.cartitem_set.all().filter(product=product)
                    if cart_item:
                        cart_item = cart_item[0]
                        cart_item.count += 1
                        cart_item.save()
                    else:
                        instance.products.add(product)
            instance.status = validated_data.get('status', instance.status)
            if instance.status == Cart.Status.ORDERED:
                instance.order_date = now()
            instance.customer = validated_data.get('customer', instance.customer)
            instance.save()
        return instance

    def get_products_with_count(self, obj):
        cart_item_list = obj.cartitem_set.all()
        cart_item_dic_list = []
        for cart_item in cart_item_list:
            cart_item_dic_list.append({'id': cart_item.product.id, 'name': cart_item.product.name,
                                       'count': cart_item.count, 'url': cart_item.product.get_absolute_url()})
        return cart_item_dic_list

    def get_url(self, obj):
        return reverse('RUD-cart-admin', kwargs={'pk': obj.pk})


class DeliveryCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ['customer', 'id', 'status']
        read_only_fields = ['customer', 'id']

    def update(self, instance, validated_data):
        with LockManager(f'cart_{instance.pk}'):
            if instance.status != Cart.Status.ON_WAY and instance.status != Cart.Status.RECEIVED:
                raise serializers.ValidationError('you can\'t update the cart in the current status')
            status = validated_data.get('status', Cart.Status.DELIVERED)
            if status != Cart.Status.DELIVERED:
                raise serializers.ValidationError('you are not allow to update to that status')
            if instance.status == Cart.Status.ON_WAY:
                instance.status = Cart.Status.DELIVERED
            else:
                instance.status = Cart.Status.APPROVED
            instance.save()
        return instance


class RetrieveUserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['username', 'user_type', 'id']
        read_only_fields = ['username', 'user_type', 'id']

    def get_user_type(self, obj):
        if obj.is_superuser:
            return 'admin'
        elif obj.groups.filter(name='delivery').exists():
            return 'delivery'
        else:
            return 'customer'
