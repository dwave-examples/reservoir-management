# Reservoir Management

Water reservoir levels must be carefully controlled to satisfy consumer demand while maintaining minimum water levels. To satisfy this demand and maintain at least a minimum level of water in the reservoir, pumps can be operated to provide water flow into the reservoir. To operate these pumps there is a cost, and we would like to choose which pumps to use throughout the day in order to minimize cost.

In this demo scenario, we have seven pumps that can be operated on 1-hour intervals throughout a 24-hour day.

## Usage

To run the demo, type:

```bash
    python demo.py
```

The demo outputs `reservoir.mp4`, a video of the reservoir water levels for a problem with seven pumps available, as shown below.

![Example Solution](readme_imgs/reservoir.gif)

## Problem Formulation

### Objective

The general objective for this problem is to minimize cost. Cost is determine by which pumps are used in each time slot. To compute the cost for a given timeslot, we must take into consideration the amount of power required for the pumps in use as well as the cost of power at the given time. Power rates fluctuate at different times of day, meaning that the cost to operate a pump also varies at different times of day.

### Constraints

This problem consists of three groups of constraints.

1. Each pump must be used at least once.

2. Each time slot must have at least one unused pump as a backup.

3. At each time slot, the water level must be within allowable levels.

For the full mathematical formulation of these constraints, please see the paper cited in the References section.

## References

Kowalik, Przemysław, and Magdalena Rzemieniak. "Binary Linear Programming as a Tool of Cost Optimization for a Water Supply Operator." Sustainability 13.6 (2021): 3470.
