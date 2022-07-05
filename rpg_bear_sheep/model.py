'''
Bear-Sheep Predation Model modification:

Bears with RPG system preying on sheep.

Based on the Wolf-Sheep predation example from
https://github.com/projectmesa/mesa/
'''

import random

import numpy as np
from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from agents import Sheep, Bear
from schedule import RandomActivationByBreed


class BearSheepPredation(Model):
    '''
    RPG Bear-Sheep Predation Model
    '''

    initial_sheep = 100
    initial_bears = { 'cowards': 50, 'aggressive': 25 }

    sheep_reproduce = 0.04
    bear_reproduce = 0.06

    bear_gain_from_food = 20

    verbose = False  # Print-monitoring

    def __init__(self, initial_sheep=100, initial_cowards=50,
                 initial_aggressive=50,
                 sheep_reproduce=0.08, bear_reproduce=0.05,
                 hunt_success_chance=0.06,
                 bear_gain_from_food=40, mating_season_frequency = 4,
                 coward_litter_size_range = [1, 4],
                 aggressive_litter_size_range = [1, 6],
                 coward_parental_care_range = [8, 16],
                 aggressive_parental_care_range = [1, 8],
                 encounter_rate = 1,
                 xp_for_sheep=100,
                 xp_for_bear=500):
        '''
        Create a new Wolf-Sheep model with the given parameters.
        Args:
            initial_sheep: Number of sheep to start with
            initial_cowards: Number of coward bears to start with
            initial_aggressive: Number of aggressive bears to start with
            sheep_reproduce: Probability of each sheep reproducing each step
            bear_gain_from_food: Energy a bear gains from eating a sheep
            hunt_success_chance: A base chance to succeed in hunting sheep
            mating_season_frequency: Frequency of bears entering the mating season
        '''

        self.generator = np.random.default_rng()
        # Set parameters
        self.initial_sheep = initial_sheep
        self.initial_cowards = initial_cowards
        self.initial_aggressive = initial_aggressive
        self.sheep_reproduce = sheep_reproduce
        self.bear_reproduce = bear_reproduce
        self.sheep_limit = 2000
        self.bear_gain_from_food = bear_gain_from_food
        self.hunt_success_chance = hunt_success_chance
        self.mating_season_frequency = mating_season_frequency
        self.season = 'normal'
        self.xp_for_sheep = xp_for_sheep
        self.xp_for_bear = xp_for_bear
        self.encounter_rate = encounter_rate

        self.random_generator = np.random.default_rng()

        self.initial_values = { 'coward': {'lower_cub_limit': 1,
                                           'upper_cub_limit': 4,
                                           'lower_parental_care_limit': 8,
                                           'upper_parental_care_limit': 16},
                                'aggressive': {'lower_cub_limit': 1,
                                               'upper_cub_limit': 6,
                                               'lower_parental_care_limit': 1,
                                               'upper_parental_care_limit': 8}}
        self.schedule = RandomActivationByBreed(self)
        self.datacollector = DataCollector(
            {"Bears": lambda m: m.schedule.get_breed_count(Bear),
             "Sheep": lambda m: m.schedule.get_breed_count(Sheep),
             "Coward bears": lambda m:
             len(m.schedule.get_agents_by_behavior(Bear, 'coward')),
             "Aggressive bears": lambda m:
             len(m.schedule.get_agents_by_behavior(Bear, 'aggressive')),
             "Average coward level": lambda m:
             np.average([agent.level for agent in m.schedule.get_agents_by_behavior(Bear,
                         'coward')] or [0]),
             "Average aggressive level": lambda m:
             np.average([agent.level for agent in m.schedule.get_agents_by_behavior(Bear,
                         'aggressive')] or [0]),
             "Cubs": lambda m: len([cub for cub in
                                    m.schedule.get_agents_by_breed(Bear) if cub.is_under_parental_care])})

        unique_id = 1
        # Create sheep:
        for i in range(self.initial_sheep):
            sheep = Sheep(unique_id, self)
            #self.grid.place_agent(sheep, (x, y))
            self.schedule.add(sheep)
            unique_id += 1

        # Create bears
        for i in range(self.initial_cowards):
            energy = random.randrange(10 * self.bear_gain_from_food)
            bear = Bear(unique_id, self, energy, 'coward') 
            self.schedule.add(bear)
            unique_id += 1

        for i in range(self.initial_aggressive):
            energy = random.randrange(2 * self.bear_gain_from_food)
            bear = Bear(unique_id, self, energy, 'aggressive') 
            self.schedule.add(bear)
            unique_id += 1

        self.unique_id = unique_id

        self.running = True

    def step(self):
        if self.schedule.time % self.mating_season_frequency == 0:
            self.season = 'mating'
        else:
            self.season = 'normal'
        self.schedule.step()
        self.datacollector.collect(self)
        if self.verbose:
            print([self.schedule.time,
                   self.schedule.get_breed_count(Bear),
                   len([bear for bear in
                        self.schedule.get_agents_by_breed(Bear)
                        if bear.behavior == 'coward']),
                   self.schedule.get_breed_count(Sheep)])

    def run_model(self, step_count=200):

        if self.verbose:
            print('Initial number wolves: ',
                  self.schedule.get_breed_count(Bear))
            print('Initial number sheep: ',
                  self.schedule.get_breed_count(Sheep))
            coward_bears = [ bear for bear in self.schedule.get_agents_by_breed(Bear)
                             if bear.behavior == 'coward' ]
            aggressive_bears = [ bear for bear in self.schedule.get_agents_by_breed(Bear)
                                 if bear.behavior == 'aggressive' ]
            print('Initial coward bears: ',
                  len(coward_bears))
            print('Initial aggressive bears: ',
                  len(aggressive_bears))

        for i in range(step_count):
            self.step()

        if self.verbose:
            print('')
            print('Final number wolves: ',
                  self.schedule.get_breed_count(Bear))
            print('Final number sheep: ',
                  self.schedule.get_breed_count(Sheep))
            coward_bears = [ bear for bear in self.schedule.get_agents_by_breed(Bear)
                             if bear.behavior == 'coward' ]
            aggressive_bears = [ bear for bear in self.schedule.get_agents_by_breed(Bear)
                                 if bear.behavior == 'aggressive' ]
            print('Final coward bears: ',
                  len(coward_bears))
            print('Final aggressive bears: ',
                  len(aggressive_bears))

    def generate_id(self):
        self.unique_id += 1
        return self.unique_id
