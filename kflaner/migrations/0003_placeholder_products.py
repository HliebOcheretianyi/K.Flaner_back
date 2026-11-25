from django.db import migrations

PLACEHOLDER_PRODUCTS = [
    ("eff94a41-f65e-4e04-8e3c-f6feec61391b", "К. Фланер №1 — цифровий випуск", "PDF першого випуску часопису.", 10000),
    ("f6c160cd-08d9-4a60-ba3b-750aa2c743d2", "К. Фланер №2 — цифровий випуск", "PDF другого випуску часопису.", 12000),
    ("b35b8e13-2c72-42cf-81b9-5dcec1627cc5", "К. Фланер №1 — друкований випуск", "Друкований примірник першого випуску.", 25000),
    ("78954c99-940b-46e6-91e3-eaffdac0b5ed", "Футболка «К. Фланер»", "Бавовняна футболка з логотипом часопису.", 60000),
    ("e762bde0-249d-48ac-8ee8-03fbbfeb032d", "Торба «К. Фланер»", "Полотняна торба з логотипом часопису.", 35000),
    ("91308d6d-18bf-47ec-9de0-d8f519931d41", "Тестовий продукт", "Для перевірки оплати.", 100),
]


def create_placeholder_products(apps, schema_editor):
    Product = apps.get_model("kflaner", "Product")
    for product_id, name, description, price_amount in PLACEHOLDER_PRODUCTS:
        Product.objects.get_or_create(
            id=product_id,
            defaults={"name": name, "description": description, "price_amount": price_amount, "currency": "UAH"},
        )


def delete_placeholder_products(apps, schema_editor):
    Product = apps.get_model("kflaner", "Product")
    Product.objects.filter(id__in=[product_id for product_id, *_ in PLACEHOLDER_PRODUCTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("kflaner", "0002_products_and_purchases"),
    ]

    operations = [
        migrations.RunPython(create_placeholder_products, delete_placeholder_products),
    ]
