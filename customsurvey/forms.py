from django import forms
from django.utils.safestring import mark_safe

numerical_choices = [('1',1),('2',2),('3',3),('4',4),('5',5),('6',6),('7',7),('8',8),('9',9),('10',10)]


class TeamEvalForm(forms.Form):
    difficulty = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I found this map challenging")
    satisfaction = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I was satisfied with my team's performance")
    confusion = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I found the actions of my teammates confusing")
    collaboration = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="The team collaborated well together")
    contribution = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="The team performed better because of my presence")
    interaction = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I interacted frequently with my teammates")
    isolation = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I was mostly minding my own business in the game")
    activity = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="I moved about a lot in each round")
    understanding = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="My teammates understood my plan")
    intelligence = forms.ChoiceField(choices=numerical_choices, widget=forms.RadioSelect(), label="My teammates behaved intelligently")
