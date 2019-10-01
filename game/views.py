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
from customsurvey.forms import TeamEvalForm, QuizForm
from customsurvey.models import TeamEvalSurveyData
def main_view(request):

    return render(request, "main.html")


def game_view(request):

    ip, _ = get_client_ip(request)
    if "decision" in request.POST: 
        if request.POST["decision"] == "disagree":
            return HttpResponseRedirect("/")
    try:
        player = Player.objects.get(IP=ip)
    except ObjectDoesNotExist:
        player = Player.objects.create(IP=ip,active=True)
        print("Created new player with ip " + str(player.IP))

    # Check to see if any survey data is posted 
    form = TeamEvalForm(request.POST)
    if form.is_valid():
        TeamEvalSurveyData.objects.create(difficulty=request.POST["difficulty"],\
            satisfaction=request.POST["satisfaction"],\
            collaboration=request.POST["collaboration"],\
            confusion=request.POST["confusion"],\
            contribution=request.POST["contribution"],\
            interaction=request.POST["interaction"],\
            isolation=request.POST["isolation"],\
            activity=request.POST["activity"],\
            understanding=request.POST["understanding"],\
            intelligence=request.POST["intelligence"],\
            game_id=request.POST["prev_game_id"])
    if "command" in request.POST and request.POST["command"] == "Start Session":
        new_game = Config.objects.get(main=True).generate_game(player.id)
        new_game.add_player(player)

        
        player.save()
            

    elif "command" in request.POST and request.POST["command"] == "Join Session" or "join" in request.GET:
        if "game_id" in request.POST:
            game_id = request.POST["game_id"]
        else:
            game_id = player.redirected_gameid
            player.redirected_gameid = ""
            player.save()
        print(game_id)
        if int(game_id) == -1:
            pass
            # return HttpResponseRedirect("survey/1")
        elif int(game_id) == -2:
            return render(request, "debrief.html")
            # return HttpResponseRedirect("survey/2")
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
    print("Board view called")
    if "admin" in request.POST and request.POST["admin"]:
        player_board = Board.objects.get(id=Game.objects.get(id=request.POST["game_id"]).board_id)
        while (player_board.locked):
            pass 
        hist_request = -1 if "history" not in request.POST else int(request.POST["history"])
        view_context = {
            "cells" : player_board.getDisplayCells("admin", history=hist_request),
            "message" : "" if "show_message" in request.POST and request.POST["show_message"] == "false" else player_board.getMessage("admin", history=hist_request),
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
        
        if "click_data" in request.POST:
            click_data = request.POST["click_data"]
            click_data = eval(click_data)
            redirect = player_board.handleTurn(player, json.dumps(click_data))
            if redirect == "continue":
                redirect = ""
            elif redirect == "break":
                redirect = ""
        else:
            # Retain last state 
            if player_board.parsed_needs_refresh[player.IP] != "True" and player_board.parsed_needs_refresh[player.IP] != "False":
                redirect = player_board.parsed_needs_refresh[player.IP] 
            else:
                redirect = ""
        print("Refresh: ", player_board.parsed_needs_refresh[player.IP])
        print("Redirect: ", redirect)
        view_context = {
            "cells" : player_board.getDisplayCells(player),
            "message" : player_board.getMessage(player),
            "map_name" : player_board.getName(),
            "redirect" : redirect,
            "show_message" : 1 if "hide_message" not in request.POST else 0
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
            return HttpResponseRedirect("manage")
        except Exception as e:
            print(str(e))

    if "game_del" in request.GET:
        id_to_remove = request.GET["game_del"]
        try:
            Game.objects.get(id=id_to_remove).delete() 
            return HttpResponseRedirect("manage")
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
                return render(request, "error.html", {"error_code": msg})

            # Resolve all-bot games
            fin = Board.objects.get(id=new_game.board_id).handleTurn("admin","test")
            current_id = new_game.board_id
            count = 1
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
                    g_id = int(fin.split('=')[1].split('&')[0])
                    
                    if g_id == -1 or g_id == -2:
                        # Temporary hack 
                        count -= 1 
                        if count == 0:
                            break

                        seq_data = {"index": 0, "id": id_to_test, "token_assignment":[], "players": []}
                        new_game, msg = _create_game(seq_data)
                        if new_game is None:
                            return render(request, "error.html", {"error_code": msg})
                        fin = Board.objects.get(id=new_game.board_id).handleTurn("admin","test")
                        current_id = new_game.board_id
                    else:
                        current_id = Game.objects.get(id=g_id).board_id
                    
                    fin = Board.objects.get(id=current_id).handleTurn("admin","test")
            redirect("/manage")

        

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
            translated_players = Sequence.objects.get(id=game.parsed_seq_data["id"]).parsed_players
            try:
                survey_data = TeamEvalSurveyData.objects.get(game_id=game.id).pretty_print()
            except:
                survey_data = ""
            game_table[-1] += [make_href(game.id, redirect_url+str(game.id)), corresponding_board.getName(), list(corresponding_board.parsed_pending.keys()), str(len(corresponding_board.parsed_history)-1), str(translated_players), "{:0.2f}".format(sum(corresponding_board.parsed_score_history)/len(corresponding_board.parsed_score_history)), survey_data , make_href("X", "manage?game_del="+str(game.id))]
        except ObjectDoesNotExist:
            pass
    main_config = Config.objects.get(main=True)
    if "modify_config" in request.POST:
        if request.POST["timer_enabled"]=='true':
            if main_config.timer_enabled == False:
                print('start tiner')
                main_config.timer_enabled = True 
                main_config.save()
                start_timer(timer_stop, timer_working)
        else:
            if main_config.timer_enabled == True:
                main_config.timer_enabled = False
                main_config.save() 
                timer_stop.set() 
        main_config.snapshot_interval = request.POST["snapshot_interval"]
        

    configuration_table['timer_enabled_true'] = 'checked' if main_config.timer_enabled else ''
    configuration_table['timer_enabled_false'] = 'checked' if not main_config.timer_enabled else ''
    configuration_table['snapshot_interval'] = main_config.snapshot_interval
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
        print("avg: ", sum(score_history)/len(score_history))
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

def post_survey_view(request, **kwargs):
    ip, _ = get_client_ip(request)
    try:
        player = Player.objects.get(IP=ip)
    except:
        pass 
    if player.redirected_gameid != "":
        return HttpResponseRedirect("/game?join=1")
    else:
        return render(request, "debrief.html")

def end_round_view(request):
    return render(request, "end_round.html", {"game_id": request.GET["game_id"], "prev_game_id" : request.GET["pg_id"], "max_covered" : request.GET["b"], "cells_covered" : request.GET["a"], "questionnaire_form": TeamEvalForm()})


def attach0_view(request):
    ip, _ = get_client_ip(request)
    review_table = []
    try:
        player = Player.objects.get(IP=ip)
        for game_id in player.all_game_ids.split(","):
            if game_id != "":
                review_table += [game_id]
    except:
        pass 

    
    return render(request, "attach0.html", {"review_table" : review_table})

def end_view(request):
    ip, _ = get_client_ip(request)
    # check whether to redirect to next sequence or survey
    try:
        player = Player.objects.get(IP=ip)
        player_game = Game.objects.get(id=player.game_id)
        seq = Sequence.objects.get(id=player_game.parsed_seq_data["id"])
    except Exception as e:
        print("End view error: " + str(e))
    print(seq.parsed_settings)
    if "next_seq" in seq.parsed_settings:
        if player.redirected_gameid == "end":
            try:
                next_seq = Sequence.objects.get(name=seq.parsed_settings["next_seq"])
            except ObjectDoesNotExist:
                print("End view error: Next seq does not exist")
            # Update AI name
            players = player_game.parsed_seq_data["players"]
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
                if ply.game_id == player.game_id:
                    ply.redirected_gameid = new_game.id 
                    ply.save()

        return redirect("/survey/1")
    else:
        player.redirect_gameid = "debrief"
        player.save()
        return redirect("/survey/2")

def download(request):
    file_path = request.POST["file"]
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read())
            response['content_type'] = "application/download"
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
            return response

def board_gif(request):
    game_id = request.GET["game_id"]
    index = []
    history = Board.objects.get(id=Game.objects.get(id=game_id).board_id).parsed_history
    for i,c in enumerate(history):
        if c is not None and i != len(history)-1:
            index += [len(index)+1]
    return render(request, "board_gif.html", {"game_id": game_id, "board_history": index})

def pretest_view(request):
    form = QuizForm(request.POST)
    message = ""
    if form.is_valid():
        resp = [request.POST['movement'], request.POST['traversible'], request.POST['objective'], request.POST['overlap']]
        ans = ['3','2','2','2','1']
        print(resp)
        if all([ans[i]==resp[i] for i in range(len(resp))]):
            request.POST = request.POST.copy()
            request.POST['command'] = 'Start Session'
            return game_view(request)
        else:
            message = "* One or more of the selected answers are incorrect<br>"
    return render(request, 'pretest.html', {'quiz_form' : QuizForm(), 'message' : message})