from django import forms

from .models import Subject


class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject

        fields = [
            "name",
            "description",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Python"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to learn?"
                }
            ),
        }