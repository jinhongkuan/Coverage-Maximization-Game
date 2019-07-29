import json
import os 
import random
from ipware import get_client_ip
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from player.models import Player
from game.models import Board, Game, Sequence, Config, _create_game, start_timer
from covmax.constants import timer_working, timer_stop 
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

    if "command" in request.POST:
        if request.POST["command"] == "Start Session":
            # Check if there are other available games
            open_games = Game.objects.filter(available=True)

            # Remove games initiated by this player
            
            open_games = [x for x in open_games if len(Board.objects.filter(id=x.board_id)) == 1 and ip not in Board.objects.get(id=x.board_id).parsed_pending]

            if len(open_games) == 0:
                default_seq_name= "seq0"
                fresh = True
                seq_data = {"index": 0, "id": Sequence.objects.get(name=default_seq_name).id, "token_assignment":[], "players": []}
                new_game, msg = _create_game(seq_data)
                if new_game is None:
                    render(request, "error.html", {"error_code": msg})
                else:
                    new_game.add_player(player)
                

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
        hist_request = -1 if "history" not in request.POST else int(request.POST["history"])
        view_context = {
            "cells" : player_board.getDisplayCells("admin", history=hist_request),
            "message" : player_board.getMessage("admin", history=hist_request),
            "map_name" : player_board.getName()
        }
        if player_board.parsed_needs_refresh["admin"]=="True":
            player_board.parsed_needs_refresh["admin"] = "False"
            player_board.saveState()
    else:
        # Respond to admin poll requests
        if request.method == "GET" and "poll" in request.GET:
            if "admin" in request.GET:
                try:
                    player_board = Board.objects.get(id=Game.objects.get(id=request.GET["game_id"]).board_id)
                except ObjectDoesNotExist as e:
                    return render(request, "error.html", {"error_code": str(e)})
                return HttpResponse(player_board.parsed_needs_refresh["admin"])

        # Obtain player
        try:
            player = Player.objects.get(IP=ip)
        except ObjectDoesNotExist:
            player = Player.objects.create(IP=ip,active=True)

        # Obtain player Game & Board
        if player.game_id == -1:
            return render(request, "error.html", {"error_code": "Unable to locate player game"})
        else:
            my_game = Game.objects.get(id=player.game_id)
            try:
                player_board = Board.objects.get(id=my_game.board_id)
            except ObjectDoesNotExist as e:
                return render(request, "error.html", {"error_code": str(e)})
        
        # Respond to player post request
        if request.method == "GET" and "poll" in request.GET:
            resp = player_board.parsed_needs_refresh[player.IP] if player.IP in player_board.parsed_needs_refresh else "False"
            print("Poll Response: " + str(resp))
            return HttpResponse(resp)

        
        
        # Respond to input requests
        redirect = "" 
        if "click_data" in request.POST:
            click_data = request.POST["click_data"]
            click_data = eval(click_data)
            redirect = player_board.handleTurn(player, json.dumps(click_data))
            if redirect == "continue":
                raise Exception # Not supposed to auto-resolve when there are players 
            elif redirect == "break":
                redirect = ""
                    

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
    print("view ")
    player_table = []
    sequence_table = []
    game_table = []
    configuration_table = {}
    message = ""
    redirect_url = "adminview?game_id="
    if "del" in request.GET:
        id_to_remove = request.GET["del"]
        try:
            Sequence.objects.get(id=id_to_remove).delete() 
            return HttpResponseRedirect("admin")
        except Exception as e:
            print(str(e))

    if "game_del" in request.GET:
        id_to_remove = request.GET["game_del"]
        try:
            Game.objects.get(id=id_to_remove).delete() 
            return HttpResponseRedirect("admin")
        except Exception as e:
            print(str(e))

    if "test" in request.GET:
        id_to_test = request.GET["test"]
        seq = Sequence.objects.get(id=id_to_test)
        if "player" in seq.parsed_players:
            message += "Error testing game " + str(id_to_test) + ": game requires human players\n"
        else:
            seq_data = {"index": 0, "id": id_to_test, "token_assignment":[], "players": []}
            new_game, msg = _create_game(seq_data)
            if new_game is None:
                render(request, "error.html", {"error_code": msg})

            # Resolve all-bot games
            fin = Board.objects.get(id=new_game.board_id).handleTurn("admin","test")
            current_id = new_game.board_id
            while True: 
                if fin == "continue":
                    fin = Board.objects.get(id=current_id).handleTurn("admin","test")
                    continue
                elif fin == "break" or fin == "end":
                    break
                elif fin == "error":
                    message = "Error creating board"
                    break  
                else:
                    print("fin:" + str(fin))
                    current_id = Game.objects.get(id=int(fin.split('=')[1])).board_id
                    fin = Board.objects.get(id=current_id).handleTurn("admin","test")

        

    if "add" in request.POST:
        Sequence.objects.create(name=request.POST["add"], players=request.POST["players"], settings=request.POST["settings"], data=request.POST["data"])

    for seq in Sequence.objects.all():
        sequence_table += [[seq.id,  seq.name,seq.players, seq.settings, seq.data]]

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
            players = game.parsed_seq_data["players"]
            translated_players = [] 
            for ip in players:
                x = Player.objects.filter(IP=ip)
                if len(x) == 1:
                    x = x[0].name 
                else:
                    x = ip 
                translated_players += [x]
            game_table[-1] += [make_href(game.id, redirect_url+str(game.id)), corresponding_board.getName(), list(corresponding_board.parsed_pending.keys()), str(len(corresponding_board.parsed_history)-1), str(translated_players), make_href("X", "manage?game_del="+str(game.id))]
        except ObjectDoesNotExist:
            pass
    main_config = Config.objects.get(main=True)
    if "modify_config" in request.POST:
        if request.POST["timer_enabled"]=='true':
            if main_config.timer_enabled == False:
                main_config.timer_enabled = True 
                start_timer(timer_stop, timer_working)
        else:
            if main_config.timer_enabled == True:
                main_config.timer_enabled = False 
                timer_stop.set() 
        main_config.save()

    configuration_table['timer_enabled_true'] = 'checked' if main_config.timer_enabled else ''
    configuration_table['timer_enabled_false'] = 'checked' if not main_config.timer_enabled else ''
    view_context = {
        "player_table" : player_table,
        "game_table" : game_table,
        "sequence_table" : sequence_table,
        "config_table" : configuration_table,
        "message" : message
    }

    return render(request, "manage.html", view_context)
    
def admin_observation_view(request):
    if "game_id" in request.GET:
        game_id = int(request.GET["game_id"])
        return render(request, "admin_observation.html", {"game_id" : game_id, "snapshot_range" : len([x for x in Board.objects.get(id=Game.objects.get(id=game_id).board_id).parsed_history if x is not None]) })
    else:
        return HttpResponse("Error, please stipulate game id to observe")

def graph_view(request):
    if "game_id" in request.POST:
        player_board = Board.objects.get(id=Game.objects.get(id=request.POST["game_id"]).board_id)
        score_history = player_board.parsed_score_history
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

def attach0_view(request):
    return render(request, "attach0.html", {})

def end_view(request):
    return redirect("/survey/1")