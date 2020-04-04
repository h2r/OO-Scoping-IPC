from abc import ABC
import z3
import pdb

solver = z3.Solver()
synth2varnames = {}
def get_var_names(expr):
	global synth2varnames
	if isinstance(expr, bool):
		return []
	vars = []
	for i in z3.z3util.get_vars(expr):
		i = str(i)
		if i in synth2varnames.keys():
			vars = vars + synth2varnames[i]
		else:
			vars.append(i)
	return vars
def solver_implies_condition(solver, precondition):
	# print("Assertions:")
	# for a in solver.assertions(): print(a)
	solver.push()
	# assert z3.is_expr(precondition), "{}; {}".format(type(precondition),precondition)
	# print(type(precondition))
	solver.add(z3.Not(precondition))
	# print("Assertions (including not precondition):")
	# for a in solver.assertions(): print(a)
	# print("Assertions over")
	result = solver.check()
	solver.pop()
	if result == z3.z3.unsat:
		# print("result: {}".format(result))
		return True
	else:
		if result == z3.z3.unknown:
			print("Unknown guarantee for precondition: {}".format(precondition))
			raise TimeoutError("solver returned unknown")
		# print("result: {}".format(result))
		return False

def check_implication(antecedent, consequent):
	if isinstance(antecedent,AndList):
		antecedent = antecedent.to_z3()
	if isinstance(consequent,AndList):
		consequent = consequent.to_z3()
	global solver
	solver.add(antecedent)
	solver.add(z3.Not(consequent))
	result = solver.check()
	if result == z3.z3.unsat:
		return True
	else:
		if result == z3.z3.unknown:
			print("Unknown implication for precondition: {} => {}".format(antecedent,consequent))
		return False

def get_implies(x,y):
	return ((not x) or y)

def get_iff(x,y):
	both_true = and2(x,y)
	both_false = and2(z3.Not(x),z3.Not(y))
	# pdb.set_trace()
	try:
		return or2(both_true,both_false)
	except Exception as e: print(f"{type(both_true)}, {type(both_false)}")

def or2(*x, solver=None):
	"""
	A wrapper for z3.Or meant to handle ConditionLists and simplifications based on the constant conditions
	"""
	if len(x) == 0: return False
	elif len(x) == 1: return x[0]
	else:
		new_x = []
		for i in x:
			if isinstance(i,ConditionList):
				new_x.append(i.to_z3())
			else:
				new_x.append(i)
		condition = z3.Or(*new_x)
		if solver is not None:
			if solver_implies_condition(solver, condition):
				condition = True
		return condition
		# Note, the below if_else statement exists solely to deal with Or's that only have 1
		# condition in them
		# if(len(new_x) > 1):
		# 	condition = z3.Or(*new_x)
		# else:
		# 	condition = new_x[0]
		#
		# if solver is not None:
		# 	if solver_implies_condition(solver, condition):
		# 		condition = True
		# return condition

def and2(*x):
	"""
	If there are multiple args, creates an AndList. Else, returns the original expression
	"""
	if len(x) == 0: return True
	elif len(x) == 1: return x[0]
	else:
		return AndList(*x)

def not2(x):
	if isinstance(x,ConditionList):
		x = x.to_z3()
	return z3.Not(x)

class ConditionList(ABC):
	def __init__(self, *args, name, z3_combinator):
		#If any of the args are an AndList, flatten them
		self.args = self.flatten(args)
		self.z3_combinator = z3_combinator
		self.name = name
	def flatten(self,a):
		new_list = []
		for x in a:
			if isinstance(x, type(self)):
				new_list.extend(self.flatten(x))
			elif isinstance(x,ConditionList):
				new_list.append(x)
			else:
				#If x a z3 expression, add it to the list
				z3_acceptable = acceptable_z3_condition(x)
				if z3_acceptable:
					new_list.append(x)
				else:
					print(type(x))
					raise TypeError("Don't know how to flatten {}".format(x))
		return new_list
	def to_z3(self):
		arg_list = []
		for c in self.args:
			if acceptable_z3_condition(c):
				arg_list.append(c)
			elif isinstance(c,ConditionList):
				arg_list.append(c.to_z3())
			else:
				raise TypeError("Do not know how to handle {}".format(c))
		return self.z3_combinator(*arg_list)
	def __getitem__(self, item):
		return self.args[item]
	def __iter__(self):
		return self.args.__iter__()
	def __repr__(self):
		return "{}({})".format(self.name,self.args)
	def __str__(self):
		return self.__repr__()

class AndList(ConditionList):
	def __init__(self, *args):
		super().__init__(*args, name="AndList", z3_combinator=z3.And)

class OrList(ConditionList):
	def __init__(self, *args):
		super().__init__(*args, name="OrList", z3_combinator=or2)

def acceptable_z3_condition(x):
	Z3_HANDLED_TYPES = [z3.z3.ExprRef, bool]
	for t in Z3_HANDLED_TYPES:
		if isinstance(x,t):
			return True
	return False

def test_AndList():
	z3_vars = [z3.Bool(str(i)) for i in range(10)]
	a_correct = z3_vars[1:3]
	a = AndList(*z3_vars[1:3])
	b_correct = z3_vars[0:1] + a_correct
	c_correct = z3_vars[4:6]
	d_correct = b_correct + c_correct
	b = AndList(z3_vars[0],a)
	c = AndList(*z3_vars[4:6])
	d = AndList(b,c)
	assert d.args == d_correct, "{}\n{}".format(d.args,d_correct)

def test_ConditionList():
	z3_vars = [z3.Bool(str(i)) for i in range(10)]
	#Test an and of ors
	ors = [OrList(*z3_vars[i:i+2]) for i in range(0,len(z3_vars),2)]
	and0 = AndList(*ors)
	and0_z3 = and0.to_z3()
	print(and0)
	print(and0_z3)

def split_conjunction(x):
	"""Not implemented. Thought I could do something with sexpr, but that might just be equivalent to str(), and I'm not sure how to get references to the composite conditions from it.
	I thought we had some issue with not being able to see pieces of a composite expression, but I rememvber now the issue was decomposing the ast itself, not the string"""
	pass

def split_conjunction_test():
	x = z3.Bool('x')
	y = z3.Bool('y')
	x_and_y = z3.And(x,y)
	print(x_and_y)

if __name__ == "__main__":
	pass
