from game.models import Game, Board
import numpy as np 
data = {}
for game in Game.objects.all():
    if game.id >= 2158 and game.id <= 5000:
        corr_board = Board.objects.get(id=game.board_id)
        mapName = corr_board.getName()+"_" + str(game.parsed_seq_data["id"])
        if mapName not in data:
            data[mapName] = [] 
        
        # data[mapName] += [sum(corr_board.parsed_score_history)/len(corr_board.parsed_score_history)]
        data[mapName] += [corr_board.parsed_score_history[-1]]

for key in data:
    analysis = [np.mean(data[key]), np.std(data[key]) * 1.96 / np.sqrt(len(data[key]))]
    data[key] = analysis

print(data)