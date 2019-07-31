from django.db import models
from copy import copy, deepcopy
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
       
        alpha = math.exp(self.exploration_term*len(marginal_covered_set_alpha))
        beta = math.exp(self.exploration_term*len(marginal_covered_set_beta))
        if random.uniform(0,1) <= alpha/(alpha+beta):
            action = position


        return json.dumps(action)

class Greedy(Algorithm):
    def __init__(self, agent, pick_rate):
        super().__init__(agent)
        self.name = "Greedy_" + str(agent.id)
        self.pick_rate = pick_rate

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
        
        repeated = set(repeated)

        position = (self.agent.r, self.agent.c)

        if random.random() > self.pick_rate:
            return json.dumps(position)
        actions = list(getCoveredSet(position, self.agent.movement, neighbors))
        for i in range(len(actions)):
            actions[i] = (actions[i], len(getCoveredSet(actions[i], self.agent.coverage, neighbors).difference(covered)))
        actions = sorted(actions, key=lambda x:x[1], reverse=True)   
        action = actions[0][0]     

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


class Explora(Algorithm):
    def __init__(self, agent, exploration_term, poisson,  distance_discount):
        super().__init__(agent)
        self.name = "Explora_" + str(agent.id)
        self.exploration_term = exploration_term
        self.distance_discount = distance_discount
        self.poisson_rate = poisson

    def computeTileUtility(self, pos, graph, distance_discount, lookahead):
        last_layer = set([pos])
        considered = set([pos])
        frequency = {}
        for i in range(lookahead):
            current_layer = set()
            for c in last_layer:
                new_c = graph[c]
                new_c = new_c.difference(considered)
                current_layer = current_layer.union(new_c)
                considered = considered.union(new_c)
            frequency[i+1] = len(current_layer)
            last_layer = current_layer
        
        util = sum([frequency[key] * distance_discount**key for key in frequency])
        return util 

    @staticmethod
    def square_discount(dist):
        return 1 if dist==0 or dist==1 else 1/(2*dist+1)

    @staticmethod
    def square_heuristics(graph, lookahead):
        graph = deepcopy(graph)
        # Divide graph into fully-known and partially-known sections
        partially_known = [x for x in graph.keys() if len(graph[x]) < 8]
        explored = set(graph.keys())
        possible_paths = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]]
        for l in range(lookahead):
            new_layer = set()
            for t in partially_known:
                if t not in graph:
                    graph[t] = (0, set()) # Optimism encoded
                possible_extension = set([(t[0]+x[0], t[1]+x[1]) for x in possible_paths])
                graph[t] = (graph[t][0], graph[t][1].union(possible_extension))

                possible_extension = possible_extension.difference(explored)
                new_layer = new_layer.union(possible_extension)
                explored = explored.union(possible_extension)
                
            partially_known = new_layer
        output = {}
        # Graph clean-up
        for t in graph:
            if graph[t][0] == 1:
                continue 
            output[t] = set()
            for x in graph[t][1]:
                if x not in graph or graph[x][0] == 0:
                    output[t].add(x)
        return output 

    @staticmethod
    def encode_tuple_dict(inp):
        output = {}
        for key in inp:
            output[str(key)] = [inp[key][0], list(inp[key][1])]
        return output 

    @staticmethod
    def decode_tuple_dict(inp):
        output = {}
        for key in inp:
            output[tuple(eval(key))] = [inp[key][0], set([tuple(x) for x in inp[key][1]])]
        return output 

    def computeNext(self, state):
        neighbors, connected, visible_agents = state 
        covered = set()
        for agent in visible_agents:
            if agent is self.agent:
                continue
            territory = visible_agents[agent]
            covered = covered.union(territory)

        position = (self.agent.r, self.agent.c)
        if random.random() > BLLL.poisson(self.poisson_rate, 1):
            return json.dumps(position)

        if len(self.agent.parsed_memory) == 0:
            self.agent.parsed_memory += [{}]
        parsed_memory = Explora.decode_tuple_dict(self.agent.parsed_memory[0])
        visible_tiles = getCoveredSet(position, self.agent.sight, neighbors)
        visible_walls = getCoveredSet(position, self.agent.sight, connected) - visible_tiles
        for t in visible_tiles:
            if t not in parsed_memory:
                parsed_memory[t] = (0,set())
            visible_neighbors = set(neighbors[t]).intersection(visible_tiles)
            parsed_memory[t] = (0, parsed_memory[t][1].union(visible_neighbors))
        for t in visible_walls:
            if t not in parsed_memory:
                parsed_memory[t] = (1,set())
            # Not important to keep track of their neighbors
            # visible_neighbors = set(neighbors[t]).intersection(visible_tiles)
            # parsed_memory[t] = (1, parsed_memory[t][1].union(visible_neighbors))
        
        self.agent.parsed_memory[0] = Explora.encode_tuple_dict(parsed_memory)
        self.agent.saveState()

        lookahead = 7
        optimistic_world = Explora.square_heuristics(parsed_memory, lookahead)
        action = random.choice(list(getCoveredSet(position, self.agent.movement, neighbors)-set([position])))
        covered_set_alpha = set([position] + neighbors[position])
        marginal_covered_set_alpha = covered_set_alpha - covered
        alpha_score = sum([self.computeTileUtility(x, optimistic_world, self.distance_discount, lookahead) for x in marginal_covered_set_alpha])
        covered_set_beta = set([action] + neighbors[action])
        marginal_covered_set_beta = covered_set_beta - covered 
        beta_score = sum([self.computeTileUtility(x, optimistic_world, self.distance_discount, lookahead) for x in marginal_covered_set_beta])
        alpha = math.exp(self.exploration_term*alpha_score)
        beta = math.exp(self.exploration_term*beta_score)
        if random.uniform(0,1) <= alpha/(alpha+beta):
            action = position
        else:
            pass 

        return json.dumps(action)