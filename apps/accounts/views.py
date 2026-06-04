from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm, LoginForm, PerfilForm


def registro(request):
    if request.user.is_authenticated:
        return redirect("kanban")
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.first_name}! Conta criada com sucesso.")
            return redirect("kanban")
    else:
        form = RegistroForm()
    return render(request, "accounts/registro.html", {"form": form})


def entrar(request):
    if request.user.is_authenticated:
        return redirect("kanban")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next", "kanban")
            return redirect(next_url)
        messages.error(request, "E-mail ou senha inválidos.")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


def sair(request):
    logout(request)
    return redirect("entrar")


@login_required
def perfil(request):
    profile = request.user.profile
    if request.method == "POST":
        form = PerfilForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso.")
            return redirect("perfil")
    else:
        form = PerfilForm(instance=profile)
    return render(request, "accounts/perfil.html", {"form": form})
