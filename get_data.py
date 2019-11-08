from game.models import Game, Board
from player.models import Player 
import csv 
import json 
from customsurvey.models import TeamEvalSurveyData 

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
            parsed_score_history = json.loads(board.score_history)
            output += [[game.id, x, len(game.parsed_human_players), board.name, sum(parsed_score_history)/len(parsed_score_history),board.optimal_score, ",".join(parsed_score_history), survey.difficulty, survey.satisfaction, survey.confusion, survey.collaboration, survey.contribution, survey.interaction, survey.isolation, survey.activity, survey.understanding, survey.intelligence ]]

with open("data.csv", "w", newline="") as f:
    writer = csv.writer(f, sep=";")
    writer.writerow(col_heads)
    for row in output:
        writer.writerow(row)



