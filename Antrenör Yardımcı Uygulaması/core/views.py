from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q 
from .models import Gorev, Profil, AntrenorProfil, Davet, Egzersiz, AntrenmanHareket, Mesaj
from .forms import ProfilForm, EgzersizForm
import datetime
import google.generativeai as genai
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

# --- 1. GİRİŞ YAPMA ---
def giris_yap(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'antrenor_profili'):
            return redirect('antrenor_paneli')
        return redirect('ogrenci_paneli')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if hasattr(user, 'antrenor_profili'):
                    return redirect('antrenor_paneli')
                else:
                    return redirect('ogrenci_paneli')
        else:
            messages.error(request, "Hatalı kullanıcı adı veya şifre.")
    else:
        form = AuthenticationForm()

    return render(request, 'giris.html', {'form': form})


# --- 2. ÇIKIŞ YAPMA ---
def cikis_yap(request):
    logout(request)
    return redirect('giris_yap')


# --- 3. KAYIT OLMA ---
def kayit_ol(request):
    if request.user.is_authenticated:
        return redirect('ogrenci_paneli')

    if request.method == "POST":
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')
        isim = request.POST.get('first_name')
        soyisim = request.POST.get('last_name')
        rol = request.POST.get('rol_secimi') 

        if User.objects.filter(username=kullanici_adi).exists():
            return render(request, 'kayit_ol.html', {'hata': 'Bu kullanıcı adı zaten alınmış.'})

        yeni_user = User.objects.create_user(username=kullanici_adi, password=sifre)
        yeni_user.first_name = isim
        yeni_user.last_name = soyisim
        
        if rol == 'antrenor':
            yeni_user.is_staff = True 
        
        yeni_user.save()

        if rol == 'ogrenci':
            boy = request.POST.get('boy')
            kilo = request.POST.get('kilo')
            yas = request.POST.get('yas_ogrenci')
            Profil.objects.create(user=yeni_user, boy=boy, kilo=kilo, yas=yas)
        
        elif rol == 'antrenor':
            yas = request.POST.get('yas_antrenor')
            uzmanlik = request.POST.get('uzmanlik')
            AntrenorProfil.objects.create(user=yeni_user, yas=yas, uzmanlik_alani=uzmanlik)

        return redirect('giris_yap')

    return render(request, 'kayit_ol.html')


# --- 4. ÖĞRENCİ PANELİ ---
def ogrenci_paneli(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    if hasattr(request.user, 'antrenor_profili'): return redirect('antrenor_paneli')

    aktif_kullanici = request.user
    bugun = datetime.date.today()

    # -- A) DAVET CEVAPLAMA --
    if request.method == "POST" and 'davet_cevap' in request.POST:
        davet_id = request.POST.get('davet_id')
        cevap = request.POST.get('cevap')
        try:
            davet = Davet.objects.get(id=davet_id, alici=aktif_kullanici)
            if cevap == 'kabul':
                davet.durum = 'KABUL'
                davet.save()
                profil = aktif_kullanici.profil
                profil.antrenor = davet.gonderen
                profil.save()
                messages.success(request, f"{davet.gonderen.user.first_name} hocanın takımına katıldın!")
            else:
                davet.durum = 'RED'
                davet.save()
        except Davet.DoesNotExist: pass
        return redirect('ogrenci_paneli')

    # -- B) BUGÜNKÜ GÖREVLERİ ÇEK --
    bugunku_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun).exclude(durum='TAMAMLANDI')
    
    antrenman_gorevi = bugunku_gorevler.filter(tur='ANTREMAN').first()
    beslenme_gorevi = bugunku_gorevler.filter(tur='BESLENME').first()

    # -- C) GÜNÜ BİTİR VE GÖNDER (RAPORLAMA) --
    if request.method == "POST" and 'gunu_bitir' in request.POST:
        if antrenman_gorevi:
            secilen_hareketler = request.POST.getlist('hareket_id[]')
            for hareket in antrenman_gorevi.hareketler.all():
                hareket.yapildi_mi = False
                hareket.save()
            for h_id in secilen_hareketler:
                h = AntrenmanHareket.objects.get(id=h_id)
                h.yapildi_mi = True
                h.save()
            antrenman_gorevi.durum = 'ONAY_BEKLIYOR'
            antrenman_gorevi.save()

        if beslenme_gorevi:
            beslenme_yapildi = request.POST.get('beslenme_durum') == 'on'
            beslenme_gorevi.yapildi_mi = beslenme_yapildi
            beslenme_gorevi.durum = 'ONAY_BEKLIYOR'
            beslenme_gorevi.save()

        messages.success(request, "Raporun antrenörüne gönderildi, onay bekleniyor.")
        return redirect('ogrenci_paneli')

    # -- D) CONTEXT VERİLERİ --
    yildiz_sayisi = 0
    gelen_davetler = []
    
    if hasattr(aktif_kullanici, 'profil'):
        yildiz_sayisi = aktif_kullanici.profil.yildiz_bakiyesi
        gelen_davetler = Davet.objects.filter(alici=aktif_kullanici, durum='BEKLIYOR')

    # -- E) BİLDİRİM HESAPLAMA (YENİ) --
    okunmamis_mesaj = Mesaj.objects.filter(alici=aktif_kullanici, okundu_mu=False).count()

    return render(request, 'ogrenci_paneli.html', {
        'antrenman_gorevi': antrenman_gorevi,
        'beslenme_gorevi': beslenme_gorevi,
        'yildiz_sayisi': yildiz_sayisi,
        'davetler': gelen_davetler,
        'okunmamis_mesaj': okunmamis_mesaj # Template'e gönderiyoruz
    })


# --- 5. PROFİL DÜZENLEME ---
def profil_duzenle(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    profil, created = Profil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfilForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            return redirect('ogrenci_paneli')
    else:
        form = ProfilForm(instance=profil)

    return render(request, 'profil_duzenle.html', {'form': form})


# --- 6. ANTRENÖR PANELİ ---
def antrenor_paneli(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        aktif_antrenor = request.user.antrenor_profili
    except:
        return redirect('ogrenci_paneli')

    # -- A) ÖĞRENCİ ARAMA VE DAVET --
    arama_sonuclari = []
    aranan_isim = ""

    if request.method == "POST":
        if 'arama_yap' in request.POST:
            aranan_isim = request.POST.get('ogrenci_adi')
            if aranan_isim:
                arama_sonuclari = Profil.objects.filter(user__username__icontains=aranan_isim, antrenor__isnull=True)
        
        elif 'davet_gonder' in request.POST:
            hedef_id = request.POST.get('hedef_user_id')
            hedef_user = User.objects.get(id=hedef_id)
            if not Davet.objects.filter(gonderen=aktif_antrenor, alici=hedef_user, durum='BEKLIYOR').exists():
                Davet.objects.create(gonderen=aktif_antrenor, alici=hedef_user)
                messages.success(request, f"{hedef_user.username} kullanıcısına davet gönderildi.")
            else:
                messages.warning(request, "Zaten bekleyen bir davet var.")

    # -- B) LİSTELER --
    benim_ogrencilerim = aktif_antrenor.ogrenciler.all()

    # -- C) RAPORLARI GRUPLAMA --
    bekleyen_tum_gorevler = Gorev.objects.filter(
        ogrenci__profil__antrenor=aktif_antrenor, 
        durum='ONAY_BEKLIYOR'
    ).order_by('-tarih')

    onay_bekleyenler = []
    eklenen_kontrol = set()

    for gorev in bekleyen_tum_gorevler:
        anahtar = (gorev.ogrenci.id, gorev.tarih)
        if anahtar not in eklenen_kontrol:
            onay_bekleyenler.append(gorev)
            eklenen_kontrol.add(anahtar)

    # -- D) BİLDİRİM HESAPLAMA (YENİ - EKSİK OLAN KISIM BUYDU) --
    okunmamis_mesaj = Mesaj.objects.filter(alici=request.user, okundu_mu=False).count()

    return render(request, 'antrenor_paneli.html', {
        'ogrenciler': benim_ogrencilerim,
        'arama_sonuclari': arama_sonuclari,
        'aranan_isim': aranan_isim,
        'onay_bekleyenler': onay_bekleyenler,
        'okunmamis_mesaj': okunmamis_mesaj # Template'e gönderiyoruz
    })


# --- 7. EGZERSİZ KÜTÜPHANESİ ---
def egzersiz_kutuphanesi(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    try:
        antrenor = request.user.antrenor_profili
    except:
        return redirect('ogrenci_paneli')

    if request.method == 'POST':
        form = EgzersizForm(request.POST)
        if form.is_valid():
            egzersiz = form.save(commit=False)
            egzersiz.olusturan = antrenor
            egzersiz.save()
            messages.success(request, "Egzersiz eklendi.")
            return redirect('egzersiz_kutuphanesi')
    else:
        form = EgzersizForm()

    egzersizler = Egzersiz.objects.filter(olusturan=antrenor).order_by('-olusturulma_tarihi')
    return render(request, 'egzersiz_kutuphanesi.html', {'form': form, 'egzersizler': egzersizler})

def egzersiz_sil(request, id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    egzersiz = get_object_or_404(Egzersiz, id=id, olusturan=request.user.antrenor_profili)
    egzersiz.delete()
    messages.info(request, "Egzersiz silindi.")
    return redirect('egzersiz_kutuphanesi')

def egzersiz_duzenle(request, id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    egzersiz = get_object_or_404(Egzersiz, id=id, olusturan=request.user.antrenor_profili)
    if request.method == 'POST':
        form = EgzersizForm(request.POST, instance=egzersiz)
        if form.is_valid():
            form.save()
            return redirect('egzersiz_kutuphanesi')
    else:
        form = EgzersizForm(instance=egzersiz)
    return render(request, 'egzersiz_duzenle.html', {'form': form})


# --- 8. ÖĞRENCİ YÖNET (GÖREV ATAMA) ---
def ogrenci_yonet(request, ogrenci_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        antrenor = request.user.antrenor_profili
        ogrenci_profili = Profil.objects.get(user__id=ogrenci_id, antrenor=antrenor)
        ogrenci_user = ogrenci_profili.user
    except:
        return redirect('antrenor_paneli')

    if request.method == 'POST':
        tarih = datetime.date.today()
        
        egzersiz_ids = request.POST.getlist('egzersiz_id[]')
        sets = request.POST.getlist('set[]')
        reps = request.POST.getlist('rep[]')
        
        if egzersiz_ids:
            antrenman_gorevi = Gorev.objects.create(
                ogrenci=ogrenci_user,
                baslik="GÜNLÜK ANTRENMAN PLANI",
                aciklama="Antrenörün senin için detaylı bir plan oluşturdu.",
                tur='ANTREMAN',
                tarih=tarih,
                durum='ATANDI'
            )
            for i in range(len(egzersiz_ids)):
                AntrenmanHareket.objects.create(
                    gorev=antrenman_gorevi,
                    egzersiz_id=egzersiz_ids[i],
                    set_sayisi=sets[i],
                    tekrar_sayisi=reps[i]
                )

        beslenme_notu = request.POST.get('beslenme_notu')
        if beslenme_notu and beslenme_notu.strip():
            Gorev.objects.create(
                ogrenci=ogrenci_user,
                baslik="BESLENME PROGRAMI",
                aciklama=beslenme_notu,
                tur='BESLENME',
                tarih=tarih,
                durum='ATANDI'
            )
            
        messages.success(request, "Plan başarıyla gönderildi!")
        return redirect('antrenor_paneli')

    kutuphane = Egzersiz.objects.filter(olusturan=antrenor).order_by('isim')
    return render(request, 'ogrenci_yonet.html', {'ogrenci': ogrenci_user, 'kutuphane': kutuphane})


# --- 9. ÖĞRENCİ KONTROL VE ONAY ---
def ogrenci_kontrol(request, gorev_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    baz_gorev = get_object_or_404(Gorev, id=gorev_id)
    if baz_gorev.ogrenci.profil.antrenor != request.user.antrenor_profili:
        return redirect('antrenor_paneli')

    o_gunku_gorevler = Gorev.objects.filter(ogrenci=baz_gorev.ogrenci, tarih=baz_gorev.tarih)
    antrenman_gorevi = o_gunku_gorevler.filter(tur='ANTREMAN').first()
    beslenme_gorevi = o_gunku_gorevler.filter(tur='BESLENME').first()

    if request.method == 'POST':
        yildiz_miktari = int(request.POST.get('yildiz_miktari', 0))
        profil = baz_gorev.ogrenci.profil
        profil.yildiz_bakiyesi += yildiz_miktari
        profil.save()
        
        bekleyenler = o_gunku_gorevler.filter(durum='ONAY_BEKLIYOR')
        for g in bekleyenler:
            g.durum = 'TAMAMLANDI'
            g.save()

        messages.success(request, f"Günlük rapor onaylandı, {yildiz_miktari} yıldız gönderildi.")
        return redirect('antrenor_paneli')

    return render(request, 'ogrenci_kontrol.html', {
        'ogrenci': baz_gorev.ogrenci,
        'tarih': baz_gorev.tarih,
        'antrenman': antrenman_gorevi,
        'beslenme': beslenme_gorevi
    })


# --- 10. MESAJLAŞMA SİSTEMİ (YENİ) ---
def mesaj_kutusu(request):
    """Sadece Antrenörler için: Mesajlaştığı öğrencilerin listesi"""
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        antrenor = request.user.antrenor_profili
    except:
        # Öğrenciyse direkt kendi hocasıyla sohbete gitsin
        if hasattr(request.user, 'profil') and request.user.profil.antrenor:
            hoca_id = request.user.profil.antrenor.user.id
            return redirect('sohbet_odasi', user_id=hoca_id)
        return redirect('ogrenci_paneli')

    ogrenciler = antrenor.ogrenciler.all()
    sohbet_listesi = []

    for ogr in ogrenciler:
        son_mesaj = Mesaj.objects.filter(
            (Q(gonderen=request.user) & Q(alici=ogr.user)) |
            (Q(gonderen=ogr.user) & Q(alici=request.user))
        ).last()
        
        okunmamis = Mesaj.objects.filter(gonderen=ogr.user, alici=request.user, okundu_mu=False).count()
        
        sohbet_listesi.append({
            'user': ogr.user,
            'son_mesaj': son_mesaj,
            'okunmamis': okunmamis
        })

    return render(request, 'mesaj_kutusu.html', {'sohbet_listesi': sohbet_listesi})


def sohbet_odasi(request, user_id):
    """Hem Öğrenci Hem Antrenör için Ortak Sohbet Ekranı"""
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    karshi_taraf = get_object_or_404(User, id=user_id)
    ben = request.user

    # YETKİ KONTROLÜ
    izin_var = False
    if hasattr(ben, 'profil'):
        if ben.profil.antrenor and ben.profil.antrenor.user == karshi_taraf:
            izin_var = True
    elif hasattr(ben, 'antrenor_profili'):
        if ben.antrenor_profili.ogrenciler.filter(user=karshi_taraf).exists():
            izin_var = True
            
    if not izin_var:
        messages.error(request, "Bu kişiyle mesajlaşma yetkiniz yok.")
        if hasattr(ben, 'antrenor_profili'): return redirect('mesaj_kutusu')
        return redirect('ogrenci_paneli')

    # MESAJ GÖNDERME
    if request.method == "POST":
        icerik = request.POST.get('mesaj_icerigi')
        if icerik and icerik.strip():
            Mesaj.objects.create(gonderen=ben, alici=karshi_taraf, icerik=icerik)
            return redirect('sohbet_odasi', user_id=user_id)

    # MESAJLARI GETİR
    mesajlar = Mesaj.objects.filter(
        (Q(gonderen=ben) & Q(alici=karshi_taraf)) |
        (Q(gonderen=karshi_taraf) & Q(alici=ben))
    ).order_by('tarih')

    # OKUNDU İŞARETLE
    okunmamislar = mesajlar.filter(gonderen=karshi_taraf, okundu_mu=False)
    for m in okunmamislar:
        m.okundu_mu = True
        m.save()

    return render(request, 'sohbet.html', {
        'karshi_taraf': karshi_taraf,
        'mesajlar': mesajlar
    })
    
    # --- 11. YAPAY ZEKA ASİSTANI (CHATBOT) ---
@csrf_exempt
def yapay_zeka_sor(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            soru = data.get('mesaj', '')
            
            # API ANAHTARIN (Buraya kendi anahtarını yapıştırmayı unutma!)
            GOOGLE_API_KEY = "AIzaSyCdxC6fWFN_ZfAidntRFwfOIweXSB4PuyI"
            
            genai.configure(api_key=GOOGLE_API_KEY)
            
            # GÜNCELLENEN KISIM: Listendeki en uygun modeli seçtik
            model = genai.GenerativeModel('gemini-flash-latest')
            
            prompt = f"""
            Sen Fitness Pro uygulamasının yardımcı yapay zeka asistanısın.
            Adın "FitBot".
            Sadece fitness, vücut geliştirme, beslenme, diyet ve sağlık konularında sorulara cevap ver.
            Kısa, öz ve motive edici cevaplar ver.
            Eğer konu spor dışındaysa (siyaset, tarih vb.) nazikçe cevap veremeyeceğini söyle.
            
            Kullanıcı Sorusu: {soru}
            """
            
            response = model.generate_content(prompt)
            
            cevap = response.text
            
            return JsonResponse({'cevap': cevap, 'durum': 'basarili'})
            
        except Exception as e:
            # Hatayı terminalde görmek için print ekledik
            print("HATA:", e)
            return JsonResponse({'cevap': f'Bir bağlantı hatası oldu: {str(e)}', 'durum': 'hata'})
            
    return JsonResponse({'error': 'Sadece POST isteği kabul edilir'}, status=400)