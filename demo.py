# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dwave.system import LeapHybridSampler
from dimod import BinaryQuadraticModel
import numpy as np

import matplotlib
try:
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib.use("agg")
    import matplotlib.pyplot as plt
from matplotlib import animation

def build_bqm(num_pumps, time, power, costs, flow, demand, v_init, v_min, v_max, c3_gamma):
    """Build bqm that models our problem scenario. 
    Args:
        num_pumps (int): Number of pumps available
        time (list): List of time slots
        power (list of floats): power[i] = power required for pump i
        costs (list of floats): costs[i] = unit power cost at time i
        flow (list of floats): flow[i] = flow output for pump i
        demand (list of floats): demand[i] = flow demand at time i
        v_init (float): Initial reservoir water level
        v_min (float): Minimum allowed reservoir water level
        v_max (float): Maximum allowed reservoir water level
        c3_gamma (float): Lagrange multiplier for constraint 3
    
    Returns:
        bqm (BinaryQuadraticModel): QUBO model for the input scenario
        x (list of strings): List of variable names in BQM
    """

    print("\nBuilding binary quadratic model...")

    # Build a variable for each pump
    x = [['P' + str(p) + '_' + str(t) for t in time] for p in range(num_pumps)]

    # Initialize BQM
    bqm = BinaryQuadraticModel('BINARY')

    # Objective
    gamma = 10000 # Lagrange parameter: tune for performance in different scenarios
    for p in range(num_pumps):
        for t in range(len(time)):
            bqm.add_variable(x[p][t], gamma*power[p]*costs[t]/1000)

    # Constraint 1: Every pump runs at least once per day
    for p in range(num_pumps):
        c1 = [(x[p][t], 1) for t in range(len(time))]
        bqm.add_linear_inequality_constraint(c1,
                lb = 1,
                ub = len(time),
                lagrange_multiplier = 1,
                label = 'c1_pump_'+str(p))

    # Constraint 2: At most num_pumps-1 pumps per time slot
    for t in range(len(time)):
        c2 = [(x[p][t], 1) for p in range(num_pumps)]
        bqm.add_linear_inequality_constraint(c2,
                constant = -num_pumps + 1,
                lagrange_multiplier = 1,
                label = 'c2_time_'+str(time[t]))

    # Constraint 3: Water doesn't go below v_min or above v_max
    ## Note: Multiplication by 100 is to clear fractional coefficients in inequality
    for t in range(len(time)):
        c3 = [(x[p][k], int(flow[p]*100)) for p in range(num_pumps) for k in range(t+1)]
        const = v_init - sum(demand[0:t+1])
        bqm.add_linear_inequality_constraint(c3,
                constant = int(const*100),
                lb = v_min * 100,
                ub = v_max * 100,
                lagrange_multiplier = c3_gamma,
                label = 'c3_time_'+str(time[t]))
    
    return bqm, x

def process_sample(sample, x, pumps, time, power, flow, costs, demand, v_init, verbose=True):
    """Process sample returned when submitting BQM to solver. 
    Args:
        sample (SampleSet): Sample to process
        x (list of strings): List of variable names in BQM
        pumps (list of ints): List of pumps available
        time (list): List of time slots
        power (list of floats): power[i] = power required for pump i
        flow (list of floats): flow[i] = flow output for pump i
        costs (list of floats): costs[i] = unit power cost at time i
        demand (list of floats): demand[i] = flow demand at time i
        v_init (float): Initial reservoir water level
        verbose (bool): Trigger to display command-line output
    
    Returns:
        pump_flow_schedule (list of floats):
            pump_flow_schedule[i] = amount of input flow from pumps at time i
        reservoir (list of floats): reservoir[i] = reservoir level at time i        
    """

    print("\nProcessing sampleset returned...")
    
    # Initialize variables
    total_flow = 0
    total_cost = 0
    num_pumps = len(pumps)

    # Print out time slots header
    if verbose:
        timeslots = "\n\t" + "\t".join(str(t) for t in time)
        print(timeslots)

    # Generate printout for each pump's usage
    for p in range(num_pumps):
        printout = str(pumps[p])
        for t in range(len(time)):
            printout += "\t" + str(sample[x[p][t]])
            total_flow += sample[x[p][t]] * flow[p]
            total_cost += sample[x[p][t]] * costs[t] * power[p] / 1000
        if verbose:
            print(printout)

    # Generate printout for general water levels
    printout = "Level:\t"
    reservoir = [v_init]
    pump_flow_schedule = []
    for t in range(len(time)):
        hourly_flow = reservoir[-1]
        for p in range(num_pumps):
            hourly_flow += sample[x[p][t]] * flow[p]
        reservoir.append(hourly_flow-demand[t])
        pump_flow_schedule.append(hourly_flow - reservoir[-2])
        printout += str(int(reservoir[-1])) + "\t"
    if verbose:
        print("\n" + printout)

    # Print out total flow and cost information
    print("\nTotal flow:\t", total_flow)
    print("Total cost:\t", total_cost, "\n")

    return pump_flow_schedule, reservoir

def visualize(sample, x, v_min, v_max, v_init, num_pumps, costs, power, pump_flow_schedule, reservoir, time):
    """Visualize solution as mp4 animation saved to file reservoir.mp4.
    Args:
        sample (SampleSet): Sample to process
        x (list of strings): List of variable names in BQM
        v_min (float): Minimum allowed reservoir water level
        v_max (float): Maximum allowed reservoir water level
        v_init (float): Initial reservoir water level
        num_pumps (int): Number of pumps available
        costs (list of floats): costs[i] = unit power cost at time i
        power (list of floats): power[i] = power required for pump i
        pump_flow_schedule (list of floats):
            pump_flow_schedule[i] = amount of input flow from pumps at time i
        reservoir (list of floats): reservoir[i] = reservoir level at time i
    
    Returns:
       None.                
    """

    print("\nBuilding visualization...")

    # Initialize plot
    fig, ax = plt.subplots()

    # Set up plot parameters (static)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, v_min/2+v_max)
    ax.xaxis.set_visible(False)
    ax.set_yticks([v_min, v_max])
    ax.set_yticklabels(('','Max'))
    ax.set_title("Reservoir Water Level")

    # Plot max/min water capacity lines (static)
    ax.plot(list(range(0, 5)), [v_max]*(5), color='#222222', label="Max capacity", linewidth=1.0)
    ax.plot(list(range(0, 5)), [v_min]*(5), color='#FFA143', label="Min capacity", linewidth=1.5)

    # Plot water as a blue bar graph (dynamic)
    barcollection = plt.bar(0.5, v_init, width=1.0, color='#2a7de1', align='center')

    # Blue line across top of the water (dynamic)
    water_line, = ax.plot([], [], 'b-')
    x_ax_vals = np.linspace(0, 1, 200)

    # Put list of pumps on plot (static)
    pumps_used = []
    for i in range(num_pumps):
        pumps_used.append(plt.figtext(0.03, 0.11+0.035*i, "Pump "+str(i+1), fontdict=None, color='#DDDDDD', fontsize='small'))
    
    # Put timeslot on plot (dynamic)
    time_label = ax.text(0.75, 1600, '')

    # Put cost for timeslot on plot (dynamic)
    cost_label = plt.figtext(0.45, 0.03, '', fontdict=None, color='k')

    def animate(i):

        # Compute minutes/hour for smooth animation over time
        m = i % (60/smoothing_factor)
        t = int( (i-m) / (60/smoothing_factor) )

        # Compute flow/demand per minute for smooth animation over time
        pump_min_flow = m * smoothing_factor * pump_flow_schedule[t] / 60
        demand_min = m * smoothing_factor * demand[t] / 60

        # Adjust water level for the given min/hour
        delta = reservoir[t] + pump_min_flow - demand_min
        y = [delta] * (len(x_ax_vals))
        for i, b in enumerate(barcollection):
            b.set_height(delta)
        water_line.set_data(x_ax_vals, y)

        # Adjust time/cost/pumps used text on plot for the given hour
        time_label.set_text('Time: '+str(time[t]))
        cost = 0
        for p in range(num_pumps):
            if sample[x[p][t]] == 1:
                pumps_used[p].set_color('#008c82')
                cost += sample[x[p][t]] * costs[t] * power[p] / 1000
            else:
                pumps_used[p].set_color('#DDDDDD')

        cost_label.set_text("Hourly Cost: "+str(cost))

        return water_line,

    # Build movie visualization
    smoothing_factor = 4  # Granularity factor for animation
    anim = animation.FuncAnimation(fig, animate, repeat=False, frames=int(24*(60/smoothing_factor)), interval=2, blit=True)
    mywriter = animation.HTMLWriter(fps=30)
    anim.save('reservoir.html',writer=mywriter)

    print("\nAnimation saved as reservoir.html.")

if __name__ == '__main__':

    # Set up scenario
    num_pumps = 7
    pumps = ['P'+str(p+1) for p in range(num_pumps)]
    time = list(range(1, 25))
    power = [15, 37, 33, 33, 22, 33, 22]
    costs = [169]*7 + [283]*6 + [169]*3 + [336]*5 + [169]*3
    flow = [75, 133, 157, 176, 59, 69, 120]
    demand = [44.62, 31.27, 26.22, 27.51, 31.50, 46.18, 69.47, 100.36, 131.85, 
                148.51, 149.89, 142.21, 132.09, 129.29, 124.06, 114.68, 109.33, 
                115.76, 126.95, 131.48, 138.86, 131.91, 111.53, 70.43]
    v_init = 550
    v_min = 523.5
    v_max = 1500
    c3_gamma = 0.00052

    # Build BQM
    bqm, x = build_bqm(num_pumps, time, power, costs, flow, demand, v_init, v_min, v_max, c3_gamma)

    # Run on hybrid sampler
    print("\nRunning hybrid solver...")
    sampler = LeapHybridSampler()
    sampleset = sampler.sample(bqm)
    sample = sampleset.first.sample

    # Process-lowest energy solution
    pump_flow_schedule, reservoir = process_sample(sample, x, pumps, time, power, flow, costs, demand, v_init)

    # Visualize result
    visualize(sample, x, v_min, v_max, v_init, num_pumps, costs, power, pump_flow_schedule, reservoir, time)
