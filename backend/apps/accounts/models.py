from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser requires is_staff and is_superuser")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    def __str__(self):
        return self.email


class AthleteProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="athlete_profile")
    organization = models.ForeignKey("catalogs.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="athletes")


class UserRole(models.Model):
    class Role(models.TextChoices):
        FEDERATION = "federation", "Federation"
        ATHLETE = "athlete", "Athlete"
        COACH = "coach", "Coach"
        JUDGE = "judge", "Judge"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.CharField(max_length=16, choices=Role.choices)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "role"], name="unique_user_role")]


class Guardian(models.Model):
    minor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guardians")
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100)
    confirmation_status = models.CharField(max_length=32, default="pending_verification")
    recorded_at = models.DateTimeField(default=timezone.now)


class PersonalDataConsent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    text_version = models.CharField(max_length=40)
    confirmation_method = models.CharField(max_length=40, default="registration_checkbox")
    guardian = models.ForeignKey(Guardian, null=True, blank=True, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)


def has_current_consent(user):
    latest = PersonalDataConsent.objects.filter(user=user).order_by("-recorded_at", "-pk").first()
    return latest is not None and latest.revoked_at is None
