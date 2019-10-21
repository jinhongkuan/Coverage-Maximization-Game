from django.db import models

# Create your models here.
class TeamEvalSurveyData(models.Model):
    difficulty = models.IntegerField(null=False, default=-1)
    satisfaction = models.IntegerField(null=False, default=-1)
    confusion = models.IntegerField(null=False, default=-1)
    collaboration = models.IntegerField(null=False, default=-1)
    contribution = models.IntegerField(null=False, default=-1)
    interaction = models.IntegerField(null=False, default=-1)
    isolation = models.IntegerField(null=False, default=-1)
    activity = models.IntegerField(null=False, default=-1)
    understanding = models.IntegerField(null=False, default=-1)
    intelligence = models.IntegerField(null=False, default=-1)
    game_id = models.IntegerField(null=False, default=-1)
    player_id = models.IntegerField(null=False, default=-1)

    def pretty_print(self):
        return "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(self.difficulty, self.satisfaction,self.confusion,self.collaboration,self.contribution,self.interaction,self.isolation,self.activity,self.understanding,self.intelligence)
        