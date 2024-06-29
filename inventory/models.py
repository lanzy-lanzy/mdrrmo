from django.db import models, transaction
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError

class Supplier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15, validators=[
        RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    ])
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name

class Part(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    part_number = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name} ({self.part_number})'

class Vehicle(models.Model):
    vin = models.CharField(max_length=17, unique=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField(validators=[MinValueValidator(1886), MaxValueValidator(timezone.now().year)])
    license_plate = models.CharField(max_length=10, unique=True)
    last_maintenance_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.make} {self.model} ({self.license_plate})'

class VehiclePart(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    installed_on = models.DateField()
    mileage = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.part.name} for {self.vehicle.license_plate}'

class PurchaseRequest(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True)  # New field
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    request_date = models.DateTimeField(default=timezone.now)
    approved = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    delivery_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        vehicle_info = f' for {self.vehicle.license_plate}' if self.vehicle else ''
        return f'{self.quantity} x {self.part.name}{vehicle_info}'

class Inventory(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)])

    def __str__(self):
        return f'{self.part.name} - {self.quantity}'

    def update_quantity(self, change):
        self.quantity = models.F('quantity') + change
        self.save()

class Delivery(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE)
    delivery_date = models.DateTimeField(default=timezone.now)
    received = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Delivery for {self.purchase_request.part.name} on {self.delivery_date}'

class Maintenance(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    maintenance_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    performed_by = models.CharField(max_length=100)

    def __str__(self):
        return f'Maintenance for {self.vehicle.license_plate} on {self.maintenance_date}'

@receiver(post_save, sender=Delivery)
def update_inventory_on_delivery(sender, instance, created, **kwargs):
    if created and instance.received:
        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(part=instance.purchase_request.part)
            inventory.update_quantity(instance.purchase_request.quantity)

@receiver(post_save, sender=Maintenance)
def update_inventory_on_maintenance(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(part=instance.part)
            if inventory.quantity > 0:
                inventory.update_quantity(-1)

@receiver(pre_save, sender=PurchaseRequest)
def validate_purchase_request(sender, instance, **kwargs):
    if instance.quantity <= 0:
        raise ValidationError('Quantity must be greater than zero.')

@receiver(post_save, sender=PurchaseRequest)
def handle_purchase_request_approval(sender, instance, created, **kwargs):
    if instance.approved and not instance.delivered:
        # Logic to notify supplier or initiate delivery process
        pass
