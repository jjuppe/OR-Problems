from gurobipy import *
import random

'''
    Data for this example is imported from Cordeau's VRP database at: 
    http://neumann.hec.ca/chairedistributique/data/mdvrp/new/
'''

PATH = "data/p01.txt"

file = open(PATH)
info = file.readline()
info = [int(nr) for nr in info.split()]
assert info[0] == 2
vehicles = info[1]
customers = info[2]
carriers = info[3]

for i in range(carriers):
    Q = file.readline()
Q = int(Q.split()[1])

carriers = 2  # we just regard two carrier case here
customers = 30  # we have to limit number of customers in order to solve

# Making the Sets
K = range(vehicles)  # number of vehicles
Customers = range(customers)  # number of customers
Carriers = range(carriers)  # number of carriers
Arcs = range(customers + carriers)  # total number of arcs
Vehicles = range(vehicles * carriers)  # number of vehicles

# Indexing sets
vehiclesOfCarrier = [set() for _ in Carriers]
customersOfCarrier = [set() for _ in Carriers]
carrierOfCustomer = [set() for _ in Customers]

# Variables
X = list()
Y = list()
Distances = list()
demand = list()
Demand = [list() for _ in Customers]
Depot = [set() for _ in Carriers]

for i in Customers:
    cust = file.readline()
    cust = [int(nr) for nr in cust.split()]
    X.append(cust[1])
    Y.append(cust[2])
    demand.append(cust[4])

for i in Carriers:
    dep = file.readline()
    dep = [int(nr) for nr in dep.split()]
    X.append(dep[1])
    Y.append(dep[2])


def euclidean_distance(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** .5


# Calculate the distances
for i in zip(X, Y):
    foo = [euclidean_distance(i, j) for j in zip(X, Y)]
    Distances.append(foo)

counter = 0
for r in Carriers:
    for ve in range(vehicles):
        vehiclesOfCarrier[r] = vehiclesOfCarrier[r].union({counter * vehicles + ve})
    counter += 1
print(vehiclesOfCarrier)

# Set Depots
for r in Carriers:
    Depot[r] = {customers + r}
    customersOfCarrier[r] = customersOfCarrier[r].union(Depot[r])

# Pre-processing for demand sharing
noShared = 0
for i in Customers:
    ran = random.random()
    if ran <= 0.25:
        customersOfCarrier[0] = customersOfCarrier[0].union({i})
        customersOfCarrier[1] = customersOfCarrier[1].union({i})
        carrierOfCustomer[i] = {0, 1}
        Demand[i].append(demand[i] // 2)
        Demand[i].append(demand[i] - Demand[i][0])
        noShared += 1
    else:
        if len(customersOfCarrier[0]) <= len(customersOfCarrier[1]):
            customersOfCarrier[0] = customersOfCarrier[0].union({i})
            carrierOfCustomer[i] = {0}
            Demand[i] += [demand[i], 0]
        else:
            customersOfCarrier[1] = customersOfCarrier[1].union({i})
            carrierOfCustomer[i] = {1}
            Demand[i] += [0, demand[i]]

Demand += [[0, 0], [0, 0]]

# Build the model
try:
    model = Model("SCC VRP")

    # Add decision variables
    x = model.addVars(Arcs, Arcs, Vehicles, vtype=GRB.BINARY, name="Arc transversed")
    z = model.addVars(Arcs, Carriers, Carriers, Vehicles, vtype=GRB.BINARY, name="Demand allocation")
    u = model.addVars(Arcs, Vehicles, vtype=GRB.INTEGER, lb=0, name="Subtour Elimination")

    # Add Constraints
    model.addConstrs((
        quicksum(z[i, r, s, k] for s in carrierOfCustomer[i]
                 for k in vehiclesOfCarrier[r]) == 1 for i in Customers for r in carrierOfCustomer[i]),
        name="Allocation")
    model.addConstrs(
        (quicksum(x[i, j, k] for j in customersOfCarrier[r]) <= 1 for r in Carriers for i in
         Depot[r] for k in vehiclesOfCarrier[r]), name="Depot leaving constraint")
    model.addConstrs(
        (quicksum(x[j, i, k] for j in customersOfCarrier[r]) - quicksum(x[i, j, k] for j in customersOfCarrier[r]) == 0
         for r in Carriers for k in vehiclesOfCarrier[r] for i in
         customersOfCarrier[r]))
    model.addConstrs((
        quicksum(x[i, j, k] for j in customersOfCarrier[r] if j != i) >=
        z[i, s, r, k] for r in Carriers for s in Carriers for k in vehiclesOfCarrier[r] for i in
        customersOfCarrier[r].difference(Depot[r])), "Every customer has to be visited at least once")
    model.addConstrs(
        (u[i, k] - u[j, k] + (customers + 1) * x[i, j, k] <= (customers + 1) - 1 for i in Customers for j in Arcs for k
         in Vehicles), name="Subtour elimination constraint")
    model.addConstrs(
        (quicksum(Demand[i][s] * z[i, s, r, k] for i in customersOfCarrier[r].difference(Depot[r]) for s in
                  carrierOfCustomer[i]) <= Q for r
         in Carriers for k in vehiclesOfCarrier[r]),
        name="Capacity constraint")
    model.addConstrs(
        (quicksum(z[i, s, r, k - 1] for i in customersOfCarrier[r].difference(Depot[r]) for s in carrierOfCustomer[i]) >= quicksum(
            z[i, s, r, k] for i in customersOfCarrier[r].difference(Depot[r]) for s in carrierOfCustomer[i]) for r in
         Carriers for k in vehiclesOfCarrier[r] if k > 0 and k != vehicles))

    # Objective function
    model.setObjective(
        (quicksum(Distances[i][j] * x[i, j, k] for r in Carriers for k in vehiclesOfCarrier[r] for i in Arcs for j in Arcs)),
        GRB.MINIMIZE)

    model.optimize()

except GurobiError as e:
    print('Error:' + str(e))
