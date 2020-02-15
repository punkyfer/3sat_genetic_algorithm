import numpy as np
import random
import sys

# TODO TEST: Change replacement rate with individual age and kill individuals older than x
# ADD UNIT TESTS

############# CONSTANTS #############
zero = 0.000001
infinite = 2**31

############# FUNCTIONS #############

def read_problem(filepath):
	with open(filepath, 'r') as fp:
		all_clauses = ""
		for line in fp.readlines():
			if line[0]=='c': 
				continue
			if line[0]=='p':
				num_vars = int(line.split()[2])
				num_clauses = int(line.split()[3])
			else:
				all_clauses += " "+line.replace('\n','')

		clauses = [[] for x in range(num_clauses)]
		clause = 0
		for num in all_clauses.split():
			if num=='0': 
				clause+=1
			elif num=='%': 
				break
			else:
				clauses[clause].append(int(num))

	return num_vars, clauses

############# CNF SIMPLIFICATION #############

def trivial_case(clauses):
	num_pos = 0
	num_neg = 0
	for clause in clauses:
		for num in clause:
			if num > 0: num_pos += 1
			else: num_neg += 1
	if num_neg == 0:
		return (True, 1)
	if num_pos == 0:
		return (True, 0)
	return (False, -1)

def remove_unit_vars(clauses, set_vars):
	# Find clauses with a single variable and set it
	unit_clauses = 0
	new_clauses = clauses[:]
	for i, clause in enumerate(clauses):
		if len(clause)==1:
			# Clause found
			unit_clauses += 1
			new_clauses = clauses[:i]+clauses[i+1:]
			# Set Variable
			if clause[0]>=0: set_vars[clause[0]-1] = 1
			else: set_vars[abs(clause[0])-1] = zero
			for j, new_clause in enumerate(new_clauses):
				if 0-clause[0] in new_clauses:
					# Remove negative value from clauses since its False
					new_clauses[j].remove(0-clause[0])
				#elif clause[0] in new_clauses:
					# Set value in clause to True
				#	new_clauses[j][new_clauses[j].index(clause[0])] = True
			break
	if unit_clauses==0:
		return new_clauses, set_vars
	else:
		return remove_unit_vars(new_clauses, set_vars)

def remove_pure_vars(clauses, set_vars):
	# Remove pure variables, (all appearances are negated = False, all appearances positive = True)
	new_clauses = clauses[:]
	for i in range(len(set_vars)):
		pos_var, neg_var = 0, 0
		for clause in clauses:
			if i+1 in clause: pos_var += 1
			elif -(i+1) in clause: neg_var += 1
		if pos_var > 0 and neg_var == 0:
			set_vars[i] = 1
		elif neg_var > 0 and pos_var == 0:
			set_vars[i] = 0
		elif neg_var == 0 and pos_var == 0:
			# Any value will do, since the variable doesn't appear in the formulas
			set_vars[i] = 0
		if set_vars[i] != infinite:
			for i, clause in enumerate(new_clauses):
				if i+1 in clause: new_clauses[i].remove(i+1)
				if -(i+1) in clause: new_clauses[i].remove(-(i+1))
	return new_clauses, set_vars

############# GENETIC ALGORITHM #############

def initial_population(num_vars, set_vars, pop_size=1000, ptype="bits"):
	population = []
	for p in range(pop_size):
		if ptype=='bits': rpop = np.random.randint(2, size=num_vars)
		elif ptype=='floats': rpop = np.array([random.random() for i in range(num_vars)])
		for j, var in enumerate(set_vars):
			if var != infinite:
				rpop[j] = var
		for i,x in enumerate(rpop):
			if x == 0: rpop[i] = zero
		population.append(rpop)
	return population

############# FITNESS FUNCTIONS #############

def maxsat_fitness(var_arr):
	# Since CNF formulas are of the shape (x1 OR x2 OR x3) AND (x3 OR -x2 OR -x1)
	# As soon as we find any True value inside a clause that clause is satisfied
	t_clauses = 0
	for clause in clauses:
		for num in clause:
			if num >= 0:
				if var_arr[num-1]==1:
					t_clauses += 1
					break
			elif num <= 0:
				if var_arr[abs(num)-1]==zero:
					t_clauses += 1
					break
	return t_clauses

def float_fitness(var_arr):
	t_res = 1
	for clause in clauses:
		tmp_r = 0
		for num in clause:
			if num<0:
				if var_arr[abs(num)-1] == zero:
					tmp_r += 1
				else:
					tmp_r += zero
			else:
				tmp_r += var_arr[num-1]
		#if tmp_r >= 1: tmp_r = 1
		t_res *= tmp_r
	return t_res

def maxsat_solution_found(fitness):
	if fitness >= len(clauses): return True
	return False

############# SELECTION FUNCTIONS #############

# Modify roulette so it only returns one parent
def roulette_selection(population, replacement_rate):
	# TODO: Change behaviour so that it doesn't remove parents from the selection pool
	# maybe do in separate function and test both
	tmp_pop = population[:]
	parents = []
	for i in range(int(len(population)*replacement_rate)):
		if len(tmp_pop)==0: tmp_pop = population
		total_fitness = sum([y for x,y in tmp_pop])
		probabilities = [y/total_fitness for x,y in tmp_pop]
		rnum = random.random()
		sprob = 0
		for i, prob in enumerate(probabilities):
			if rnum >= sprob and rnum <= sprob+prob:
				parents.append(tmp_pop[i][0])
				tmp_pop.pop(i)
				break
			sprob += prob
	return parents 

############# CROSSOVER FUNCTIONS #############

def single_point_crossover(parent1, parent2):
	cut_point = np.random.randint(len(parent1))
	children = [
		np.concatenate((parent1[:cut_point],parent2[cut_point:])),
		np.concatenate((parent2[:cut_point],parent1[cut_point:]))
		]
	return children

def two_point_crossover(parent1, parent2):
	cut_point_1 = np.random.randint(len(parent1)-1)
	cut_point_2 = np.random.randint(cut_point_1+1, len(parent1))
	children = [
		np.concatenate((parent1[:cut_point_1],parent2[cut_point_1:cut_point_2],parent1[cut_point_2:])),
		np.concatenate((parent2[:cut_point_1],parent1[cut_point_1:cut_point_2],parent2[cut_point_2:]))
		]
	return children

def sliding_window_crossover(parent1, parent2, crossover_window_len):
	window_len = int(crossover_window_len*len(parent1))
	max_fitness, max_i = (0,0), (0,0)
	bad_children = [[],[]]
	for i in range(len(parent1)-window_len):
		bad_children[0].append(np.concatenate((parent1[:i],parent2[i:i+window_len],parent1[i+window_len:])))
		bad_children[1].append(np.concatenate((parent2[:i],parent1[i:i+window_len],parent2[i+window_len:])))
		for t in range(2):
			fitness = maxsat_fitness(bad_children[t][i])
			if fitness >=max_fitness[0]:
				max_fitness[t] = fitness
				max_i[t] = i
	return [bad_children[0][max_i[0]], bad_children[1][max_i[1]]]

def random_map_crossover(parent1, parent2):
	rand_map = np.random.randint(2, size=len(parent1))
	child_1 = parent1[:]
	child_2 = parent2[:]
	for i, elem in enumerate(rand_map):
		if elem == 0:
			child_1[i] = parent2[i]
			child_2[i] = parent1[i]
	return [child_1, child_2]

def uniform_crossover(parent1, parent2):
	# Uses alternating bits, maybe change to a normal distribution
	child_1 = parent1[:]
	child_2 = parent2[:]
	for i in range(len(parent1)):
		if i%2==0:
			child_1[i] = parent2[i]
			child_2[i] = parent1[i]
	return [child_1, child_2]

############# MUTATION FUNCTIONS #############

def single_bit_flip(population, mutation_rate):
	new_pop = []
	for i, pop in enumerate(population):
		indiv = pop
		rmut = random.random()
		if rmut <= mutation_rate:
			ind = np.random.randint(len(indiv))
			if indiv[ind] == 1: indiv[ind] = zero
			else: indiv[ind] = 1
		new_pop.append(indiv)
	return new_pop

def multiple_bit_flip(population, mutation_rate):
	new_pop = []
	for i, pop in enumerate(population):
		indiv = pop
		rmut = random.random()
		if rmut <= mutation_rate:
			num_bits = np.random.randint(len(indiv))
			for x in range(num_bits):
				ind = np.random.randint(len(indiv))
				if indiv[ind] == 1: indiv[ind] = zero
				else: indiv[ind] = 1
		new_pop.append(indiv)
	return new_pop

def single_bit_greedy(population):
	new_pop = []
	for i, pop in enumerate(population):
		ind_fitness = maxsat_fitness(pop)
		for j in range(len(indiv)):
			t_indiv = pop
			if pop[j]==1: t_indiv[j]=zero
			elif pop[j]==zero: t_indiv[j]=1
			if maxsat_fitness(t_indiv)>ind_fitness:
				break
		new_pop.append(t_indiv)
	return new_pop

def single_bit_max_greedy(population):
	new_pop = []
	for i, pop in enumerate(population):
		ind_fitness = maxsat_fitness(pop)
		max_ind, max_fit = 0, 0
		for j in range(len(indiv)):
			t_indiv = pop
			if pop[j]==1: t_indiv[j]=zero
			elif pop[j]==zero: t_indiv[j]=1
			tfit = maxsat_fitness(t_indiv)
			if tfit>ind_fitness and tfit>=max_fit:
				max_ind = t_indiv
				max_fit = tfit
		new_pop.append(max_ind)
	return new_pop

def multi_bit_greedy(population):
	new_pop = []
	for i, pop in enumerate(population):
		ind_fitness = maxsat_fitness(pop)
		indiv = pop
		for j in range(len(indiv)):
			new_bit = 1
			if indiv[j]==1: new_bit=zero
			t_indiv = np.concatenate((indiv[:j],[new_bit],indiv[j+1:]))
			t_fitness = maxsat_fitness(t_indiv)
			if t_fitness > ind_fitness:
				ind_fitness = t_fitness
				indiv = t_indiv
		new_pop.append(indiv)
	return new_pop	

def flip_ga(population):
	new_pop = []
	for i, pop in enumerate(population):
		indiv = pop
		ind_fitness = maxsat_fitness(indiv)
		prev_fitness = ind_fitness-1
		while(prev_fitness<ind_fitness):
			prev_fitness = ind_fitness
			for j in range(len(indiv)):
				new_bit = 1
				if indiv[j]==1: new_bit=zero
				t_indiv = np.concatenate((indiv[:j],[new_bit],indiv[j+1:]))
				t_fitness = maxsat_fitness(t_indiv)
				if t_fitness > ind_fitness:
					ind_fitness = t_fitness
					indiv = t_indiv
		new_pop.append(indiv)
	return new_pop	


############# PARAMETERS #############
max_iters = 1000
pop_size = 500
replacement_rate = 0.5
mutation_rate = 0.1
crossover_window_len = 0.4


############# AUXILIARY VARIABLES #############
cur_iters = 0
sol_found = False


############# PROGRAM #############

num_vars, clauses = read_problem('./data/uf20-91/uf20-02.cnf')
#num_vars, clauses = read_problem('./data/simple_3sat_problem_u.cnf')
set_vars = [infinite]*num_vars

print (clauses)
print(len(clauses))

# CNF Simplification
sol_found, value = trivial_case(clauses)
if sol_found:
	print ("Solution found!")
	print ("Assign {} to all variables".format(value))
	sys.exit()

clauses, set_vars = remove_pure_vars(clauses)
clauses, set_vars = remove_unit_vars(clauses)

# Genetic Algorithm Execution
population = initial_population(num_vars, pop_size)


solution = []
while(not sol_found and cur_iters<max_iters):
	pop_fitness = []
	max_fitness = 0
	for pop in population:
		fitness = maxsat_fitness(pop)
		if fitness >= max_fitness: max_fitness=fitness
		pop_fitness.append([pop, fitness])
		#print (pop, fitness)
		if maxsat_solution_found(fitness): 
			print(fitness, " Solution found! > ", pop)
			sol_found=True
			solution = pop
			break

	#print(len(pop_fitness))
	# CHANGE when roulette_selection changes
	parents = roulette_selection(pop_fitness, replacement_rate)
	#print(len(pop_fitness))
	children = [] 
	while(len(parents)>=2):
		p1 = np.random.randint(0, len(parents))
		parent_1 = parents.pop(p1)
		p2 = np.random.randint(0, len(parents))
		parent_2 = parents.pop(p2)
		children += single_point_crossover(parent_1, parent_2)
		
	sorted_pop = sorted(pop_fitness, key=lambda x: x[1], reverse=True)

	#print(len(sorted_pop))

	top_pop = [x for x,y in sorted_pop[:int(replacement_rate*len(sorted_pop))]]
	new_pop = children + top_pop

	#print (len(children), len(top_pop), len(new_pop))
	#print (new_pop[:5])

	#print(new_pop[:5])

	population = single_bit_flip(new_pop, mutation_rate)

	#print(population[:5])

	if cur_iters % 1 == 0:
		print ("Generation {}, Population {}, Max Fitness {}".format(cur_iters, len(population), max_fitness))
	cur_iters += 1

if len(solution)>0:
	print("{} - Raw Solution: {}".format(float_fitness(solution), solution))
	psol = []
	for num in solution:
		#if max(solution) - num > num - min(solution):
		#	psol.append(0)
		#else:
		#	psol.append(1)
		if num>0.5: psol.append(1)
		else: psol.append(0)
	print("{} - Solution: {}".format(maxsat_fitness(psol), psol))