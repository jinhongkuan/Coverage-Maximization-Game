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
from covmax.constants import TURN_TIMER, timer_working, timer_stop
import threading
# Create your models here.

AI_MAX_ATTEMPT = 1000

class Game(models.Model):
    available = models.BooleanField(null=False, default=True)
    ongoing = models.BooleanField(null=False, default=False)
    max_turns = models.IntegerField(null=False, default=0)
    seq_data = models.TextField(null=True, default="{}")
    map_recipe = models.TextField(null=False, default="")
    board_id = models.IntegerField(null=False, default=-1)
    start_time = models.DateTimeField(null=True)
    position_assignment = models.TextField(null=False, default="[]")
    human_players = models.TextField(null=False, default="[]")
    
    parsed_seq_data = {}
    parsed_human_players = {}
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
        self.parsed_seq_data = json.loads(self.seq_data)
        self.parsed_human_players = json.loads(self.human_players)

    def make_board(self, load_map, map_name):
        max_score = load_map[-1][0]
        load_map = load_map[:-1]
        # Only accept rectangular maps
        assert([len(row) == len(load_map[0]) for row in load_map])

        map_width = len(load_map[0])
        map_height = len(load_map)
        game_board = Board.objects.create(width=map_width,height=map_height,game_id=self.id,name=map_name, optimal_score = max_score)
        game_board.load_map(load_map)

        # Create AI players
        token_assignment = self.parsed_seq_data["token_assignment"]
        players = self.parsed_seq_data["players"]
        position_assignment = json.loads(self.position_assignment) # RMB to add this before Game.objects.create
        seq = Sequence.objects.get(id=self.parsed_seq_data["id"])

        if len(token_assignment) == 0:
            for i in range(len(players)):
                new_token = ""
                while (new_token in token_assignment or new_token == ""):
                    new_token = "tokens/token" + random.choice(["green","blue","pink","orange"]) + ".png"
                token_assignment += [new_token]

        for i in range(len(players)):
            corresponding_entity = seq.parsed_players[i]
            if corresponding_entity != "player":
                game_board.addAI(corresponding_entity, position_assignment[i][0], position_assignment[i][1], token_assignment[i], seq.parsed_settings)

        self.board_id = game_board.id
        self.saveState() 

        return game_board

        
    def add_player(self, player):
        max_players = Sequence.objects.get(id=self.parsed_seq_data["id"]).parsed_players.count("player")
        if len(self.parsed_human_players) == max_players:
            print("Error joining, game is full")
            return False

        if player in self.parsed_human_players:
            return False 
        
        seq = Sequence.objects.get(id=self.parsed_seq_data["id"])
        acceptable_players = self.parsed_seq_data["players"]
        position_assignment = json.loads(self.position_assignment)
        token_assignment = self.parsed_seq_data["token_assignment"]

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
        
        pos = position_assignment[ind]
        board.add_player(player,pos[0],pos[1],token_assignment[ind], seq.parsed_settings) 
        self.parsed_human_players += [player.IP]
        self.parsed_seq_data["players"][ind] = player.IP

        if len(self.parsed_human_players) == max_players:
            self.ongoing = True
            print("Set ongoing to true because " + str(self.parsed_human_players) + " contains " + str(max_players) + " players")
            self.available = False 
            self.start_time = datetime.now(timezone.utc)
            self.save()
            board.updateAI()
        player.game_id = self.id 
        player.all_game_ids += str(self.id) + ","
        player.save()
        self.saveState()

    def saveState(self):
        self.seq_data = json.dumps(self.parsed_seq_data)
        self.human_players = json.dumps(self.parsed_human_players)
        self.save()

class Board(models.Model):
    waiting = models.TextField(null=False, default="")
    game_id = models.IntegerField(null=False)
    width = models.IntegerField(null=False)
    height = models.IntegerField(null=False)
    history = models.TextField(null=False, default='[]')
    score_history = models.TextField(null=False, default='[]')
    pending = models.TextField(null=False, default='{}')
    lastclick = models.TextField(null=False, default='{}')
    agents = models.TextField(null=False, default='{}')
    name = models.TextField(null=False, default="")
    needs_refresh = models.TextField(null=False, default='{"admin":"True"}')
    locked = models.BooleanField(null=False, default=False)
    optimal_score = models.IntegerField(null=False, default=0)
    
    grid_type = {'-1': "grey-grid", '0': "white-grid", '1': "black-grid", '2': "singly-covered-grid", '3': "doubly-covered-grid", '4': 'uncertain-grid'}
    grid_val = {}
    parsed_history = []
    parsed_score_history = []
    parsed_pending = {}
    parsed_lastclick = {}
    parsed_needs_refresh = {}
    IP_Player = {}
    IP_Agent = {}
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
        self.parsed_history = json.loads(self.history)
        if len(self.parsed_history) == 0:
            self.grid = []
        else:
            self.grid = deepcopy(self.parsed_history[-1])
          
        parsed_agents = json.loads(self.agents)
        self.parsed_lastclick = json.loads(self.lastclick)
        self.IP_Agent = {}
        for agent in parsed_agents:
            self.IP_Agent[agent] = Agent.objects.get(id=parsed_agents[agent])

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
                                if self.grid[dr][dc] != "1":
                                    self.neighbors[(r,c)] += [(dr, dc)] 
                        # Assign dollar value 
                        if self.grid[r][c] == "2":
                            self.grid_val[(r,c)] = 1 
                        elif self.grid[r][c] == "3":
                            self.grid_val[(r,c)] = 5 
                        else:
                            self.grid_val[(r,c)] = 0
                

        self.parsed_score_history = json.loads(self.score_history)
        
        if len(self.parsed_score_history) == 0 or self.getGlobalScore() == self.getOptimalScore():
            self.parsed_score_history += [self.getGlobalScore()]

        for player in self.IP_Agent:
            self.max_coverage_range = max(self.max_coverage_range, self.IP_Agent[player].coverage)


    def add_player(self, caller, row, col, token_, settings):
        print("add player called ", str(caller))
        if caller.IP not in self.parsed_pending:
            self.parsed_pending[caller.IP] = None 
            new_agent = Agent.objects.create(r=row,c=col,token=token_, coverage=settings["coverage"], sight=settings["sight"], movement=settings["movement"])
            self.IP_Agent[caller.IP] = new_agent 
        for player in self.parsed_needs_refresh:
            self.parsed_needs_refresh[player] = "True"
        self.parsed_needs_refresh[caller.IP] = "False"
        self.saveState()

    def addAI(self, recipe, row, col, token_, settings):
        # An AI is controlled by the algo_instance of an agent
        new_agent = Agent.objects.create(r=row,c=col,token=token_, algorithm=recipe, coverage=settings["coverage"], sight=settings["sight"], movement=settings["movement"])
        new_agent.save()
        
        agent_name = new_agent.algo_instance.__class__.__name__ + "_" + str(new_agent.id)
    
        self.parsed_pending[agent_name] = None 
        self.IP_Agent[agent_name] = new_agent 
        print("AI " + str(agent_name) + " has joined the board")
        self.saveState()


    def updateAI(self):
        for agent_ip in self.IP_Agent:
            if self.IP_Agent[agent_ip].algo_instance is not None and self.parsed_pending[agent_ip] is None:
                exceed_limit = True
                for i in range(AI_MAX_ATTEMPT):
                    
                    action = self.IP_Agent[agent_ip].algo_instance.computeNext(self.generateState(self.IP_Agent[agent_ip]))
                    viable = self.attemptAction(agent_ip, action, test=True)
                    if viable:
                        self.parsed_pending[agent_ip] = action
                        exceed_limit = False
                        break
                if exceed_limit:
                    self.parsed_pending[agent_ip] = json.dumps((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c))
                    print("Error, " + self.IP_Agent[agent_ip].algo_instance.name + " was unable to decide on next action")

        self.saveState()

    def getOptimalScore(self):
        return self.optimal_score

    def handleTurn(self, caller, action, force_next=False):
        redirect = ""
        my_game = Game.objects.get(id=self.game_id)
        should_continue = True
        if not my_game.ongoing:
            return "break" 
        
        # Fail-safe check
        if None in self.parsed_pending.values():
            for agent in self.parsed_pending:
                if self.parsed_pending[agent] == None and "_" in agent:
                    print("Fail-safe activated")
                    self.updateAI()
                    break

        if caller != "admin":
            if caller.IP not in self.parsed_pending:
                print("Error, player not supposed to be playing on this board")
                return "error"
            if not force_next and self.attemptAction(caller.IP, action, test=True):

                # Only accept moves when it is the player's turn
                if caller.IP == self.waiting:
                    self.parsed_pending[caller.IP] = action
                else:
                    self.parsed_pending[caller.IP] = None
                self.parsed_lastclick[caller.IP] = action

        all_done = True
        for player in self.parsed_pending:
            if self.parsed_pending[player] == None or self.parsed_pending[player] == "null":
                all_done = False
                break 
        all_done = all_done or force_next

        # Modified to fit sequential
        if (not Config.objects.get(main=True).timer_enabled and all_done) or (Config.objects.get(main=True).timer_enabled and (caller=="admin" or all_done)):
            # Execute all pending actions
            # test1
            for player in self.parsed_pending:
                if self.parsed_pending[player] is None:
                    if player in self.parsed_lastclick and self.parsed_lastclick[player] is not None and self.waiting == player:
                        self.parsed_pending[player] = self.parsed_lastclick[player] 
                    else:
                        self.parsed_pending[player] = json.dumps((self.IP_Agent[player].r,self.IP_Agent[player].c))
                self.attemptAction(player, self.parsed_pending[player], test=False)
                    
                # self.parsed_pending[player] = None
            # Sequential mechanism
            self.waiting = random.choice(list(self.parsed_pending.keys()))
            self.parsed_pending[self.waiting] = None
            
            for player in self.parsed_needs_refresh:
                if self.parsed_needs_refresh[player] == "False":
                    self.parsed_needs_refresh[player] = "True"
            # Commit all actions 
            # Condense memory to only positions
            if (len(self.parsed_history)-1) % Config.objects.get(main=True).snapshot_interval == 0:
                self.parsed_history[-1] = {}
                for agent in self.IP_Agent:
                    self.parsed_history[-1][agent] = (self.IP_Agent[agent].r, self.IP_Agent[agent].c) 
            else:
                self.parsed_history[-1] = None 
            self.parsed_history += [deepcopy(self.grid)]
            self.parsed_score_history += [self.getGlobalScore()]
            self.saveState()

            # Determine if game has ended
            seq = Sequence.objects.get(id=my_game.parsed_seq_data["id"])
            if len(self.parsed_history) > seq.parsed_data[my_game.parsed_seq_data["index"]][1]:
                my_game.ongoing = False
                my_game.save()
                for player_ in self.IP_Player:
                    new_game_id = Config.objects.get(main=True).generate_game(self.IP_Player[player_].id).id
                    redirect = "end_round?game_id=" + str(new_game_id)  + "&a=" + str(self.getGlobalScore()) + "&b=" + str(self.getOptimalScore()) + "&pg_id=" + str(self.game_id)
                    print(player_, ":",redirect)
                    self.parsed_needs_refresh[player_] = redirect 
                self.saveState()
                '''
                    # Move user to next game 
                # Create the next game
                my_game = Game.objects.get(id=self.game_id) 
                my_game.ongoing = False
                my_game.save()

                if False:
                    seq_data = my_game.parsed_seq_data
                    seq = Sequence.objects.get(id=seq_data["id"])
                    new_index = seq_data["index"]+1
                    if new_index >= len(seq.parsed_data):
                        if "next_seq" in seq.parsed_settings:
                            try:
                                next_seq = Sequence.objects.get(name=seq.parsed_settings["next_seq"])
                            except ObjectDoesNotExist:
                                print("End view error: Next seq does not exist")
                            # Update AI name
                            players = my_game.parsed_seq_data["players"]
                            ai_players = [x for x in players if "(" in x]
                            ai_players_new = [x for x in next_seq.parsed_players if x != "player"]
                            if len(ai_players) != len(ai_players_new):
                                print("End view error: AI counts mismatch")
                            for i in range(len(players)):
                                if "(" in players[i]:
                                    players[i] = ai_players_new[0]
                                    ai_players_new = ai_players_new[1:]
                            seq_data = seq_data = {"index": 0, "id": next_seq.id, "token_assignment":[], "players": players}
                            new_game, msg = _create_game(seq_data)
                            for ply in Player.objects.all():
                                if ply.game_id == self.game_id:
                                    ply.redirected_gameid = new_game.id 
                                    ply.save()
                            # redirect = "end_round?game_id=-1"  + "&a=" + str(self.getGlobalScore()) + "&b=" + str(self.getOptimalScore() ) + "&pg_id=" + str(self.game_id)
                            redirect = "end_round?game_id=" + str(new_game.id) + "&a=" + str(self.getGlobalScore()) + "&b=" + str(self.getOptimalScore() ) + "&pg_id=" + str(self.game_id)
                        else:
                            redirect = "end_round?game_id=-2"  + "&a=" + str(self.getGlobalScore()) + "&b=" + str(self.getOptimalScore() ) + "&pg_id=" + str(self.game_id)

                    else:
                        new_data = deepcopy(seq_data)
                        new_data["index"] = new_index
                        new_game, msg = _create_game(new_data)
                        if new_game is None:
                            redirect = "error"
                        else:
                            redirect = "end_round?game_id=" + str(new_game.id)  + "&a=" + str(self.getGlobalScore()) + "&b=" + str(self.getOptimalScore()) + "&pg_id=" + str(self.game_id)
                else:
                '''
                
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

        return (self.neighbors, self.connected, agents, self.grid_val)

    def attemptAction(self, callerIP, action, test=False, no_pending=False):
        try:
            agent=self.IP_Agent[callerIP]
        except KeyError:

            # print("Error, action performed by non-existent player " + str(callerIP))
            # print("not in " + str(self.IP_Agent))
            return False
        original_r, original_c = agent.r, agent.c
        action_parsed = json.loads(action)
        dr, dc = action_parsed
        agent.r = dr 
        agent.c = dc 
        accessible = Board.getCoveredSet((original_r, original_c), agent.movement, self.neighbors)
        if agent.r >= 0 and agent.r < self.height and agent.c >= 0 and agent.c < self.width and self.grid[agent.r][agent.c] != "1" and (dr, dc) in accessible:
            if test:
                agent.r = original_r
                agent.c = original_c
                if not no_pending:
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

    def getMessage(self, caller, history=-1):
        if caller == "admin":
            message = "You are currently spectating the game as an admin"
            if history != -1:
                data_points = 0 
                for i in range(len(self.parsed_history)):
                    if self.parsed_history[i] is not None:
                        data_points += 1 
                        if data_points == history:
                            history = i 
                            break
                message += "<br>Turn: " + str(history) 
            message += "<br>Average Score: " + str(round(sum(self.parsed_score_history)/float(len(self.parsed_score_history)), 2))
            for player in self.IP_Agent:
                x = Player.objects.filter(IP=player)
                if len(x) == 1:
                    x = x[0].name 
                else:
                    x = player
                message += "<br>" + x + ": " + "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[player].token) + "' style='position: relative; z-index:1'>"
            return message
        # Assumes this is a human player
        callerIP = caller.IP  
        output = ""
     
        if Game.objects.get(id=self.game_id).available:
            output += "Waiting for more player(s).."
        elif callerIP == self.waiting:
            output += "Your Move"
        else:
            if not self.waiting == "":
                output += "Waiting for other player: <img src='{0}' style='width: 25px; height: 25px; vertical-align: middle'></img>".format(os.path.join(STATIC_URL,self.IP_Agent[self.waiting].token))
        my_game = Game.objects.get(id=self.game_id)
        seq = Sequence.objects.get(id=my_game.parsed_seq_data["id"])
        output += "<br>(" + str(int(seq.parsed_data[my_game.parsed_seq_data["index"]][1]) - len(self.parsed_history)) + " turns remaining)"
        output += "<br><br><div style='align:center'>"
        output += "<img src='{0}' style='width: 25px; height: 25px;'></img> <i> = 1 score</i>".format(os.path.join(STATIC_URL,"tokens/dollar1_.png"))
        output += "<br><img src='{0}' style='width: 25px; height: 25px;'></img> <i> = 5 score</i>".format(os.path.join(STATIC_URL,"tokens/dollar5_.png"))
        output += "</br>"
        return output 
        
    def getDisplayCells(self, caller, history=-1):
        output = {}
        total_covered_set = set()
        repeated_covered_set = []
        seq = Sequence.objects.get(id=(Game.objects.get(id=self.game_id).parsed_seq_data["id"]))
        show_obstacles = seq.parsed_settings["map_knowledge"] == 'true'
        if caller == "admin":
            visible_set = set([(x,y) for x in range(self.height) for y in range(self.width)])
            certain_set = set([(x,y) for x in range(self.height) for y in range(self.width)])
        else:
            visible_set = self.getCoveredSet((self.IP_Agent[caller.IP].r, self.IP_Agent[caller.IP].c), self.IP_Agent[caller.IP].sight, self.connected)
            certain_set = self.getCoveredSet((self.IP_Agent[caller.IP].r, self.IP_Agent[caller.IP].c), 1, self.connected)

        if history==-1 or history==len([x for x in self.parsed_history if x is not None]):
            for agent_ip in self.IP_Agent:
                if (self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c) not in visible_set:
                    continue
                x = self.getCoveredSet((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c), self.IP_Agent[agent_ip].coverage, self.neighbors)
                total_covered_set = total_covered_set.union(x)
                repeated_covered_set += list(x)
        else:
            snapshots = 0
            for i in range(len(self.parsed_history)):
                if self.parsed_history[i] != None:
                    snapshots+= 1
                    if snapshots == history:
                        snapshot = self.parsed_history[i]
                        history = i
                        for agent_ip in snapshot:

                            x = self.getCoveredSet(tuple(snapshot[agent_ip]), self.IP_Agent[agent_ip].coverage, self.neighbors)
                            total_covered_set = total_covered_set.union(x)
                            repeated_covered_set += list(x)
                        break 
        for element in total_covered_set:
            repeated_covered_set.remove(element)
        
        repeated_covered_set = set(repeated_covered_set)
        for r in range(self.height):
            for c in range(self.width):
                key = (r,c)
                content = ""
                if key not in visible_set:
                    if show_obstacles and self.grid[r][c] == "1":
                        val = "1"
                    else:
                        val = "-1"
                else:
                    if self.grid[r][c] == "0" or self.grid[r][c] == "2" or self.grid[r][c] == "3":
                        if key not in certain_set:
                            val = "4"
                        elif key in repeated_covered_set:
                            val = "3"
                        elif key in total_covered_set:
                            val = "2"
                        else:
                            val = "4"

                    else:
                        val = "1"
                    if self.grid[r][c] == "2":
                        content += "<img src='"+ os.path.join(STATIC_URL,"tokens/dollar1_.png") +"' style='position:absolute; left: 0px; height: 50px; width: 50px'>"
                    elif self.grid[r][c] == "3":
                        content += "<img src='"+ os.path.join(STATIC_URL,"tokens/dollar5_.png") +"' style='position:absolute; left: 0px; height: 50px; width: 50px'>"
              
                content_agent = ""
                if history==-1 or history==len([x for x in self.parsed_history if x is not None]):
                    
                    for agent in self.IP_Agent:
                        if self.IP_Agent[agent].r == r and self.IP_Agent[agent].c == c and val != "-1":
                            if caller != "admin" and agent == caller.IP:
                                content_agent += "<img src='"+ os.path.join(STATIC_URL,"tokens/player.png") +"' style='position:absolute; z-index:2; top: 6px; left: 13.5px'>"
                                content_agent += "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position:absolute; top: 25px; left: 25px; transform: translate(-50%, -50%); width: 40px; height 40px'>"
                            else:
                                content_agent += "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position:absolute; top: 25px; left: 25px; transform: translate(-50%, -50%); width: 40px; height 40px'>"
                else:
                    snapshot = self.parsed_history[history]
                    for agent in snapshot:
                        if tuple(snapshot[agent]) == (r,c) and val != "-1":
                            if caller != "admin" and agent == caller.IP:
                                content_agent += "<img src='"+ os.path.join(STATIC_URL,"tokens/player.png") +"' style='position:absolute; z-index:2;  top: 6px; left: 13.5px'>"
                                content_agent += "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position:absolute; top: 25px; left: 25px; transform: translate(-50%, -50%); width: 40px; height 40px'>"
                            else:
                                content_agent += "<img src='" + os.path.join(STATIC_URL,self.IP_Agent[agent].token) + "' style='position:absolute; top: 25px; left: 25px; transform: translate(-50%, -50%); width: 40px; height 40px'>"
                
                content += content_agent
                output[key] = (self.grid_type[val] + (" hover-highlight" if caller!="admin" and self.attemptAction(caller.IP, json.dumps([r,c]), test=True, no_pending=True) else ""), content)
        return output 
    
    def getGraphData(self):
        pass 

    def getScore(average=True):
        if average:
            return sum(self.parsed_score_history)/len(self.parsed_score_history)
        else:
            return self.parsed_score_history[-1]
            
    def getGlobalScore(self):
        total_covered_set = set()
        for agent_ip in self.IP_Agent:
            x = self.getCoveredSet((self.IP_Agent[agent_ip].r, self.IP_Agent[agent_ip].c), self.IP_Agent[agent_ip].coverage, self.neighbors)
            total_covered_set = total_covered_set.union(x)
        return sum(self.grid_val[x] for x in total_covered_set)

    def saveState(self):
        self.history = json.dumps(self.parsed_history)
        self.pending = json.dumps(self.parsed_pending)
        self.lastclick = json.dumps(self.parsed_lastclick)
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
    settings = models.TextField(null=False, default='{"coverage": 1, "sight": 3, "movement": 1, "map_knowledge":"false"}')
    parsed_data = None 
    parsed_players = None
    parsed_settings = None 
    def initialize(self):
        self.parsed_data = json.loads(self.data)
        self.parsed_players = json.loads(self.players)
        self.parsed_settings = json.loads(self.settings)

def initialize_board(instance, **kwargs):
    instance.initialize()

def initialize_game(instance, **kwargs):
    instance.initialize()

def initialize_sequence(instance, **kwargs):
    instance.initialize()

models.signals.post_init.connect(initialize_board, Board)    
models.signals.post_init.connect(initialize_game, Game)
models.signals.post_init.connect(initialize_sequence, Sequence)

def _create_game(seq_data_):
    map_name = Sequence.objects.get(id=seq_data_["id"]).parsed_data[seq_data_["index"]][0]
    turns_limit = Sequence.objects.get(id=seq_data_["id"]).parsed_data[seq_data_["index"]][1]

    if len(seq_data_["players"]) == 0:
        seq_data_["players"] = copy(Sequence.objects.get(id=seq_data_["id"]).parsed_players)
    player = seq_data_["players"]
    
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

    

    new_game = Game.objects.create(seq_data=json.dumps(seq_data_), position_assignment=json.dumps(start_pos), \
            map_recipe=json.dumps(read_map), max_turns=turns_limit)
    print("Created new game(" + str(new_game.id) + ")")
    print(new_game.parsed_seq_data)
    # new_game.saveState()
    

    
    new_board = new_game.make_board(read_map, map_name.split(".")[0])
    

    if Sequence.objects.get(id=seq_data_["id"]).parsed_players.count("player") == 0:
        print("set ongoing to true")
        new_game.ongoing = True
        new_game.available = False
        new_game.parsed_seq_data["players"]=list(Board.objects.get(id=new_game.board_id).parsed_pending.keys())
        new_board.updateAI()
    new_game.saveState()
    return (new_game, "")

class Config(models.Model):
    timer_enabled = models.BooleanField(null=False,default=False)
    snapshot_interval = models.IntegerField(null=False, default=1)
    main = models.BooleanField(null=False,default=False)
    assigner = models.TextField(null=False, default='{"table":{},"progress":{}}')

    parsed_assigner = None
    assigner_table = { 0: [-1,-2,-3,-4],
        1: [-5,-6,-7,-8],
        2: [-5,-6,-7,-8],
        3: [-9,-10,-11,-12],
        4: [-9,-10,-11,-12],
        5: [-9,-10,-11,-12]
    }
    assigner_table2 = {
        0: [-5,-6,-3,-4],
        1: [-1,-2,-3,-4],
        2: [-5,-10,-8,-9],
        3: [-7,-2,-8,-9],
        4: [-7,-10,-11,-4],
        5: [-7,-10,-3,-12]
    }
    # Game: Map, Player count
    assigner_seq2 = {
        1: (0,1),
        2: (1,2),
        3: (2,3),
        4: (3,3),
        5: (0,2),
        6: (1,1),
        7: (0,3),
        8: (2,2),
        9: (3,2),
        10: (1,3),
        11: (2,1),
        12: (3,1)
    }

    assigner_seq = {
        1: (0,1),
        2: (1,1),
        3: (2,1),
        4: (3,1),
        5: (0,2),
        6: (1,2),
        7: (2,2),
        8: (3,2),
        9: (0,3),
        10: (1,3),
        11: (2,3),
        12: (3,3)
    }
    def generate_seq(self, _name, maps, bot):
        for i in range(12):
            Sequence.objects.create(name="seq_"+_name+"_"+str(i+1), \
                data=json.dumps([maps[self.assigner_seq[i+1][0]]]), \
                    players=json.dumps(["player"]*self.assigner_seq[i+1][1]+[bot]*(3-self.assigner_seq[i+1][1])))


    def generate_game(self,player_id):
        # Progress ranges from 0 to 3, initialized to -1
        print("game has ended!")
        real_id = player_id - Player.objects.first().id
        if str(real_id) not in self.parsed_assigner['table']:
            tab =  self.parsed_assigner['table']
            prog =  self.parsed_assigner['progress']
            assert(real_id % 6 == 0)
            for di in self.assigner_table:
                self.parsed_assigner['table'][str(real_id + di)] = copy(self.assigner_table[di])
                self.parsed_assigner['progress'][str(real_id + di)] = -1
        self.parsed_assigner['progress'][str(real_id)] += 1 
        # Update 
        # Find current progress 
        if self.parsed_assigner['progress'][str(real_id)] == 3:
            self.assigner = json.dumps(self.parsed_assigner)
            self.save()
            print(self.parsed_assigner['progress'])
            return None # Player is done 
        else:
            
            progress = self.parsed_assigner['progress'][str(real_id)]
            print(self.parsed_assigner)
            if self.parsed_assigner['table'][str(real_id)][progress] < 0:
                # Hasn't been assigned a game yet, create one and assign peers to it 
                ind = abs(self.parsed_assigner['table'][str(real_id)][progress])
                
                # Create game 
                seq_data = {}
                seq_data["id"] = Sequence.objects.get(name="seq_exp3_" + str(ind)).id
                seq_data["index"] = 0 # '-7' corresponds to the 7th game in the table 
                seq_data["players"] = [] # Temporary hack 
                seq_data["token_assignment"] = [] # Temporary hack 
                new_game, msg = _create_game(seq_data)
                # Update everyone else 
                for i in range(6):
                    peer_id = (real_id // 6) * 6 + i
                    for j, cell in enumerate(self.parsed_assigner['table'][str(peer_id)]):
                        if cell == -ind:
                            self.parsed_assigner['table'][str(peer_id)][j] = new_game.id 

                self.assigner = json.dumps(self.parsed_assigner)
                self.save()
                return new_game
            else:
                game = Game.objects.get(id=self.parsed_assigner['table'][str(real_id)][progress])
                self.assigner = json.dumps(self.parsed_assigner)
                self.save()
                return game

        



def initialize_config(instance, **kwargs):
    instance.parsed_assigner = json.loads(instance.assigner)
    


models.signals.post_init.connect(initialize_config, Config)

def async_timer(timer_stop):
    ongoing_games = Game.objects.filter(ongoing=True)
    for game in ongoing_games:
        if datetime.now(timezone.utc) - game.start_time >= timedelta(seconds=TURN_TIMER):
            resp = Board.objects.get(id=game.board_id).handleTurn("admin", "tick")
            if resp != "break" and resp != "continue" and resp!= "":
                game.ongoing = False
            game.start_time = datetime.now(timezone.utc)
            game.save()
    if not timer_stop.is_set():
        threading.Timer(1, async_timer, [timer_stop]).start()


def start_timer(timer_working, timer_stop):
    if Config.objects.get(main=True).timer_enabled:
        timer_working = True
        async_timer(timer_stop)
            
