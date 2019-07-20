from django.db import models
from player.models import Player, Agent
from covmax.constants import MAX_TURNS, MAP_NAMES
from covmax.settings import STATIC_URL
from django.core.exceptions import ObjectDoesNotExist
import json 
import random
from copy import copy, deepcopy 
import os 
from datetime import datetime
# Create your models here.

AI_MAX_ATTEMPT = 1000

class Game(models.Model):
    ongoing = models.BooleanField(null=False, default=False)
    AI_players = models.TextField(null=False, default="")
    human_players = models.TextField(null=False, default="[]")
    map_recipe = models.TextField(null=False, default="")
    board_id = models.IntegerField(null=False, default=-1)
    position_assignment = models.TextField(null=False, default="[]")
    start_time = models.DateTimeField(null=True)
    parsed_human_players = [] 
    parsed_position_assignment = [] 
    
    def initialize(self):
        print(self.human_players)
        self.parsed_human_players = json.loads(self.human_players)
        self.parsed_position_assignment = json.loads(self.position_assignment)
        

    def make_board(self, load_map, map_name):

        # Only accept rectangular maps
        assert([len(row) == len(load_map[0]) for row in load_map])

        map_width = len(load_map[0])
        map_height = len(load_map)
        game_board = Board.objects.create(width=map_width,height=map_height,game_id=self.id,name=map_name)
        game_board.load_map(load_map)

        # Create AI players
        parsed_AI_players = json.loads(self.AI_players)
        for recipe in parsed_AI_players:
            game_board.addAI(recipe[0],recipe[1][0], recipe[1][1])
        self.board_id = game_board.id
        self.saveState() 

    def add_player(self, player):
        print("add player called by " + str(player))
        if len(self.parsed_human_players) == len(self.parsed_position_assignment):
            print("Error joining, game is full")
            print(self.parsed_human_players)
            print(self.parsed_position_assignment)
            self.ongoing = True 
            return False

        try:
            board = Board.objects.get(id=self.board_id)
            board.add_player(player,self.parsed_position_assignment[len(self.parsed_human_players)][0], \
                self.parsed_position_assignment[len(self.parsed_human_players)][1]) 
            self.parsed_human_players += [player.IP]
            if len(self.parsed_human_players) == len(self.parsed_position_assignment):
                self.ongoing = True
                self.start_time = datetime.now()

        except ObjectDoesNotExist:
            print("Error, trying to add player to non-existent board")
            return False

        player.game_id = self.id 
        player.save()
        self.saveState()

    def saveState(self):

        self.human_players = json.dumps(self.parsed_human_players)
        self.position_assignment = json.dumps(self.parsed_position_assignment)
        self.save()

class Board(models.Model):
    game_id = models.IntegerField(null=False)
    width = models.IntegerField(null=False)
    height = models.IntegerField(null=False)
    history = models.TextField(null=False, default='[]')
    score_history = models.TextField(null=False, default='[]')
    pending = models.TextField(null=False, default='{}')
    agents = models.TextField(null=False, default='{}')
    name = models.TextField(null=False, default="")
    needs_refresh = models.TextField(null=False, default='{"admin":"True"}')
    locked = models.BooleanField(null=False, default=False)
    grid_type = {'-1': "grey-grid", '0': "white-grid", '1': "black-grid", '2': "singly-covered-grid", '3': "doubly-covered-grid", '4': 'uncertain-grid'}

    parsed_history = []
    parsed_score_history = []
    parsed_pending = {}
    parsed_needs_refresh = {}
    IP_Player = {}
    IP_Agent = {}
    id_pool = None 
    grid = None
    cells = {}
    neighbors = {}
    connected = {} # An alternate version of neighbors that include non-traversible tiles 
    covered_set = None
    max_coverage_range = 0


    def play_history(self, stage):

        self.grid = self.history[stage]
        
    def load_map(self, new_map):

        self.grid = deepcopy(new_map)
        self.parsed_history = [deepcopy(self.grid)] 
        self.saveState() 

    def initialize(self):

        self.id_pool = list(range(100))

        self.parsed_history = json.loads(self.history)
        if len(self.parsed_history) == 0:
            self.grid = []
        else:
            self.grid = deepcopy(self.parsed_history[-1])
          
        parsed_agents = json.loads(self.agents)

        self.IP_Agent = {}
        for agent in parsed_agents:
            self.IP_Agent[agent] = Agent.objects.get(id=parsed_agents[agent])
            if self.IP_Agent[agent].algo_instance is not None:
                if int(agent.split('_')[1]) in self.id_pool:
                    self.id_pool.remove(int(agent.split('_')[1]))


        self.parsed_needs_refresh = json.loads(self.needs_refresh)


        self.parsed_pending = json.loads(self.pending)
        for player in self.parsed_pending:
            try:
                if "_" in player:
                    continue
                self.IP_Player[player] = Player.objects.get(IP=player)
            except KeyError:
                print("Error, contains non-existent player")
                return "Error, contains non-existent player"
        
        
        if len(self.grid) > 0:
            for r in range(self.height):
                    for c in range(self.width):
                        neighbor_offsets = [[-1,-1], [-1,0], [-1,1], [0,-1], [0,1], [1,-1], [1,0], [1,1]]
                        self.neighbors[(r,c)] = []
                        self.connected[(r,c)] = []
                        for offset in neighbor_offsets:
                            dr, dc = offset
                            dr += r 
                            dc += c 
                            if dr >=0 and dr < self.height and dc >= 0 and dc < self.width:
                                self.connected[(r,c)] += [(dr, dc)]
                                if self.grid[dr][dc] == "0":
                                    self.neighbors[(r,c)] += [(dr, dc)] 

        self.parsed_score_history = json.loads(self.score_history)
        if len(self.parsed_score_history) == 0:
            self.parsed_score_history += [self.getGlobalScore()]

        for player in self.IP_Agent:
            self.max_coverage_range = max(self.max_coverage_range, self.IP_Agent[player].coverage)


    def add_player(self, caller, row, col):
        if caller.IP not in self.parsed_pending:
            self.parsed_pending[caller.IP] = None 
            new_agent = Agent.objects.create(r=row,c=col,token="tokens/token" + str(random.randint(0,99)) + ".png")
            self.IP_Agent[caller.IP] = new_agent 
        print("Player " + str(caller.IP) + " has joined the board")
        for player in self.parsed_needs_refresh:
            self.parsed_needs_refresh[player] = "True"
        self.parsed_needs_refresh[caller.IP] = "False"
        self.saveState()

    def addAI(self, recipe, row, col):
        # An AI is controlled by the algo_instance of an agent
        if True: # Assumes that AI do not attempt to join games themselves
            new_agent = Agent.objects.create(r=row,c=col,token="tokens/token" + str(random.randint(0,99)) + ".png", algorithm=recipe)
            new_agent.save()
            agent_name = new_agent.algo_instance.__class__.__name__ + "_" + str(new_agent.id)
            self.parsed_pending[agent_name] = None 
            self.IP_Agent[agent_name] = new_agent 
        print("AI " + str(agent_name) + " has joined the board")
        self.saveState()

    def updateAI(self):
        # Temporary fix for None id problem
        self.locked = True 
        self.save()
        print(self.IP_Agent)
        print(self.parsed_pending)
        for agent_ip in self.IP_Agent:
            print(agent_ip)
            if self.IP_Agent[agent_ip].algo_instance is not None and self.parsed_pending[agent_ip] is None:
                exceed_limit = True
                for i in range(AI_MAX_ATTEMPT):
                    
                    action = self.IP_Agent[agent_ip].algo_instance.computeNext(self.generateState(self.IP_Agent[agent_ip]))
                    viable = self.attemptAction(self.IP_Agent[agent_ip].algo_instance.name, action, test=True)
                    if viable:
                        exceed_limit = False
                        break
                if exceed_limit:
                    self.attemptAction(self.IP_Agent[agent_ip].algo_instance.name, json.dumps((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c)), test=True)
                    print("Error, " + self.IP_Agent[agent_ip].algo_instance.name + " was unable to decide on next action")
        self.locked = False 
        self.save()

    def handleTurn(self, caller, action, force_next=False):
        
        if not Game.objects.get(id=caller.game_id).ongoing:
            print("Game has yet to be started")
            return True 

        self.updateAI()
        if caller.IP not in self.parsed_pending:
            print("Error, player not supposed to be playing on this board")
            return True
        if not force_next and self.attemptAction(caller.IP, action, test=True):
            self.parsed_pending[caller.IP] = action
        all_done = True
        for player in self.parsed_pending:
            if self.parsed_pending[player] == None or self.parsed_pending[player] == "null":
                all_done = False
                print(player + " has not finished")
                break 
        all_done = all_done or force_next
        if all_done:
            # Execute all pending actions
            for player in self.parsed_pending:
                if self.parsed_pending[player] is not None:
                    self.attemptAction(player, self.parsed_pending[player], test=False)
                self.parsed_pending[player] = None
            for player in self.parsed_needs_refresh:
                self.parsed_needs_refresh[player] = "True"
            # Commit all actions 
            self.parsed_history += [deepcopy(self.grid)]
            self.parsed_score_history += [self.getGlobalScore()]
            self.saveState()

            # Determine if game has ended
            map_index = MAP_NAMES.index(self.getName(True))
            if len(self.parsed_history) >= MAX_TURNS[map_index]:
                # Move user to next game 
                return False 
            # AI turn
            self.updateAI()
        return True
           
    def generateState(self, agent):
        # Exclude agent's own contribution to covered set 
        covered_set = set()
        repeated_set = []
        visible_set = self.getCoveredSet((agent.r, agent.c), agent.sight, self.neighbors)
        agents = {}
        for agent_ip in self.IP_Agent:
            other_agent = self.IP_Agent[agent_ip]
            if (other_agent.r, other_agent.c) in visible_set:
                reg = self.getCoveredSet((other_agent.r, other_agent.c), other_agent.coverage, self.neighbors)
                covered_set = covered_set.union(reg)
                repeated_set += list(reg)
                agents[other_agent] = reg.intersection(visible_set)
        for c in covered_set:
            repeated_set.remove(c)
        repeated_set = set(repeated_set)
        covered_set = covered_set.intersection(visible_set)
        repeated_set = repeated_set.intersection(visible_set)

        return (self.neighbors, agents)

    def attemptAction(self, callerIP, action, test=False):
        try:
            agent=self.IP_Agent[callerIP]
        except KeyError:
            for agent in self.IP_Agent:
                if self.IP_Agent[agent].algo_instance is not None and self.IP_Agent[agent].algo_instance.name == callerIP:
                    self.IP_Agent[callerIP] = self.IP_Agent[agent]
                    self.IP_Agent.pop(agent) 
                    if agent in self.parsed_pending:
                        self.parsed_pending[callerIP] = self.parsed_pending[agent]
                        self.parsed_pending.pop(agent)
                    else:
                        self.parsed_pending[callerIP] = None
                    
                    agent = self.IP_Agent[callerIP]
                    break 
                else:
                    print("Error, action performed by non-existent player")
                    return False
        original_r, original_c = agent.r, agent.c
        action_parsed = json.loads(action)
        dr, dc = action_parsed
        agent.r = dr 
        agent.c = dc 
        if agent.r >= 0 and agent.r < self.height and agent.c >= 0 and agent.c < self.width and self.grid[agent.r][agent.c] != "1" and \
            ((dr, dc) in self.neighbors[(original_r, original_c)] or (dr,dc)==(original_r,original_c)):
            if test:
                agent.r = original_r
                agent.c = original_c
                self.parsed_pending[callerIP] = action 
                self.saveState()
            return True
        
        agent.r = original_r
        agent.c = original_c
        return False
    
    def getCoveredSet(self, position, extension, neighbors):
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

    def getName(self, inc_ext=False):
        return self.name + (".csv" if inc_ext else "")

    def getMessage(self, caller):
        if caller == "admin":
            message = "You are currently spectating the game as an admin"
            for player in self.IP_Agent:
                message += "<br>" + player + ": " + "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[player].token) + "' style='position: relative; z-index:1'>"
            return message
        # Assumes this is a human player
        callerIP = caller.IP  
        output = ""
        print(Game.objects.get(id=self.game_id).ongoing)
        if not Game.objects.get(id=self.game_id).ongoing:
            output += "Waiting for more player(s).."
        elif self.parsed_pending[callerIP] is None:
            output += "Your Turn"
        else:
            output += "Waiting for other player(s).."
        output += "<br>(" + str(MAX_TURNS[MAP_NAMES.index(self.getName(True))] - len(self.parsed_history)) + " turns remaining)"
        return output 
        
    def getDisplayCells(self, caller):
        output = {}
        total_covered_set = set()
        repeated_covered_set = []
        if caller == "admin":
            visible_set = set([(x,y) for x in range(self.width) for y in range(self.height)])
            certain_set = set([(x,y) for x in range(self.width) for y in range(self.height)])
        else:
            visible_set = self.getCoveredSet((self.IP_Agent[caller.IP].r, self.IP_Agent[caller.IP].c), self.IP_Agent[caller.IP].sight, self.connected)
            certain_set = self.getCoveredSet((self.IP_Agent[caller.IP].r, self.IP_Agent[caller.IP].c), self.IP_Agent[caller.IP].sight - self.max_coverage_range, self.connected)

        for agent_ip in self.IP_Agent:
            if (self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c) not in visible_set:
                continue
            x = self.getCoveredSet((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c), self.IP_Agent[agent_ip].coverage, self.neighbors)
            total_covered_set = total_covered_set.union(x)
            repeated_covered_set += list(x)
        for element in total_covered_set:
            repeated_covered_set.remove(element)
        repeated_covered_set = set(repeated_covered_set)
        for r in range(self.height):
            for c in range(self.width):
                key = (r,c)
                if key not in visible_set:
                    val = "-1"
                else:
                    if self.grid[r][c] == "0":
                        if key in repeated_covered_set:
                            val = "3"
                        elif key in total_covered_set and key in certain_set:
                            val = "2"
                        elif key in total_covered_set and key not in certain_set:
                            val = "2"
                        elif key not in total_covered_set and key in certain_set:
                            val = "0"
                        elif key not in total_covered_set and key not in certain_set:
                            val = "4"
                    else:
                        val = "1"
                content = ""
                for agent in self.IP_Agent:
                    if self.IP_Agent[agent].r == r and self.IP_Agent[agent].c == c and val != "-1":
                        if caller != "admin" and agent == caller.IP:
                            content = "<img src='"+ os.path.join(STATIC_URL,"tokens/player.png") +"' style='position:absolute; z-index:2; margin: 6px 13.5px'>"
                            content += "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position: relative; z-index:1'>"
                        else:
                            content = "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position: relative; z-index:1'>"

                output[key] = (self.grid_type[val], content)
        return output 
    
    def getGraphData(self):
        pass 

    def getGlobalScore(self):
        total_covered_set = set()
        for agent_ip in self.IP_Agent:
            x = self.getCoveredSet((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c), self.IP_Agent[agent_ip].coverage, self.neighbors)
            total_covered_set = total_covered_set.union(x)
        return len(total_covered_set)

    def saveState(self):
        self.history = json.dumps(self.parsed_history)
        self.pending = json.dumps(self.parsed_pending)
        self.score_history = json.dumps(self.parsed_score_history)
        self.needs_refresh = json.dumps(self.parsed_needs_refresh)
        parsed_agents = {}
        for agent in self.IP_Agent:
            parsed_agents[agent] = self.IP_Agent[agent].id 
            self.IP_Agent[agent].save()
        self.agents = json.dumps(parsed_agents)
        self.save()

def initialize_board(instance, **kwargs):
    instance.initialize()

def initialize_game(instance, **kwargs):
    instance.initialize()

models.signals.post_init.connect(initialize_board, Board)    
models.signals.post_init.connect(initialize_game, Game)