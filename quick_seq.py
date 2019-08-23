import json 
from game.models import Sequence
def generate_sequences(a,b,c,turns):
    def algo(num):
        sel = [a,b,c]
        num = sel[num]
        return (["player"] + ["BLLL(instance, {0}, 0.25)".format(num)]*3)
    begin = [0,0]
    for i in range(9):
        seq_begin = [begin[0] + i//3, (begin[1] + i) % 3]  # start pos, ago 
        seq = []
        for j in range(7):
            if j % 2 == 0:
                if len(seq) > 0:
                    if j == 6:
                        Sequence.objects.create(name=seq[0], players=json.dumps(seq[2]), data=json.dumps(seq[1]))
                        break
                    else:
                        Sequence.objects.create(name=seq[0], players=json.dumps(seq[2]), data=json.dumps(seq[1]),\
                            settings='{"coverage": 1, "sight": 3, "movement": 1, "map_knowledge":"false", "next_seq":"{0}"}'.format("seq0_{0}_{1}".format(i, j // 2)))
                        print("player {0} add {1}".format(i, str(seq)))
                
                seq = ["seq0_{0}_{1}".format(i, j // 2), [],algo(seq_begin[1])]
                if j != 0:
                    seq_begin = [(seq_begin[0] + 1) % 3, (seq_begin[1] + 1) % 3]
            seq[1] += [["map{0}_{1}.csv".format(j+1, seq_begin[0]+1), turns]]