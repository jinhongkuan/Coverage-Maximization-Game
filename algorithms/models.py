from django.db import models
import random 
import json
import math 
# Create your models here.

# These are vanilla classes
class Algorithm():
    def __init__(self, agent):
        self.agent = agent 
        self.name = "algorithm_" + str(agent.id)
        
    def computeNext(self, state):
        action = None 
        return action 
     

class BLLL(Algorithm):
    def __init__(self, agent, exploration_term):
        super().__init__(agent)
        self.name = "BLLL_" + str(agent.id)
        self.exploration_term = exploration_term


    def computeNext(self, state):
        neighbors, visible, covered = state 
        position = (self.agent.r, self.agent.c)
        action = random.choice(neighbors[position])
        covered_set_alpha = set([position] + neighbors[position])
        marginal_covered_set_alpha = covered_set_alpha - covered 
        covered_set_beta = set([action] + neighbors[action])
        marginal_covered_set_beta = covered_set_beta - covered 
        alpha = math.exp(self.exploration_term*len(marginal_covered_set_alpha))
        beta = math.exp(self.exploration_term*len(marginal_covered_set_beta))
        if random.uniform(0,1) <= alpha/(alpha+beta):
            action = position
        else:
            pass 

        return json.dumps(action)
    