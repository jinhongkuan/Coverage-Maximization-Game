import json
import csv
import os 
import random
from ipware import get_client_ip
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from player.models import Player
from game.models import Board, Game
from covmax.settings import STATIC_ROOT
from covmax.constants import MAP_NAMES, MAX_PLAYERS
import PIL, PIL.Image
from io import BytesIO, StringIO
import plotly
import plotly.graph_objects as go 
def main_view(request):

    return render(request, "main.html")


def game_view(request):

    ip, _ = get_client_ip(request)
    try:
        player = Player.objects.get(IP=ip)
    except ObjectDoesNotExist:
        player = Player.objects.create(IP=ip,active=True)
        print("Created new player with ip " + str(player.IP))

    print("Connection from " + str(ip))

    if "command" in request.POST:
        if request.POST["command"] == "Start Session":
            # Check if there are other on-going games
            open_games = Game.objects.filter(ongoing=False)

            # Remove games initiated by this player
            open_games = [x for x in open_games if ip not in Board.objects.get(id=x.board_id).parsed_pending]

            if len(open_games) == 0:
                print("Creating a new game")
                if "map_name" in request.POST:
                    map_name = request.POST["map_name"]
                else:
                    map_name = MAP_NAMES[0] 

                read_map = []
                start_pos = None
                with open(os.path.join(STATIC_ROOT, map_name)) as map_file:
                    reader = csv.reader(map_file, delimiter=',')
                    for row in reader:
                        r = len(read_map)
                        for c in range(len(row)):
                            if "*" in row[c]:
                                row[c] = row[c].replace('*','')
                                start_pos = (r,c)
                        read_map += [row]

                if start_pos is None:
                    return render(request, "error.html", {"error_code": "Map does not indicate start locations"})
                
                # TEMP - Placeholder for future admin-controlled bot assignment
                AI_recipes = []
                human_count = 1
                for i in range(MAX_PLAYERS[MAP_NAMES.index(map_name)]-human_count):
                    AI_recipes += [("Conscientious(instance,1,0.5)",start_pos)]
                AI_recipes = json.dumps(AI_recipes)
                human_positions = json.dumps([start_pos]*human_count)
                new_game = Game.objects.create(AI_players=AI_recipes, position_assignment=human_positions, \
                     map_recipe=json.dumps(read_map))

                new_game.make_board(read_map, map_name.split(".")[0])

                new_game.add_player(player)
                player.game_id = new_game.id 
                player.all_game_ids += str(new_game.id) + ","
            else:
                # TEMP - Pick the oldest open game
                game = open_games[0]
                parsed_pending = json.loads(Board.objects.get(id=game.board_id).pending)
                game.add_player(player)                    
                player.game_id = game.id 
                player.all_game_ids += str(game.id) + ","
            
            player.save()
                
        elif request.POST["command"] == "Continue Session":  
            if player.game_id == -1:
                return main_view(request)
            else:
                pass
 
    
    if "name" in request.POST:
        player.name = request.POST["name"]
        player.save()

    if player.name == "":
        return render(request, "name_set.html")

    return render(request, "game.html")

def board_view(request):
    ip, _ = get_client_ip(request)

    if "admin" in request.POST and request.POST["admin"]:
        player_board = Board.objects.get(id=Game.objects.get(id=request.POST["game_id"]).board_id)
        while (player_board.locked):
            pass 
        view_context = {
            "cells" : player_board.getDisplayCells("admin"),
            "message" : player_board.getMessage("admin"),
            "map_name" : player_board.getName()
        }

        if player_board.parsed_needs_refresh["admin"]=="True":
            player_board.parsed_needs_refresh["admin"] = "False"
            player_board.saveState()
    else:
        # Obtain player
        try:
            player = Player.objects.get(IP=ip)
        except ObjectDoesNotExist:
            player = Player.objects.create(IP=ip,active=True)
            print("Created new player with IP " + str(ip))

        # Obtain player Game & Board
        if player.game_id == -1:
            return render(request, "error.html", {"error_code": "Unable to locate player game"})
        else:
            try:
                player_board = Board.objects.get(id=Game.objects.get(id=player.game_id).board_id)
            except ObjectDoesNotExist as e:
                return render(request, "error.html", {"error_code": str(e)})
        
        # Respond to poll requests
        if request.method == "GET" and "poll" in request.GET:
            if "admin" in request.GET:
                return HttpResponse(player_board.parsed_needs_refresh["admin"])
            else:
                return HttpResponse(player_board.parsed_needs_refresh[player.IP] if player.IP in player_board.parsed_needs_refresh else "False")
        # Respond to input requests
        redirect = "" 
        if "click_data" in request.POST:
            click_data = request.POST["click_data"]
            click_data = eval(click_data)
            continue_game = player_board.handleTurn(player, json.dumps(click_data))
            if not continue_game:
                if MAP_NAMES.index(player_board.getName(True)) < len(MAP_NAMES) - 1:
                    redirect = "end_round?map=" + MAP_NAMES[MAP_NAMES.index(player_board.getName(True))+1]
                    for player_ in player_board.parsed_needs_refresh:
                        player_board.parsed_needs_refresh[player_] = redirect
                else:
                    redirect = "end"
                    for player_ in player_board.parsed_needs_refresh:
                        player_board.parsed_needs_refresh[player_] = redirect

        view_context = {
            "cells" : player_board.getDisplayCells(player),
            "message" : player_board.getMessage(player),
            "map_name" : player_board.getName(),
            "redirect" : redirect
        }

        if player_board.parsed_needs_refresh[player.IP]=="True":
            player_board.parsed_needs_refresh[player.IP] = "False"
        
        player_board.saveState()

    return render(request, "board.html", view_context)
    
def make_href(text, link):
    return "<a href='" + str(link) + "'>" + str(text) + "</a>"

def admin_view(request):
    player_table = []
    redirect_url = "adminview?game_id="
    for player in Player.objects.all():
        player_table += [[]]
        past_games = ""
        for game_id in player.all_game_ids.split(","):
            if game_id == "":
                continue
            past_games += ("," if len(past_games) > 0 else "") + make_href(game_id, redirect_url+str(game_id))
        player_table[-1] += [player.IP, player.name, past_games]

    game_table = []
    for game in Game.objects.all():
        try:
            corresponding_board = Board.objects.get(id=game.board_id)
            game_table += [[]]
            game_table[-1] += [game.id, corresponding_board.getName(), list(corresponding_board.parsed_pending.keys()), len(corresponding_board.parsed_history)]
        except ObjectDoesNotExist:
            pass

    view_context = {
        "player_table" : player_table,
        "game_table" : game_table
    }

    return render(request, "admin.html", view_context)
    
def admin_observation_view(request):
    if "game_id" in request.GET:
        return render(request, "admin_observation.html", {"game_id" : request.GET["game_id"] })
    else:
        return HttpResponse("Error, please stipulate game id to observe")

def graph_view(request):
    if "game_id" in request.POST:
        player_board = Board.objects.get(id=Game.objects.get(id=request.POST["game_id"]).board_id)
        score_history = player_board.parsed_score_history
        print(score_history)
        fig = go.Figure(data=[go.Scatter(y=score_history)])
        fig.update_layout(height=600,xaxis=go.layout.XAxis(
        title=go.layout.xaxis.Title(
            text="Turns",
            font=dict(
                family="Courier New, monospace",
                size=18,
                color="#7f7f7f"
            )
        )
    ),
    yaxis=go.layout.YAxis(
        title=go.layout.yaxis.Title(
            text="# Covered",
            font=dict(
                family="Courier New, monospace",
                size=18,
                color="#7f7f7f"
            )
        )
    ))
        graph_div = plotly.offline.plot(fig, auto_open= False, output_type="div")
        return render(request, "graph.html", {"graph_div":graph_div})# HttpResponse(buffer.getvalue(), mimetype="image/png")
    else:
        return HttpResponse("Error, please stipulate game id to observe")

def end_round_view(request):
    return render(request, "end_round.html", {"map_name": request.GET["map"]})