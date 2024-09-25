import math

def calculate_indeps(fpr, tpr, g, n):
    fnr = 1-tpr
    tnr = 1-fpr


    alpha = g*fnr+(1-g)*tnr

    cn = (tpr)*g*(1-alpha**n)/(1-alpha)

    gn = cn + (alpha**n)*g

    cinf = (tpr)*g/(1-alpha)

    print(cn)

    print(gn)

    print(cinf)

    cutoff = 0.01

    n_end = math.log(cutoff)/math.log(alpha)

    print(f"n at which less than {cutoff} diff: {n_end}")

n=15

print("g24")
#g24
fpr = 0.299
tpr = 0.769
g = 0.054
calculate_indeps(fpr, tpr,g, n)
print("-with sound")
calculate_indeps(0, 1,g, n)

print("gc")
#GC
#TODO where did these numbers come from???:
#fpr = 0.667
#tpr = 0.817
tpr = .1667
fpr = .1463
#g = 0.11
g = .16
calculate_indeps(fpr, tpr, g, n)
print("-with sound")
calculate_indeps(0, 1,g, n)

print("bw")
#BW
fpr = 0.378
tpr = 0.9636
g = 0.4
calculate_indeps(fpr, tpr,g, n)
print("-with sound")
calculate_indeps(0, 1,g, n)
