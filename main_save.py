import random
from copy import copy, deepcopy 
import numpy as np 
import matplotlib.pyplot as plt 
import csv 
import os 
import time
class MDP_Learner:

    @staticmethod
    def _normalize(row):

        row = abs(row)
        return row/sum(row)

    def make_matrix_consistent(self):
        self.matrix = np.concatenate((self.matrix[:,0:1], 
        abs(self.matrix[:,1:2]/sum(self.matrix[:,1:2])),
        np.apply_along_axis(MDP_Learner._normalize, 1, self.matrix[:,2:self.state_size+2]),
        np.apply_along_axis(MDP_Learner._normalize, 1, self.matrix[:,self.state_size+2:])), axis=1) 

    def __init__(self, state_size, set_strategy=None):
        # This matrix is a Nx(2N+1) representation of learning strategy 
        # Each row represents a decision node, expressed in: action, trans. prob | opp. cooperate | opp. defect
        if set_strategy is None:
            self.matrix = np.concatenate(([[i%2] for i in range(state_size)],
            [[1/state_size] for i in range(state_size)],
            np.random.rand(state_size, state_size),
            np.random.rand(state_size, state_size)), axis=1)
        else:
            self.matrix = set_strategy

        
        self.state_size = state_size
        self.make_matrix_consistent()
        self.state_index = np.random.choice(a=self.matrix.shape[0], p=self.matrix[:,1])
        self.prev_state_observation = (0,1)
        self.age = 0
        
    def refresh(self):
        self.state_index = np.random.choice(a=self.matrix.shape[0], p=self.matrix[:,1])

    def play(self):
        return self.matrix[self.state_index,0]

    def observe(self, observation):
        if observation is not None:
            if observation == 0:
                trans_prob = self.matrix[self.state_index, 2:self.state_size+2]
            else:
                trans_prob = self.matrix[self.state_index, self.state_size+2:]
    
            next_state = np.random.choice(range(self.state_size),p=trans_prob)
            self.prev_state_observation = (self.state_index, int(next_state+2+observation*self.state_size))
            self.state_index = next_state

    


    def mutate(self, rate):
        # Mutate mixed strategy
        self.matrix[:,1] += Mutation.pairwise_gaussian(rate, self.matrix[:,1])
        
        # Mutate transition probabilities 
        for i in range(self.matrix.shape[0]):
            for obs_shift in range(2): # Do calculation separately for the Obs(Coop) and Ops(Defect) sets of columns
                shift = 2 + obs_shift * self.state_size
                mutation = Mutation.pairwise_gaussian(rate,self.matrix[i,shift:shift+self.state_size])
                self.matrix[i,shift:shift+self.state_size] += mutation

        self.make_matrix_consistent() # Only to fix floating-point error

class Mutation:
    @staticmethod
    def pairwise_gaussian(rate, array):
        normal_values = np.zeros(len(array))
        projected = copy(array)
        for i in range(len(projected)):
            j = (i+1) % len(projected)
            alpha = np.random.normal(loc=0, scale=rate)
            normal_values[i] += alpha 
            normal_values[j] -= alpha  
            projected[i] += alpha 
            projected[j] -= alpha 
        min_scaling = 1.0
        for i in range(len(normal_values)):
            i_after = projected[i]
            excess = i_after - 1 if i_after > 1 else abs(min(0, i_after))
            scaling = 1 - excess/abs(normal_values[i])
            min_scaling = min(min_scaling, scaling)
        normal_values *= min_scaling

        return normal_values

class Selection:
	@staticmethod
	def truncation(population, scores):
		# Kill off half and clone the rest 
		new_pops = sorted([(scores[i], population[i]) for i in range(len(scores))], key=lambda x:x[0], reverse=True) 
		new_pops = new_pops[:len(scores)//2]
		new_pops = [x[1] for x in new_pops]
		return new_pops

class Interaction:
	@staticmethod
	def pairwise(population, fresh_mind, payoff_matrix):
		scores = [0]*len(population)
		combinations = copy(template_combinations)
		for i in range(len(population)):
		    for j in range(i+1, len(population)):
		        for k in range(repetition):
		            i_play = int(population[i].play())
		            j_play = int(population[j].play())
		            population[i].observe(j_play)
		            population[j].observe(i_play)
		            scores[i] += payoff_matrix[i_play,j_play,0]
		            scores[j] += payoff_matrix[i_play,j_play,1]
		            play = play_to_str[i_play+j_play]
		            if play not in combinations:
		                combinations[play] = 0 
		            combinations[play] += 1
		        if fresh_mind:
		            population[i].refresh()
		            population[j].refresh()
		return scores, combinations

    @staticmethod
    def uniform_random(population, cutoff):
        return np.random.choice(population, size=cutoff)

class Population:
    def __init__(self, population_size, state_size, repetition, fresh_mind = False, set_strategy=None):
        self.pops = [MDP_Learner(state_size, set_strategy) for i in range(population_size)]
        self.repetition = repetition 
        self.fresh_mind = fresh_mind
        self.population_size = population_size

    def aggregate_selection(self, payoff_matrix):
        np.random.shuffle(self.pops)
        num_offsprings = self.population_size//2
        scores, combinations = Interaction.pairwise(self.pops, self.fresh_mind, payoff_matrix)
        self.pops = Selection.truncation(self.pops, scores)

        for i in range(len(self.pops)):
            self.pops[i].age += 1
            self.pops += [deepcopy(self.pops[i])]
            self.pops[-1].age = 0
            self.pops[-1].mutate(0.02) 
        
        return combinations

rand_seed = time.time()
random.seed(rand_seed)
# Change these
name = "data/pd_test"
prisoner = [[[1,4],[3,3]],
                [[2,2],[4,1]]]

no_conflict = [[[3,2],[4,4]],
                [[1,1],[2,3]]]
p_matrix = prisoner
iterations = 4000

window = 50
repetition = 10
play_to_str = {2 : "DD", 1 : "C/D", 0 : "CC"}
template_combinations = {"DD":0, "C/D":0, "CC":0}
tit_for_tat = np.asarray([[0,1.0,1.0,0.0,0.0,1.0], [1,0.0,1.0,0.0,0.0,1.0]])
midway = np.asarray([[0,1.0,0.5,0.5,0.5,0.5], [1,0.0,0.5,0.5,0.5,0.5]])
Pops = Population(10,2, repetition, fresh_mind=True, set_strategy=midway)
name += "_" + str(len(Pops.pops)) + "players"
np.set_printoptions(precision=2, suppress=True)
tally = {"CC":[], "C/D":[], "DD":[]}

test_gene_coverage = []
fossils = []
for i in range(iterations):
    
    for pop in Pops.pops:
        test_gene_coverage += [pop.matrix[0,2]] 
    combinations = (Pops.aggregate_selection(np.asarray([[p_matrix[0][1],p_matrix[0][0]],
                                                        [p_matrix[1][1],p_matrix[1][0]]])))
    for key in combinations:
        tally[key] += [combinations[key]]
    if i % window == 0:
        print(i)
        all_matrices = []
        for pop in Pops.pops:
            all_matrices += copy([pop.matrix])
        fossils += [all_matrices]

for key in tally:
    plt.plot([sum(tally[key][i*window:(i+1)*window])/window for i in range(iterations//window)])

 

plt.legend(list(tally.keys()))

plt.savefig(fname=name+".png")
plt.show()

with open(name + ".csv", "w", newline="") as f:
    f_writer = csv.writer(f)
    f_writer.writerow(["Seed", rand_seed])
    f_writer.writerow(["Action", "Start. P", "C|C", "C|D", ])
    for i in range(len(Pops.pops)):
        mat = Pops.pops[i].matrix
        for r in range(mat.shape[0]):
            for c in range(1,mat.shape[1]):
                mat[r,c] = round(mat[r,c]*100)/100
        f_writer.writerows(mat)
        f_writer.writerow([])
        
while True:
    generation = int(input("Generation to peek: "))
    for i, pop_matrix in enumerate(fossils[generation]):
        print("--- Agent {0} ---".format(i))
        for row in pop_matrix:
            print(row)
