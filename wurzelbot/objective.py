# example objective: do quests -> farm certain amount of plant
# - mark plants as do not sell if under certain amount
# - set priority of plant / set desired amount of plant -> planter task order

# example objective: buy new garden -> make certain amount of money -> sell most profitable plant, but also sell to wimps
# - objective triggers automatically at certain level
# -
# fall back objective: level up and farm money

# side objective: serve wimps

# how to handel multiple objectives

# importance of objective:
# main objective
# multiple main objectives after each other
# side objective -> if resources are available
# fall back objective -> if no other objectives

# example problem: money farming for new garden -> new plant is more efficient in money farming ->
# it requires to by new plant even though money is reserved for new garden

# possible solution: objective levels -> split up objective in sub-objectives
# sub-objective example: farm money
# sub-objective example: farm certain amount of plant -> sub-objective of farm money (another sub-objective)???
# sub-objective example: buy plant

# further problem: what if money is not enough for required plant

# how should leftover resources be handled, is it even possible? -> other gardens
# main objective: do quests (farm carrots)
# second objective: buy new garden (money can be farmed with other products e.g. waterplants in water garden)
# -> carrots require to be marked as reserved (only certain amount) -> same with money

# split up reservation and working and add priority for reservation so reservation order does not matter
