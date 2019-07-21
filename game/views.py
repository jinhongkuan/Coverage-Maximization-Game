import json
import os 
import random
from ipware import get_client_ip
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from player.models import Player
from game.models import Board, Game, Sequence, _create_game
import csv
from covmax.settings import STATIC_ROOT
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
                default_seq_name= "seq0"
                fresh = True
                seq = Sequence.objects.get(name=default_seq_name)
                new_index = 0
                map_info = seq.parsed_data[0] 
                players = seq.parsed_players
                new_game, msg = _create_game(map_info[0], map_info[1], players, fresh)
                if new_game is None:
                    render(request, "error.html", {"error_code": msg})
                else:
                    new_game.parsed_seq_data["id"] = seq.id
                    new_game.parsed_seq_data["index"] = new_index
                    # new_game.saveState()
                    new_game.add_player(player)
                

            else:
                # TEMP - Pick the oldest open game
                print("Found other open games")
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

        elif request.POST["command"] == "Join Session":
            game_id = request.POST["game_id"]
            game = Game.objects.get(id=game_id)
            game.add_player(player)
          
 
    
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
            my_game = Game.objects.get(id=player.game_id)
            try:
                player_board = Board.objects.get(id=my_game.board_id)
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
            redirect = player_board.handleTurn(player, json.dumps(click_data))
                    

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
    sequence_table = []
    game_table = []
    message = ""
    redirect_url = "adminview?game_id="

    if "del" in request.GET:
        id_to_remove = request.GET["del"]
        try:
            Sequence.objects.get(id=id_to_remove).delete() 
        except:
            pass

    if "test" in request.GET:
        id_to_test = request.GET["test"]
        seq = Sequence.objects.get(id=id_to_test)
        if "player" in seq.parsed_players:
            message += "Error testing game " + str(id_to_test) + ": game requires human players\n"
        else:
            seq = Sequence.objects.get(id=id_to_test)
            new_index = 0
            map_info = seq.parsed_data[0] 
            players = seq.parsed_players
            new_game, msg = _create_game(map_info[0], map_info[1], players, True)
            if new_game is None:
                render(request, "error.html", {"error_code": msg})
            else:
                new_game.parsed_seq_data["id"] = seq.id
                new_game.parsed_seq_data["index"] = new_index
                new_game.saveState()
            # Resolve all-bot games 
            fin = Board.objects.get(id=new_game.board_id).handleTurn("admin","test")
            print("res=" + str(fin))
            if fin == "end":
                # Successful resolution
                pass

        

    if "add" in request.POST:
        Sequence.objects.create(name=request.POST["add"], players=request.POST["players"],data=request.POST["data"])

    for seq in Sequence.objects.all():
        sequence_table += [[seq.id,  seq.name,seq.players, seq.data]]

    for player in Player.objects.all():
        player_table += [[]]
        past_games = ""
        for game_id in player.all_game_ids.split(","):
            if game_id == "":
                continue
            past_games += ("," if len(past_games) > 0 else "") + make_href(game_id, redirect_url+str(game_id))
        player_table[-1] += [player.IP, player.name, past_games]


    for game in Game.objects.all():
        try:
            corresponding_board = Board.objects.get(id=game.board_id)
            game_table += [[]]
            game_table[-1] += [make_href(game.id, redirect_url+str(game.id)), corresponding_board.getName(), list(corresponding_board.parsed_pending.keys()), len(corresponding_board.parsed_history)]
        except ObjectDoesNotExist:
            pass

    view_context = {
        "player_table" : player_table,
        "game_table" : game_table,
        "sequence_table" : sequence_table,
        "message" : message
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
    return render(request, "end_round.html", {"game_id": request.GET["game_id"]})