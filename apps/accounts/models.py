from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Plano(models.TextChoices):
    FREE = "free", "Gratuito"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    plano = models.CharField(max_length=20, choices=Plano.choices, default=Plano.FREE)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.plano})"

    @property
    def is_pro(self):
        return self.plano in (Plano.PRO, Plano.ENTERPRISE)

    @property
    def limite_imoveis(self):
        return None if self.is_pro else 5


@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def salvar_perfil(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()
