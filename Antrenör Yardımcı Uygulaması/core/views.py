from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import Gorev, Profil
import datetime

from .forms import ProfilForm
# --- YENİ EKLENEN: GİRİŞ YAPMA FONKSİYONU ---
def giris_yap(request):
    if request.user.is_authenticated:
        # Zaten giriş yapmışsa rolüne göre yönlendir
        if request.user.is_staff:
            return redirect('/admin/')
        return redirect('ogrenci_paneli')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Antrenör (Admin/Staff) ise Admin paneline gönder
                if user.is_staff:
                    return redirect('/admin/')
                # Değilse Öğrenci Paneline gönder
                return redirect('ogrenci_paneli')
        else:
            messages.error(request, "Hatalı kullanıcı adı veya şifre.")
    else:
        form = AuthenticationForm()

    return render(request, 'giris.html', {'form': form})

# --- YENİ EKLENEN: ÇIKIŞ YAPMA FONKSİYONU ---
def cikis_yap(request):
    logout(request)
    return redirect('giris_yap')

# --- GÜNCELLENEN: ÖĞRENCİ PANELİ ---
def ogrenci_paneli(request):
    # Eğer giriş yapmamışsa direkt giriş sayfasına at
    if not request.user.is_authenticated:
        return redirect('giris_yap')

    aktif_kullanici = request.user
    bugun = datetime.date.today()

    # --- KAYDETME İŞLEMİ (POST) ---
    if request.method == "POST":
        secilen_id_listesi = request.POST.getlist('yapilanlar')
        bugunku_tum_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun)
        
        try:
            profil = Profil.objects.get(user=aktif_kullanici)
        except Profil.DoesNotExist:
            profil = None

        for gorev in bugunku_tum_gorevler:
            str_id = str(gorev.id)
            if str_id in secilen_id_listesi:
                if not gorev.yapildi_mi: 
                    gorev.yapildi_mi = True
                    gorev.save()
                    if profil: profil.yildiz_bakiyesi += 1
            else:
                if gorev.yapildi_mi:
                    gorev.yapildi_mi = False
                    gorev.save()
                    if profil: profil.yildiz_bakiyesi -= 1
        
        if profil: profil.save()
        return redirect('ogrenci_paneli')

    # --- GÖRÜNTÜLEME İŞLEMİ (GET) ---
    tum_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun)
    antrenmanlar = tum_gorevler.filter(tur='ANTREMAN')
    beslenmeler = tum_gorevler.filter(tur='BESLENME')
    
    yildiz_sayisi = 0
    if hasattr(aktif_kullanici, 'profil'):
        yildiz_sayisi = aktif_kullanici.profil.yildiz_bakiyesi

    return render(request, 'ogrenci_paneli.html', {
        'antrenmanlar': antrenmanlar,
        'beslenmeler': beslenmeler,
        'yildiz_sayisi': yildiz_sayisi
    })
def profil_duzenle(request):
    if not request.user.is_authenticated:
        return redirect('giris_yap')

    # Kullanıcının profilini al, yoksa oluştur (Hata almamak için)
    profil, created = Profil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfilForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            return redirect('ogrenci_paneli') # Kaydedince panele dön
    else:
        form = ProfilForm(instance=profil) # Mevcut bilgileri formun içine doldur

    return render(request, 'profil_duzenle.html', {'form': form})
