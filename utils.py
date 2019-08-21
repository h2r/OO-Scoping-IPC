import z3
def get_var_names(expr):
	vars = [str(i) for i in z3.z3util.get_vars(expr)]
	return vars

def split_and(expr):
	if expr.decl() == z3.And:
		pass

if __name__ == "__main__":
	a = z3.Bool('a')
	b = z3.Bool('b')
	a_and_b = z3.And(a,b)
	d= a_and_b.decl()
	print(d)
	print(a_and_b.sort())
	x = z3.z3core.Z3_get_app_num_args(a_and_b, a_and_b)
	print(x)
	# print(d.params())
	# print(d.name())
	# assert d is z3.And