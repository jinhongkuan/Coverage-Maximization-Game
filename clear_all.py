from game.models import Game, Board, Config, Sequence
from player.models import Player, Agent 
# Bug fix
Game.objects.all().delete()
Board.objects.all().delete()
Player.objects.all().delete()
Agent.objects.all().delete()
Sequence.objects.all().delete()

if len(Config.objects.filter(main=True)) == 0:
    Config.objects.create(main=True)

A = Config.objects.get(main=True)
A.assigner = '{"table":{},"progress":{}}'
A.generate_seq("exp3",[("Map 1.csv",200),("Map 2.csv",200),("Map 3.csv",200),("Map 4.csv",200), ("Tutorial.csv", 150)], "BLLL(instance,2,0.25)") # Last map is placed first 
A.timer_enabled = True 
A.snapshot_interval = 1 
A.save()

