from game.models import Game, Board
import numpy as np 
data = {}
for game in Game.objects.all():
    # if game.id >=13619 and game.id <=13999 :  # 3
    # if game.id >=14633 and game.id <=14992 :  # 2
    # if game.id >= 14993 and game.id <= 15333: # 10
    # if game.id >= 15334:
        try:
            corr_board = Board.objects.get(id=game.board_id)
            mapName = corr_board.getName()
            if str(game.parsed_seq_data["id"]) not in data:
                data[str(game.parsed_seq_data["id"])] = {}
            if mapName not in data[str(game.parsed_seq_data["id"])]:
                data[str(game.parsed_seq_data["id"])][mapName] = [] 
            ind = corr_board.parsed_score_history.index(max(corr_board.parsed_score_history))
            if ind > 0:
                data[str(game.parsed_seq_data["id"])][mapName] += [ind]
            # data[str(game.parsed_seq_data["id"])][mapName] += [sum(corr_board.parsed_score_history[:60])/60]
            # data[str(game.parsed_seq_data["id"])][mapName] += [corr_board.parsed_score_history[-1]]
        except:
            pass


for key in data:
    for key2 in data[key]:
        # analysis = ['{:0.2f}'.format(np.mean(data[key][key2])), '{:0.2f}'.format(np.std(data[key][key2]))]
        analysis = ['{:0.2f}'.format(np.mean(data[key][key2])), '{0}'.format(len(data[key][key2]))]
        data[key][key2] = analysis
        print(key2, ": ", analysis)


