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
        neighbors, visible_agents = state 
        covered = set()
        repeated = []

        for agent in visible_agents:
            if agent is self.agent:
                continue
            territory = visible_agents[agent]
            covered = covered.union(territory)
            repeated += list(territory)
        for c in covered:
            repeated.remove(c)
        
        covered = covered.union()
        repeated = set(repeated)

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

class Conscientious(Algorithm):
    def __init__(self, agent, exploration_term, consc_term):
        super().__init__(agent)
        self.name = "Consc_" + str(agent.id)
        self.exploration_term = exploration_term
        self.consc_term = consc_term

    def computeNext(self, state):
        neighbors, visible_agents = state 
        covered = set()
        repeated = []
        jerk = self.agent
        max_overlap = 0

        for agent in visible_agents:
            territory = visible_agents[agent]
            covered = covered.union(territory)
            repeated += list(territory)
        for c in covered:
            repeated.remove(c)
        
        covered = covered.union()
        repeated = set(repeated)

        for agent in visible_agents:
            territory = visible_agents[agent]
            overlap = len(territory.intersection(repeated))
            if overlap > max_overlap:
                max_overlap = overlap 
                jerk = agent
        print(self.name + " thinks that " + ("player" if jerk.algo_instance is None else jerk.algo_instance.name))
        covered = set()
        repeated = []       
        for agent in visible_agents:
            if agent is not jerk and agent is not self.agent:
                territory = visible_agents[agent]
                covered = covered.union(territory)
                repeated += list(territory)
        for c in covered:
            repeated.remove(c)
        repeated = set(repeated)
        jerk_marginal = visible_agents[jerk].difference(covered)
        if jerk is self.agent:
            jerk_marginal = set()
        position = (self.agent.r, self.agent.c)
        action = random.choice(neighbors[position])
        covered_set_alpha = set([position] + neighbors[position])
        marginal_covered_set_alpha = covered_set_alpha - covered 
        jerk_marginal_alpha = jerk_marginal.intersection(marginal_covered_set_alpha)
        covered_set_beta = set([action] + neighbors[action])
        marginal_covered_set_beta = covered_set_beta - covered 
        jerk_marginal_beta = jerk_marginal.intersection(marginal_covered_set_beta)
        alpha = math.exp(self.exploration_term*(len(marginal_covered_set_alpha)-len(jerk_marginal_alpha)*self.consc_term))
        beta = math.exp(self.exploration_term*(len(marginal_covered_set_beta)-len(jerk_marginal_beta)*self.consc_term))
        if random.uniform(0,1) <= alpha/(alpha+beta):
            action = position
        else:
            pass 

        return json.dumps(action)
