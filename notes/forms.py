from django import forms

from .models import Note


class NoteForm(forms.ModelForm):

    class Meta:
        model = Note
        fields = ["subject", "title", "content"]

        widgets = {
            "subject": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Python Functions"
                }
            ),

            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 12,
                    "placeholder": "Write your study notes here..."
                }
            ),
        }