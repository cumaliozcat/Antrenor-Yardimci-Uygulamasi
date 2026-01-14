from django import forms
from .models import Profil, Egzersiz

class ProfilForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['boy', 'kilo'] # Sadece bu alanları değiştirebilsin
        widgets = {
            'boy': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Boyunuz (cm)'}),
            'kilo': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Kilonuz (kg)'}),
        }
class EgzersizForm(forms.ModelForm):
    class Meta:
        model = Egzersiz
        fields = ['isim', 'aciklama', 'video_link']
        widgets = {
            'isim': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Örn: Bench Press'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Hareketin detayları...'}),
            'video_link': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'Youtube video linki (varsa)'}),
        }        
        