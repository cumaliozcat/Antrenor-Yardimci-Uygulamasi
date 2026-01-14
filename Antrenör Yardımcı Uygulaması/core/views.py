from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import Gorev, Profil, AntrenorProfil, Davet
from .forms import ProfilForm
from .models import Egzersiz
from .forms import EgzersizForm
import datetime


# --- 1. GİRİŞ YAPMA ---
def giris_yap(request):
    # Eğer kullanıcı zaten giriş yapmışsa yönlendir
    if request.user.is_authenticated:
        if hasattr(request.user, "antrenor_profili"):
            return redirect("antrenor_paneli")
        return redirect("ogrenci_paneli")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Giriş başarılı, rolüne göre yönlendir
                if hasattr(user, "antrenor_profili"):
                    return redirect("antrenor_paneli")
                else:
                    return redirect("ogrenci_paneli")
        else:
            messages.error(request, "Hatalı kullanıcı adı veya şifre.")
    else:
        form = AuthenticationForm()

    return render(request, "giris.html", {"form": form})


# --- 2. ÇIKIŞ YAPMA ---
def cikis_yap(request):
    logout(request)
    return redirect("giris_yap")


# --- 3. KAYIT OLMA ---
def kayit_ol(request):
    if request.user.is_authenticated:
        return redirect("ogrenci_paneli")

    if request.method == "POST":
        kullanici_adi = request.POST.get("username")
        sifre = request.POST.get("password")
        isim = request.POST.get("first_name")
        soyisim = request.POST.get("last_name")
        rol = request.POST.get("rol_secimi")

        # Kullanıcı adı dolu mu kontrolü
        if User.objects.filter(username=kullanici_adi).exists():
            return render(
                request, "kayit_ol.html", {"hata": "Bu kullanıcı adı zaten alınmış."}
            )

        # Kullanıcıyı oluştur
        yeni_user = User.objects.create_user(username=kullanici_adi, password=sifre)
        yeni_user.first_name = isim
        yeni_user.last_name = soyisim

        # Antrenör ise panele girmesi için staff yetkisi ver (Opsiyonel, kendi panelimiz var artık)
        if rol == "antrenor":
            yeni_user.is_staff = True

        yeni_user.save()

        # Profil oluşturma
        if rol == "ogrenci":
            boy = request.POST.get("boy")
            kilo = request.POST.get("kilo")
            yas = request.POST.get("yas_ogrenci")

            Profil.objects.create(user=yeni_user, boy=boy, kilo=kilo, yas=yas)

        elif rol == "antrenor":
            yas = request.POST.get("yas_antrenor")
            uzmanlik = request.POST.get("uzmanlik")

            AntrenorProfil.objects.create(
                user=yeni_user, yas=yas, uzmanlik_alani=uzmanlik
            )

        return redirect("giris_yap")

    return render(request, "kayit_ol.html")


# --- 4. ÖĞRENCİ PANELİ ---
def ogrenci_paneli(request):
    if request.method == "POST" and "davet_cevap" in request.POST:
        davet_id = request.POST.get("davet_id")
        cevap = request.POST.get("cevap")  # 'kabul' veya 'red'

        davet = Davet.objects.get(id=davet_id)

        if cevap == "kabul":
            davet.durum = "KABUL"
            davet.save()

            # Öğrencinin profilini güncelle: Artık antrenörü bu kişi!
            profil = request.user.profil
            profil.antrenor = davet.gonderen
            profil.save()

            # Diğer tüm bekleyen davetleri sil veya reddet (İsteğe bağlı)
        else:
            davet.durum = "RED"
            davet.save()

        return redirect("ogrenci_paneli")
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    # Antrenörler bu sayfaya giremesin, kendi panellerine gitsin
    if hasattr(request.user, "antrenor_profili"):
        return redirect("antrenor_paneli")

    aktif_kullanici = request.user
    bugun = datetime.date.today()

    # -- A) DAVET CEVAPLAMA (KABUL/RED) --
    if request.method == "POST" and "davet_cevap" in request.POST:
        davet_id = request.POST.get("davet_id")
        cevap = request.POST.get("cevap")  # 'kabul' veya 'red'

        try:
            davet = Davet.objects.get(id=davet_id, alici=aktif_kullanici)
            if cevap == "kabul":
                davet.durum = "KABUL"
                davet.save()

                # Öğrenciyi antrenöre bağla
                profil = aktif_kullanici.profil
                profil.antrenor = davet.gonderen
                profil.save()

                messages.success(
                    request,
                    f"{davet.gonderen.user.first_name} hocanın takımına katıldın!",
                )
            else:
                davet.durum = "RED"
                davet.save()
                messages.info(request, "Davet reddedildi.")
        except Davet.DoesNotExist:
            pass

        return redirect("ogrenci_paneli")

    # -- B) GÖREV TAMAMLAMA İŞLEMLERİ --
    if request.method == "POST" and "yapilanlar" in request.POST:
        secilen_id_listesi = request.POST.getlist("yapilanlar")
        bugunku_tum_gorevler = Gorev.objects.filter(
            ogrenci=aktif_kullanici, tarih=bugun
        )

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
                    if profil:
                        profil.yildiz_bakiyesi += 1
            else:
                if gorev.yapildi_mi:
                    gorev.yapildi_mi = False
                    gorev.save()
                    if profil:
                        profil.yildiz_bakiyesi -= 1

        if profil:
            profil.save()
        return redirect("ogrenci_paneli")

    # -- C) VERİLERİ ÇEKME --
    tum_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun)
    antrenmanlar = tum_gorevler.filter(tur="ANTREMAN")
    beslenmeler = tum_gorevler.filter(tur="BESLENME")

    yildiz_sayisi = 0
    gelen_davetler = []

    if hasattr(aktif_kullanici, "profil"):
        yildiz_sayisi = aktif_kullanici.profil.yildiz_bakiyesi
        # Bekleyen davetleri çek
        gelen_davetler = Davet.objects.filter(alici=aktif_kullanici, durum="BEKLIYOR")

    return render(
        request,
        "ogrenci_paneli.html",
        {
            "antrenmanlar": antrenmanlar,
            "beslenmeler": beslenmeler,
            "yildiz_sayisi": yildiz_sayisi,
            "davetler": gelen_davetler,
        },
    )


# --- 5. PROFİL DÜZENLEME ---
def profil_duzenle(request):
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    profil, created = Profil.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfilForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            return redirect("ogrenci_paneli")
    else:
        form = ProfilForm(instance=profil)

    return render(request, "profil_duzenle.html", {"form": form})


# --- 6. ANTRENÖR PANELİ (YENİ) ---
def antrenor_paneli(request):
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    try:
        aktif_antrenor = request.user.antrenor_profili
    except AntrenorProfil.DoesNotExist:
        # Antrenör değilse öğrenci paneline
        return redirect("ogrenci_paneli")

    arama_sonuclari = []
    aranan_isim = ""

    if request.method == "POST":
        # ÖĞRENCİ ARAMA
        if "arama_yap" in request.POST:
            aranan_isim = request.POST.get("ogrenci_adi")
            if aranan_isim:
                # Antrenörü olmayan (boşta) ve ismi eşleşen öğrencileri bul
                arama_sonuclari = Profil.objects.filter(
                    user__username__icontains=aranan_isim, antrenor__isnull=True
                )

        # DAVET GÖNDERME
        elif "davet_gonder" in request.POST:
            hedef_user_id = request.POST.get("hedef_user_id")
            hedef_user = User.objects.get(id=hedef_user_id)

            # Zaten bekleyen bir davet var mı?
            var_mi = Davet.objects.filter(
                gonderen=aktif_antrenor, alici=hedef_user, durum="BEKLIYOR"
            ).exists()

            if not var_mi:
                Davet.objects.create(gonderen=aktif_antrenor, alici=hedef_user)
                messages.success(
                    request, f"{hedef_user.username} kullanıcısına davet gönderildi."
                )
            else:
                messages.warning(request, "Zaten bekleyen bir davet var.")

    # Benim öğrencilerimi listele
    benim_ogrencilerim = aktif_antrenor.ogrenciler.all()

    return render(
        request,
        "antrenor_paneli.html",
        {
            "ogrenciler": benim_ogrencilerim,
            "arama_sonuclari": arama_sonuclari,
            "aranan_isim": aranan_isim,
        },
    )
    # --- 7. EGZERSİZ KÜTÜPHANESİ LİSTELE & EKLE ---


def egzersiz_kutuphanesi(request):
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    # Sadece antrenörler girebilir
    try:
        antrenor = request.user.antrenor_profili
    except:
        return redirect("ogrenci_paneli")

    # Ekleme İşlemi (POST)
    if request.method == "POST":
        form = EgzersizForm(request.POST)
        if form.is_valid():
            egzersiz = form.save(commit=False)
            egzersiz.olusturan = antrenor  # Egzersizi bu antrenöre bağla
            egzersiz.save()
            messages.success(request, "Yeni egzersiz kütüphanene eklendi!")
            return redirect("egzersiz_kutuphanesi")
    else:
        form = EgzersizForm()

    # Listeleme İşlemi (Sadece bu antrenörün egzersizleri)
    egzersizler = Egzersiz.objects.filter(olusturan=antrenor).order_by(
        "-olusturulma_tarihi"
    )

    return render(
        request, "egzersiz_kutuphanesi.html", {"form": form, "egzersizler": egzersizler}
    )


# --- 8. EGZERSİZ SİL ---
def egzersiz_sil(request, id):
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    # Sadece kendi egzersizini silebilir (Güvenlik)
    egzersiz = get_object_or_404(
        Egzersiz, id=id, olusturan=request.user.antrenor_profili
    )
    egzersiz.delete()
    messages.info(request, "Egzersiz silindi.")
    return redirect("egzersiz_kutuphanesi")


# --- 9. EGZERSİZ DÜZENLE ---
def egzersiz_duzenle(request, id):
    if not request.user.is_authenticated:
        return redirect("giris_yap")

    egzersiz = get_object_or_404(
        Egzersiz, id=id, olusturan=request.user.antrenor_profili
    )

    if request.method == "POST":
        form = EgzersizForm(request.POST, instance=egzersiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Egzersiz güncellendi.")
            return redirect("egzersiz_kutuphanesi")
    else:
        form = EgzersizForm(instance=egzersiz)

    return render(request, "egzersiz_duzenle.html", {"form": form})
