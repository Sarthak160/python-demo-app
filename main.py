import os
import sys
import json
from django.conf import settings
from django.core.management import execute_from_command_line

# --- 1. Configure Django FIRST ---
# This must be done before importing any other Django modules.
settings.configure(
    DEBUG=True,
    SECRET_KEY='a-secret-key-for-development',
    ROOT_URLCONF=__name__,
    DATABASES={
        # Default to SQLite for easy local setup. It will create a db.sqlite3 file.
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        }
        # --- To use MySQL instead, comment out the section above and uncomment this one ---
        # 'default': {
        #     'ENGINE': 'django.db.backends.mysql',
        #     'NAME': os.getenv("DB_NAME", "demo"),
        #     'USER': os.getenv("DB_USER", "demo"),
        #     'PASSWORD': os.getenv("DB_PASSWORD", "demopass"),
        #     'HOST': os.getenv("DB_HOST", "127.0.0.1"),
        #     'PORT': os.getenv("DB_PORT", 3306),
        # }
    },
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'rest_framework',
        'rest_framework_simplejwt',
        'rest_framework_simplejwt.token_blacklist',
        '__main__', # Refers to this file
    ],
)

# --- 2. Import Django modules AFTER configuration ---
from django.db import models
from django.http import JsonResponse
from django.urls import path, include
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# --- 3. Database Models ---
# These models mimic the structure from your queries (Clients, Accounts, Permissions).

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Submodule(models.Model):
    name = models.CharField(max_length=100, unique=True)

class SubmodulePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    submodule = models.ForeignKey(Submodule, on_delete=models.CASCADE)
    can_read = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)

class Client(models.Model):
    display_name = models.CharField(max_length=200)
    client_status = models.CharField(max_length=50, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

class Account(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='accounts')
    account_no_dataphile = models.CharField(max_length=100, null=True, blank=True)
    account_status = models.CharField(max_length=50, default='Open')
    market_value = models.DecimalField(max_digits=20, decimal_places=2)

# --- 4. API Serializers (for converting data to/from JSON) ---

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'display_name', 'client_status', 'created_at']

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'client', 'account_no_dataphile', 'account_status', 'market_value']

# --- 5. API Views (The logic for your endpoints) ---

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user_roles = Role.objects.filter(name__in=['portfolio_manager', 'admin'])
        SubmodulePermission.objects.filter(role__in=user_roles, submodule__name='ClientsViewSet').exists()
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def detailed_info(self, request, pk=None):
        client = self.get_object()
        unlinked_accounts = Account.objects.filter(client_id=client.id, account_no_dataphile__isnull=True)
        linked_accounts = Account.objects.filter(client_id=client.id, account_no_dataphile__isnull=False)
        clients_with_high_value_accounts = Client.objects.filter(
            id__in=Account.objects.filter(market_value__gt=50000).values('client_id')
        )
        return JsonResponse({
            "client_name": client.display_name,
            "unlinked_count": unlinked_accounts.count(),
            "linked_count": linked_accounts.count(),
            "other_high_value_client_count": clients_with_high_value_accounts.count(),
        })

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

# --- 6. URL Routing ---
router = routers.DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'accounts', AccountViewSet, basename='account')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# --- 7. Main execution block ---
if __name__ == "__main__":
    # Create the database tables on first run.
    execute_from_command_line([sys.argv[0], 'makemigrations', os.path.basename(__file__).replace(".py", "")])
    execute_from_command_line([sys.argv[0], 'migrate'])

    # Create a default user, roles, and permissions for testing
    if not User.objects.filter(username='testuser').exists():
        User.objects.create_user('testuser', 'test@example.com', 'testpass123')
        admin_role, _ = Role.objects.get_or_create(name='admin')
        pm_role, _ = Role.objects.get_or_create(name='portfolio_manager')
        clients_submodule, _ = Submodule.objects.get_or_create(name='ClientsViewSet')
        SubmodulePermission.objects.get_or_create(role=admin_role, submodule=clients_submodule, defaults={'can_read': True, 'can_write': True})
        SubmodulePermission.objects.get_or_create(role=pm_role, submodule=clients_submodule, defaults={'can_read': True, 'can_write': False})
        print("Created default user, roles, and permissions.")

    print("Starting development server at http://127.0.0.1:8000/")
    execute_from_command_line([sys.argv[0], 'runserver', '0.0.0.0:8000'])
