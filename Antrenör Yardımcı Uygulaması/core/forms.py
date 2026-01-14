from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profil, Egzersiz, AntrenorProfil

# --- 1. KULLANICI TEMEL BİLGİ FORMU (İsim, Soyisim, Kullanıcı Adı) ---
class KullaniciGuncellemeForm(forms.ModelForm):
    username = forms.CharField(label="Kullanıcı Adı", help_text="Benzersiz olmalıdır.")
    first_name = forms.CharField(label="İsim")
    last_name = forms.CharField(label="Soyisim")
    email = forms.EmailField(label="E-Posta", required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    # Kullanıcı adı kontrolü (Başka biri almış mı?)
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Kendisi hariç bu kullanıcı adını kullanan başkası var mı?
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bu kullanıcı adı zaten kullanımda. Lütfen başka bir tane seçin.")
        return username

# --- 2. ÖĞRENCİ FİZİKSEL BİLGİ FORMU ---
class OgrenciProfilForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['boy', 'kilo', 'yas']

# --- 3. ANTRENÖR PROFİL FORMU ---
class AntrenorProfilForm(forms.ModelForm):
    class Meta:
        model = AntrenorProfil
        fields = ['yas', 'uzmanlik_alani']

# --- 4. EGZERSİZ FORMU (Kütüphane İçin) ---
class EgzersizForm(forms.ModelForm):
    class Meta:
        model = Egzersiz
        fields = ['isim', 'aciklama', 'video_link']