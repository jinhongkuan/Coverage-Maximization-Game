from django.db import models
from player.models import Player, Agent
from covmax.settings import STATIC_URL
from django.core.exceptions import ObjectDoesNotExist
import json 
import random
from copy import copy, deepcopy 
import os 
from datetime import datetime, timezone, timedelta
import csv
from covmax.settings import STATIC_ROOT
from covmax.constants import TURN_TIMER
import threading
# Create your models here.

AI_MAX_ATTEMPT = 1000

class Game(models.Model):
    available = models.BooleanField(null=False, default=True)
    ongoing = models.BooleanField(null=False, default=False)
    max_turns = models.IntegerField(null=False, default=0)
    seq_data = models.TextField(null=True, default="{}")
    AI_players = models.TextField(null=False, default="")
    human_players = models.TextField(null=False, default="[]")
    map_recipe = models.TextField(null=False, default="")
    board_id = models.IntegerField(null=False, default=-1)
    position_assignment = models.TextField(null=False, default="[]")
    start_time = models.DateTimeField(null=True)
    parsed_human_players = [] 
    parsed_position_assignment = [] 
    parsed_seq_data = {}
    
    @classmethod 
    def hasTimer(cls):
        if hasattr(cls, "timer"):
            return True
        else:
            cls.timer = "timer"
            return False

    def initialize(self):
        if self.start_time == None:
            self.start_time = datetime.now(timezone.utc)
        self.parsed_human_players = json.loads(self.human_players)
        self.parsed_position_assignment = json.loads(self.position_assignment)
        self.parsed_seq_data = json.loads(self.seq_data)

    def make_board(self, load_map, map_name, fresh):

        # Only accept rectangular maps
        assert([len(row) == len(load_map[0]) for row in load_map])

        map_width = len(load_map[0])
        map_height = len(load_map)
        game_board = Board.objects.create(width=map_width,height=map_height,game_id=self.id,name=map_name)
        game_board.load_map(load_map)

        # Create AI players
        parsed_AI_players = json.loads(self.AI_players)
        
        for recipe in parsed_AI_players:
            game_board.addAI(recipe[0],recipe[1][0], recipe[1][1], fresh)
        self.board_id = game_board.id
        self.saveState() 

        
    def add_player(self, player):
        if len(self.parsed_human_players) == len(self.parsed_position_assignment):
            print("Error joining, game is full")
            return False

        if player in self.parsed_human_players:
            return False 
        
        acceptable_players = [x[0] for x in self.parsed_position_assignment]
        if player.IP in acceptable_players:
            ind = acceptable_players.index(player.IP)
            
        elif "player" in acceptable_players:
            ind = acceptable_players.index("player")

        else:
            print("player has no place here")
            return False 

        try:
            board = Board.objects.get(id=self.board_id)
        except ObjectDoesNotExist:
            print("Error, trying to add player to non-existent board")
            return False
        
        pos = self.parsed_position_assignment[ind][1]
        board.add_player(player,pos[0],pos[1]) 
        self.parsed_human_players += [player.IP]

        if len(self.parsed_human_players) == len(self.parsed_position_assignment):
            self.ongoing = True
            self.available = False 
            self.parsed_seq_data["players"] = list(board.parsed_pending.keys())
            self.start_time = datetime.now(timezone.utc)
            self.save()

        player.game_id = self.id 
        player.all_game_ids += str(self.id) + ","
        player.save()
        self.saveState()

    def saveState(self):
        self.seq_data = json.dumps(self.parsed_seq_data)
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

    def addAI(self, recipe, row, col, fresh):
        # An AI is controlled by the algo_instance of an agent
        if True: # Assumes that AI do not attempt to join games themselves
            if fresh:
                new_agent = Agent.objects.create(r=row,c=col,token="tokens/token" + str(random.randint(0,99)) + ".png", algorithm=recipe)
                new_agent.save()
                agent_name = new_agent.algo_instance.__class__.__name__ + "_" + str(new_agent.id)
            else:
                old_agent = Agent.objects.get(id=recipe)
                new_agent = Agent.objects.create(r=row,c=col,token=old_agent.token, algorithm=old_agent.algorithm)
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
        for agent_ip in self.IP_Agent:
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
        redirect = ""
        my_game = Game.objects.get(id=self.game_id)
        should_continue = True
        if not my_game.ongoing:
            print("Game has yet to be started")
            return "break" 

        # HACK - bug fix
        if None in self.parsed_pending.values():
            self.updateAI()
        
        
        if caller != "admin":
            if caller.IP not in self.parsed_pending:
                print("Error, player not supposed to be playing on this board")
                return ""
            if not force_next and self.attemptAction(caller.IP, action, test=True):
                self.parsed_pending[caller.IP] = action

        all_done = True
        for player in self.parsed_pending:
            if self.parsed_pending[player] == None or self.parsed_pending[player] == "null":
                all_done = False
                print(player + " has not finished")
                break 
        all_done = all_done or force_next
        if (not Config.objects.get(main=True).timer_enabled and all_done) or (Config.objects.get(main=True).timer_enabled and action=="tick"):
            # Execute all pending actions
            for player in self.parsed_pending:
                if self.parsed_pending[player] is not None:
                    self.attemptAction(player, self.parsed_pending[player], test=False)
                self.parsed_pending[player] = None
            for player in self.parsed_needs_refresh:
                if self.parsed_needs_refresh[player] == "False":
                    print("set " + player + " to true")
                    self.parsed_needs_refresh[player] = "True"
            # Commit all actions 
            self.parsed_history = [None] * len(self.parsed_history) + [deepcopy(self.grid)]
            self.parsed_score_history += [self.getGlobalScore()]
            self.saveState()

            # Determine if game has ended
            seq = Sequence.objects.get(id=my_game.parsed_seq_data["id"])
            if len(self.parsed_history) > seq.parsed_data[my_game.parsed_seq_data["index"]][1]:
                # Move user to next game 
                # Create the next game
                my_game = Game.objects.get(id=self.game_id) 
                my_game.ongoing = False
                my_game.save()
                seq_data = my_game.parsed_seq_data
                seq = Sequence.objects.get(id=seq_data["id"])
                new_index = seq_data["index"]+1
                if new_index >= len(seq.parsed_data):
                    redirect = "end"
                else:
                    map_info = seq.parsed_data[new_index] 
                    players = seq_data["players"]
                    new_game, msg = _create_game(map_info[0],map_info[1],players, False)
                    if new_game is None:
                        redirect = "error"
                    else:
                        new_game.parsed_seq_data["id"] = seq_data["id"]
                        new_game.parsed_seq_data["index"] = new_index
                        new_game.saveState()
                        redirect = "end_round?game_id=" + str(new_game.id) 
                for player_ in self.parsed_needs_refresh:
                    self.parsed_needs_refresh[player_] = redirect
                self.saveState()
                return redirect 
            # AI turn

            self.updateAI()

            # Check if this is an all-bot game
            all_done = True
            for player in self.parsed_pending:
                if self.parsed_pending[player] == None or self.parsed_pending[player] == "null":
                    all_done = False
                    break 

            if all_done:
                redirect = "continue"
            
        return redirect
           
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

        return (self.neighbors, self.connected, agents)

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
    
    @classmethod
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

            message += "<br>Average Score: " + str(round(sum(self.parsed_score_history)/float(len(self.parsed_score_history)), 2))
            for player in self.IP_Agent:
                message += "<br>" + player + ": " + "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[player].token) + "' style='position: relative; z-index:1'>"
            return message
        # Assumes this is a human player
        callerIP = caller.IP  
        output = ""
        if Game.objects.get(id=self.game_id).available:
            output += "Waiting for more player(s).."
        elif self.parsed_pending[callerIP] is None:
            output += "Your Turn"
        else:
            output += "Waiting for other player(s).."
        my_game = Game.objects.get(id=self.game_id)
        seq = Sequence.objects.get(id=my_game.parsed_seq_data["id"])
        output += "<br>(" + str(int(seq.parsed_data[my_game.parsed_seq_data["index"]][1]) - len(self.parsed_history)) + " turns remaining)"
        return output 
        
    def getDisplayCells(self, caller):
        output = {}
        total_covered_set = set()
        repeated_covered_set = []
        if caller == "admin":
            visible_set = set([(x,y) for x in range(self.height) for y in range(self.width)])
            certain_set = set([(x,y) for x in range(self.height) for y in range(self.width)])
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

class Sequence(models.Model):
    name = models.TextField(null=False)
    players = models.TextField(null=True, default='[]')
    data = models.TextField(null=True, default='[]')
    parsed_data = None 
    parsed_players = None

    def initialize(self):
        self.parsed_data = json.loads(self.data)
        self.parsed_players = json.loads(self.players)

def initialize_board(instance, **kwargs):
    instance.initialize()

def initialize_game(instance, **kwargs):
    instance.initialize()

def initialize_sequence(instance, **kwargs):
    instance.initialize()

models.signals.post_init.connect(initialize_board, Board)    
models.signals.post_init.connect(initialize_game, Game)
models.signals.post_init.connect(initialize_sequence, Sequence)

def _create_game(map_name, turns_limit, player,  fresh=True):
    read_map = []
    start_pos = []
    with open(os.path.join(STATIC_ROOT, map_name)) as map_file:
        reader = csv.reader(map_file, delimiter=',')
        for row in reader:
            r = len(read_map)
            for c in range(len(row)):
                if "*" in row[c]:
                    row[c] = row[c].replace('*','')
                    start_pos += [(r,c)]
            read_map += [row]

    if len(start_pos) == 0:
        return (None, "Map does not indicate start locations") 
    elif len(start_pos) != 1 and len(start_pos) != len(player):
        return (None, "Number of start locations does not match number of players") 
    elif len(start_pos) == 1:
        start_pos = [start_pos[0]]*len(player)
    # TEMP - Placeholder for future admin-controlled bot assignment
    if fresh:
        AI_recipes = list(filter(lambda x:x!="player", player))
        human_players = list(filter(lambda x:x=="player", player))
        for i in range(len(AI_recipes)):
            pos_index = random.randint(0, len(start_pos)-1)
            AI_recipes[i] = (AI_recipes[i], start_pos[pos_index])
            del start_pos[pos_index]
        for i in range(len(human_players)):
            pos_index = random.randint(0, len(start_pos)-1)
            human_players[i] = (human_players[i], start_pos[pos_index])
            del start_pos[pos_index]
    else:
        AI_recipes = list(filter(lambda x:"_" in x, player))
        human_players = list(filter(lambda x:"_" not in x, player))
        for i in range(len(AI_recipes)):
            pos_index = random.randint(0, len(start_pos)-1)
            AI_recipes[i] = (AI_recipes[i].split('_')[1], start_pos[pos_index])
            del start_pos[pos_index]
        for i in range(len(human_players)):
            pos_index = random.randint(0, len(start_pos)-1)
            human_players[i] = (human_players[i], start_pos[pos_index])
            del start_pos[pos_index]

    new_game = Game.objects.create(AI_players=json.dumps(AI_recipes), position_assignment=json.dumps(human_players), \
            map_recipe=json.dumps(read_map), max_turns=turns_limit)
    print("Created new game(" + str(new_game.id) + ")")
    
    # new_game.saveState()
    new_game.make_board(read_map, map_name.split(".")[0], fresh)
    if len(human_players) == 0:
        print("set ongoing to true")
        new_game.ongoing = True
        new_game.available = False
        new_game.parsed_seq_data["players"]=list(Board.objects.get(id=new_game.board_id).parsed_pending.keys())
        new_game.save()
    return (new_game, "")

class Config(models.Model):
    timer_enabled = models.BooleanField(null=False,default=False)
    main = models.BooleanField(null=False,default=False)
    

def async_timer(timer_stop):
    ongoing_games = Game.objects.filter(ongoing=True)

    for game in ongoing_games:
        if datetime.now(timezone.utc) - game.start_time >= timedelta(seconds=TURN_TIMER):
            print("tick")
            resp = Board.objects.get(id=game.board_id).handleTurn("admin", "tick")
            print("resp:" + resp)
            if resp != "break" and resp != "continue" and resp!= "":
                game.ongoing = False
            game.start_time = datetime.now(timezone.utc)
            game.save()
    if not timer_stop.is_set():
        threading.Timer(1, async_timer, [timer_stop]).start()


def start_timer():
    if Config.objects.get(main=True).timer_enabled:
        timer_stop = threading.Event()
        print("start timer")
        print(threading.active_count())
        async_timer(timer_stop)
            
