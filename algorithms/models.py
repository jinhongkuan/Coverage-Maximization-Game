from django.db import models
import random 
import json
import math 
# Create your models here.

# These are vanilla classes
class Algorithm():
    def __init__(self, agent):
        self.agent = agent 
        self.name = "algorithm_"
        
    def computeNext(self, state):
        action = None 
        return action 
     

class BLLL(Algorithm):
    def __init__(self, agent, exploration_term, poisson_rate):
        super().__init__(agent)
        self.name = "BLLL_" + str(agent.id)
        self.exploration_term = exploration_term
        self.poisson_rate = poisson_rate

    @classmethod 
    def poisson(cls, rate, duration):
        return 1 - math.exp(-rate*duration)

    def computeNext(self, state):
        neighbors, connected, visible_agents = state 
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

        if random.random() > BLLL.poisson(self.poisson_rate, 1):
            return json.dumps(position)

        action = random.choice(list(getCoveredSet(position, self.agent.movement, neighbors)-set([position])))
        covered_set_alpha = set([position] + neighbors[position])
        marginal_covered_set_alpha = covered_set_alpha - covered 
        covered_set_beta = set([action] + neighbors[action])
        marginal_covered_set_beta = covered_set_beta - covered
        if self.exploration_term == 999: # Special case for fully-greedy algo
            if len(marginal_covered_set_alpha) >= len(marginal_covered_set_beta):
                action = position 
        else:
            alpha = math.exp(self.exploration_term*len(marginal_covered_set_alpha))
            beta = math.exp(self.exploration_term*len(marginal_covered_set_beta))
            if random.uniform(0,1) <= alpha/(alpha+beta):
                action = position


        return json.dumps(action)

class Conscientious(Algorithm):
    def __init__(self, agent, exploration_term, consc_term):
        super().__init__(agent)
        self.name = "Consc_" + str(agent.id)
        self.exploration_term = exploration_term
        self.consc_term = consc_term

    def computeNext(self, state):
        neighbors, connected, visible_agents = state 
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
        action = random.choice(list(getCoveredSet(position, self.agent.movement, neighbors)-set([position])))
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

class Explorer(Algorithm):
    def __init__(self, agent, exploration_term, poisson,  distance_discount):
        super().__init__(agent)
        self.name = "Explorer_" + str(agent.id)
        self.exploration_term = exploration_term
        self.distance_discount = distance_discount
        self.poisson_rate = poisson

    def computeTileUtility(self, pos, neighbors, obstacles, distance_discount):
        if pos in obstacles:
            return 0
        CAP = 6 
        last_layer = set([pos])
        considered = set([pos])
        frequency = {}
        possible_paths = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]]
        for i in range(CAP):
            current_layer = set()
            for c in last_layer:
                new_c = set([(x[0] + c[0], x[1] + c[1]) for x in possible_paths])
                new_c = new_c.difference(obstacles)
                current_layer = current_layer.union(new_c.difference(considered))
                considered = considered.union(new_c)
            frequency[i+1] = len(current_layer)
            last_layer = current_layer
        
        util = sum([frequency[key] * distance_discount**key for key in frequency])
        return util 


    def computeNext(self, state):
        neighbors, connected, visible_agents = state 
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
        if random.random() > BLLL.poisson(self.poisson_rate, 1):
            return json.dumps(position)
        visible_tiles = getCoveredSet(position, self.agent.sight, neighbors)
        connected_tiles = getCoveredSet(position, self.agent.sight, connected)
        visible_walls = visible_tiles - connected_tiles
        parsed_memory = set(self.agent.parsed_memory)
        parsed_memory = parsed_memory.union(visible_walls)
        self.agent.parsed_memory =  list(parsed_memory)
        self.agent.saveState()
        visible_walls = parsed_memory
        action = random.choice(list(getCoveredSet(position, self.agent.movement, neighbors)-set([position])))
        covered_set_alpha = set([position] + neighbors[position])
        marginal_covered_set_alpha = covered_set_alpha - covered
        alpha_score = sum([self.computeTileUtility(x, neighbors, visible_walls, self.distance_discount) for x in marginal_covered_set_alpha])
        covered_set_beta = set([action] + neighbors[action])
        marginal_covered_set_beta = covered_set_beta - covered 
        beta_score = sum([self.computeTileUtility(x, neighbors, visible_walls, self.distance_discount) for x in marginal_covered_set_beta])
        alpha = math.exp(self.exploration_term*alpha_score)
        beta = math.exp(self.exploration_term*beta_score)
        if random.uniform(0,1) <= alpha/(alpha+beta):
            action = position
        else:
            pass 

        return json.dumps(action)

def getCoveredSet(position, extension, neighbors):
        covered_set = set()
        last_iter = set([position])
        covered_set = covered_set.union(last_iter)
        for i in range(extension):
            this_iter = set()
            if len(last_iter) == 0:
                break 
            for cell in last_iter:
                for neighbor in neighbors[cell]:
                    if neighbor not in covered_set:
                        this_iter.add(neighbor)
                        covered_set.add(neighbor)
            last_iter = this_iter
        return covered_set