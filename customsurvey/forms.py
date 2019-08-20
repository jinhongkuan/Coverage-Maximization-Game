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

class QuizForm(forms.Form):

    movement = forms.ChoiceField(choices=[(1, 'Press the arrow keys on my keyboard'), (2, 'Click on any tile on the map'), (3, 'Click on the tiles that becomes highlighted when hovered')], widget=forms.RadioSelect(), label="To move my agent around the map, I will:")
    traversible = forms.ChoiceField(choices=[(1, 'White'), (2, 'Black'), (3, 'Green'), (4, 'Dark Green')], widget=forms.RadioSelect(), label="An agent cannot move to a tile which is colored:")
    objective = forms.ChoiceField(choices=[(1, 'Make my agent cover as many tiles as possible'), (2, 'Work with other agents to maximize the number of tiles covered'), (3, 'Visit as many tiles as possible')], widget=forms.RadioSelect(), label="The objective of this game is to:")
    overlap = forms.ChoiceField(choices=[(1, 'Area covered by an agent'), (2, "Overlap between agents' area of coverage")], widget=forms.RadioSelect(), label="A dark-green tile indicates:")
    stay = forms.ChoiceField(choices=[(1, 'Click on the current position of your agent'), (2, "You cannot stay in the same spot")], widget=forms.RadioSelect(), label="To stay in the same spot on the map:")
