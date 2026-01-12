from django import forms
from .models import Profil

class ProfilForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['boy', 'kilo'] # Sadece bu alanları değiştirebilsin
        widgets = {
            'boy': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Boyunuz (cm)'}),
            'kilo': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Kilonuz (kg)'}),
        }