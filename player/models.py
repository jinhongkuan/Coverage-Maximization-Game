from django.db import models
from algorithms.models import Algorithm, BLLL, Conscientious, Explorer, Explora, Greedy
import json 
class Player(models.Model):
    IP = models.CharField(max_length = 100, null=False)
    name = models.CharField(max_length = 100, null=False, default="")
    active = models.BooleanField(null=False)
    game_id = models.IntegerField(null=False, default=-1)
    all_game_ids = models.TextField(null=False, default="")

class Agent(models.Model):
    token = models.TextField(null=False, default="tokens/token.png")
    algorithm = models.TextField(null=False, default="")
    algo_instance = None 
    r = models.IntegerField(null=False)
    c = models.IntegerField(null=False)
    coverage = models.IntegerField(null=False,default=1)
    sight = models.IntegerField(null=False,default=2)
    movement = models.IntegerField(null=False, default=1)
    memory = models.TextField(null=False,default="[]")
    parsed_memory = None 

    def saveState(self):
        self.memory = json.dumps(self.parsed_memory)
        self.save()
def initialize_agent(instance, **kwargs):
    if instance.algorithm != "":
        # This is an AI, let's create an algorithm instance for it
        instance.algo_instance = eval(instance.algorithm)
    instance.parsed_memory = json.loads(instance.memory)





models.signals.post_init.connect(initialize_agent, Agent)
