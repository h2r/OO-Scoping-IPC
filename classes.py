import copy
from abc import ABC
from collections import OrderedDict
import z3
import itertools
from instance_building_utils import *
from typing import List
from utils import get_possible_values, get_atoms
def get_all_groundings(base_str, names, keys):
	name_lists = [names[k] for k in keys]
	object_name_sequence_list = itertools.product(*name_lists)
	x = object_name_sequence_list
	# x = list([i[0] for i in object_name_sequence_list])
	groundings = [g2n_names(base_str,object_names) for object_names in x]
	return groundings

class Skill():
	def __init__(self, precondition, action, effect: List):
		"""
		:param precondition: Precondition object
		:param action: string
		:param effect: list of affected variables
		"""
		self.precondition = precondition
		self.action = action
		self.effect = effect
		self.implicitly_affected_variables = []
		self.implicit_effects_processed = False
	def get_precondition(self):
		return self.precondition
	def get_action(self):
		return self.action
	def get_targeted_variables(self, grounded = False):
		# Is it safe to check possible values for tgt objects independently? It should be sound, but give up
			#some potential scoping - if we check independently, we get a product space that may be larger than we
			# need, but is certainly not smaller. We care about effects bc they force us to backchain, so adding
			#more vars to the effect set can, at worst, make us include skills we don't need.
		if not grounded:
			return self.effect
		if grounded:
			pvar2groundings = OrderedDict()
			for pvar in self.effect:
				# pvar is something like "passenger-y-curr".
				# We can apply it to a z3 obj to get "passenger-y-curr(p0)"
				pvar_func = pvar.decl()
				# consts will be things like p (generic passenger).
				consts = get_atoms(pvar)
				const2vals = OrderedDict()
				# We'll check the values each const can have. Ex. p can have value p0 or p1
				for o in consts:
					const2vals[o] = get_possible_values(self.get_precondition(), o)
				val_combos = itertools.product(*const2vals.values())
				# pvar2groundings[pvar] = [pvar_func(*grounding_args) for grounding_args in val_combos]
				pvar2groundings[pvar] = []
				for grounding_args in val_combos:
					print(grounding_args[0])
					pvar2groundings[pvar].append(pvar_func(*grounding_args))
			return [i for x in pvar2groundings.values() for i in x]

	def get_affected_variables(self):
		if not self.implicit_effects_processed:
			raise ValueError("Implicit effects of this skill not yet processed")
		return tuple(list(self.effect) + list(self.implicitly_affected_variables))

	def get_explicit_affected_variables(self):
		return tuple(list(self.effect))
	
	def __repr__(self):
		return "({},    {},    {})".format(self.get_precondition(),self.get_action(),self.get_targeted_variables())
	def __str__(self):
		return self.__repr__()
	def __eq__(self, other):
		return self.get_action() == other.get_action() and self.get_precondition() is other.get_precondition() \
			   and self.get_targeted_variables() == other.get_targeted_variables() # and self.get_affected_variables() == other.get_affected_variables()
	def __hash__(self):
		return hash(self.__repr__())

def split_skill_on_obj_vals(skill: Skill, obj, vals):
	# TODO implement
	raise NotImplementedError()
	pass

class Precondition():
	"""
	A Precondition is a first order expression that defines a set of states in a domain
	"""
	def __init__(self, variables, z3_condition):
		self.variables = variables
		self.z3_condition = z3_condition
	def get_variables(self):
		return self.variables
	def get_z3(self, state):
		return self.z3_condition

class UngroundedThing():
	def __init__(self, name, arguments):
		self.name = name
		self.arguments = arguments
	def ground(self, object_names):
		#If there are no args, it is already grounded
		if len(self.arguments) == 0:
			return [self.name]
		else:
			return get_all_groundings(self.name,  object_names, self.arguments)

class DomainAttribute(UngroundedThing):
	def __init__(self, name, type, arguments, constraints = ()):
		super().__init__(name,arguments)
		# self.name = name
		self.type = type
		self.constraints = constraints
		# self.arguments = arguments
		self.object_counts = {}
		self.groundings = []

class DomainAction(UngroundedThing):
	def __init__(self, name, arguments):
		super().__init__(name,arguments)
		# self.name = name
		# self.arguments = arguments


def get_all_effected_vars(skills: List[Skill]):
	pvars = []
	for s in skills:
		pvars.extend(s.get_targeted_variables())
	# cast to string if they are z3 vars. I'd rather deal with z3 vars the whole time, but don't know how.
	pvars = [str(s) for s in pvars]
	return sorted(list(set(pvars)))

if __name__ == "__main__":
	pass