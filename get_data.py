from game.models import Game, Board
from player.models import Player 
import csv 
import json 
from customsurvey.models import TeamEvalSurveyData 
import os 

def generate_csv():
    os.chdir(os.path.dirname(__file__))
    # Different sheet for different team compositions 
    # Game ID, Player Name, Num Players, Map, Avg Score, Score History, Ratings
    col_heads = ["game_id", "player_ip", "num players", "map", "avg score", "optimal score", "history","difficulty", "satisfaction","confusion","collaboration","contribution","interaction","isolation","activity","understanding","intelligence"]
    output = []
    for game in Game.objects.all():
        surveys = TeamEvalSurveyData.objects.filter(game_id=game.id)
        if len(surveys) > 0:
            for survey in surveys:
                x = Player.objects.filter(IP=survey.player_id)
                if len(x) == 1:
                    x = x[0].name 
                else:
                    x = survey.player_id
                board = Board.objects.get(id=game.board_id)
                output += [[game.id, x, len(game.parsed_human_players), board.name, board.getScore(), board.getOptimalScore(), ",".join([str(x) for x in board.parsed_score_history]), survey.difficulty, survey.satisfaction, survey.confusion, survey.collaboration, survey.contribution, survey.interaction, survey.isolation, survey.activity, survey.understanding, survey.intelligence ]]

    with open("data.csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(col_heads)
        for row in output:
            writer.writerow(row)



