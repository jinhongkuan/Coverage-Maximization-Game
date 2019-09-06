from game.models import Game, Board
import numpy as np 
data = {}
for game in Game.objects.all():
    # if game.id >=13619 and game.id <=13999 :  # 3
    # if game.id >= 14001 and game.id <= 14360: # 2
    # if game.id >=14633 and game.id <=14992 :  # 6
    # if game.id >= 14993 and game.id <= 15333: # 10
    # if game.id >= 15334:          # 6
    # if game.id >= 15438 and game.id <= 15725:
    # if game.id >= 15335 and game.id <= 15437: # 18
    if game.id >= 15742:
        try:
            corr_board = Board.objects.get(id=game.board_id)
            mapName = corr_board.getName()
            if str(game.parsed_seq_data["id"]) not in data:
                data[str(game.parsed_seq_data["id"])] = {}
            if mapName not in data[str(game.parsed_seq_data["id"])]:
                data[str(game.parsed_seq_data["id"])][mapName] = [] 
          
            # data[str(game.parsed_seq_data["id"])][mapName] += [sum(corr_board.parsed_score_history[:60])/60]
            data[str(game.parsed_seq_data["id"])][mapName] += [corr_board.parsed_score_history[59]]
        except:
            pass

print()
for key in data:
    for key2 in data[key]:
        analysis = ['{:0.2f}'.format(np.mean(data[key][key2])), '{0}'.format(len(data[key][key2]))]
        data[key][key2] = analysis
        print(key2, ": ", analysis)

for key in data:
    arr = [[]]
    for key2 in data[key]:
        
        arr[-1] += data[key][key2][0]
        if len(arr[-1]) % 3 == 0:
            arr += [[]]
    print(arr)
    np.savetxt(key+".csv", np.asarray(arr[:-1],dtype=np.float64))

