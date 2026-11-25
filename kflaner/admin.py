from decimal import Decimal
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.db.models import QuerySet
from django.core.exceptions import NON_FIELD_ERRORS
from django.http import HttpRequest

from kflaner.controllers.products import product_use_cases
from kflaner.domain.errors import DomainError, ValidationError
from kflaner.domain.products import ProductDraft
from kflaner.models import Product, Purchase, User


class UserCreationForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserEditForm
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")
    list_display = ("email", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Особисті дані", {"fields": ("first_name", "last_name")}),
        ("Роль і доступ", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Дати", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "role", "usable_password", "password1", "password2")}),
    )


MINOR_UNITS_PER_MAJOR = 100
FORM_FIELD_BY_DRAFT_FIELD = {"price_amount": "price"}


class ProductForm(forms.ModelForm):
    price = forms.DecimalField(label="Ціна", min_value=Decimal("0"), max_digits=14, decimal_places=2)


    class Meta:
        model = Product
        fields = ("name", "description", "currency")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.initial["price"] = Decimal(self.instance.price_amount) / MINOR_UNITS_PER_MAJOR

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        if self.errors:
            return cleaned
        draft = ProductDraft(
            name=cleaned["name"],
            description=cleaned.get("description", ""),
            price_amount=int(cleaned["price"] * MINOR_UNITS_PER_MAJOR),
            currency=cleaned["currency"],
        )
        # The remote write happens during validation so that a payment-manager rejection is shown
        # on the form instead of crashing the admin after the local object was already saved.
        try:
            if self.instance._state.adding:
                product = product_use_cases.create_product(draft)
            else:
                product = product_use_cases.edit_product(self.instance.id, draft)
        except ValidationError as error:
            field = FORM_FIELD_BY_DRAFT_FIELD.get(error.field, error.field)
            raise forms.ValidationError({field if field in self.fields else NON_FIELD_ERRORS: error.message})
        except DomainError as error:
            raise forms.ValidationError(f"Payment manager: {error.message}")
        self.instance.id = product.id
        self.instance._state.adding = False
        cleaned.update(name=product.name, description=product.description, currency=product.currency)
        return cleaned


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ("name", "price_display", "currency", "updated_at")
    search_fields = ("name", "id")
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "name", "description", "price", "currency", "created_at", "updated_at")

    def save_model(self, request: HttpRequest, obj: Product, form: ProductForm, change: bool) -> None:
        # Already created in payment-manager and mirrored locally by ProductForm.clean().
        pass

    def delete_model(self, request: HttpRequest, obj: Product) -> None:
        self._delete(request, obj)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        for product in queryset:
            self._delete(request, product)

    def _delete(self, request: HttpRequest, product: Product) -> None:
        try:
            product_use_cases.delete_product(product.id)
        except DomainError as error:
            self.message_user(request, f"«{product}» не видалено: {error.message}", messages.ERROR)

    @admin.display(description="Ціна", ordering="price_amount")
    def price_display(self, product: Product) -> str:
        return f"{Decimal(product.price_amount) / MINOR_UNITS_PER_MAJOR:.2f}"


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "unit_amount", "currency", "purchased_at", "payment_id")
    list_filter = ("product",)
    search_fields = ("user__email", "product__name", "payment_id")
    list_select_related = ("user", "product")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Purchase | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Purchase | None = None) -> bool:
        return False
