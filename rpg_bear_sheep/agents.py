'''

Based on the Wolf-Sheep predation example from
https://github.com/projectmesa/mesa/
'''
import random

import numpy as np
from enum import Enum

from mesa import Agent

def bond_with_cub(mother, cub):
    assert(mother.is_female)
    mother.does_care_after_cubs = True
    cub.is_under_parental_care = True

def chase_cub_away(mother, cub):
    assert(mother.is_female)
    mother.does_care_after_cubs = False
    cub.is_under_parental_care = False

def attempt_to_mate(male, female):
    '''
    Returns:
        True, if mating succeeded
        False, otherwise
    '''
    assert(male.model == female.model)
    # Which model we currently use
    current_model = male.model
    if female.does_care_after_cubs:
        return False

    # Females prefer higher leveled mates
    chance_to_reproduce = current_model.bear_reproduce * male.level
    if male.behavior != female.behavior:
        chance_to_reproduce = chance_to_reproduce / 2
    return random.random() < chance_to_reproduce

class Sheep(Agent):
    '''
    A sheep that walks around, reproduces (asexually) and gets eaten.
    The init is the same as the RandomWalker.
    '''

    # Don't model energy for sheep
    #energy = None

    def __init__(self, unique_id, model, energy=None):
        super().__init__(unique_id, model)
     #   super().__init__(pos, model, moore=moore)
        self.model = model
        self.energy = energy
        self.unique_id = self.unique_id

    def step(self):
        '''
        A model step. Just reproduce.
        '''
        if random.random() < self.model.sheep_reproduce:
            sheep = self.model.schedule.get_agents_by_breed(Sheep)
            if len(sheep) < self.model.sheep_limit:
                lamb = Sheep(self.model.generate_id(), self.model)
                self.model.schedule.add(lamb)

    def die(self):
        self.model.schedule.remove(self)


class Bear(Agent):
    '''
    A bear that walks around, reproduces, levels up and eats sheep.

    Fields:
        behavior: aggressive attacks everyone, coward hides. 
        level: current level
        is_female: is a bear female (can bear cubs)
        is_under_parental_care: is a bear under parental care right now
        does_care_after_cubs: 
        parental_care_countdown: how many left 
        accumulated_xp: total XP accumulated
        mother: the bear's mother
    '''

    energy = None

    # 'coward'
    behavior = None

    def __init__(self, unique_id, model, energy=None, behavior=None,
                 father=None, mother=None):
        super().__init__(unique_id, model)
        self.model = model
        self.energy = energy
        self.behavior = behavior
        self.is_under_parental_care = False
        self.does_care_after_cubs = False
        self.mother = mother

        assert(self.behavior in ['coward', 'aggressive'])

        self.level = 1
        self.accumulated_xp = 0
        if father and mother:
            self.lower_cub_limit = \
                (father.lower_cub_limit + mother.lower_cub_limit) // 2
            self.upper_cub_limit = \
                (father.upper_cub_limit + mother.upper_cub_limit) // 2
            self.lower_parental_care_limit = \
                (father.lower_parental_care_limit +
                 mother.lower_parental_care_limit) // 2
            self.upper_parental_care_limit = \
                (father.upper_parental_care_limit +
                 mother.upper_parental_care_limit) // 2
        else:
            self.lower_cub_limit = \
                self.model.initial_values[self.behavior]["lower_cub_limit"]
            self.upper_cub_limit = \
                self.model.initial_values[self.behavior]["upper_cub_limit"] + 1
            self.lower_parental_care_limit = \
                self.model.initial_values[self.behavior]["lower_parental_care_limit"]
            self.upper_parental_care_limit = \
                self.model.initial_values[self.behavior]["upper_parental_care_limit"]\
                + 1

        if random.random() < 0.5:
            self.is_female = True
        else:
            self.is_female = False

    def update(self):
        ''' Update information about the bear, i.e. the level
        '''
        # The level is
        while self.accumulated_xp > np.exp(self.level + 1):
            self.level += 1

    def attack(self, other):
        ''' Attack other bear 
        '''
        # The more level the bear attains, the stronger the bear attacks
        this_bear_attack_strength = self.level
        other_bear_attack_strength = self.level
        # Using exponential distribution, so closer to zero better
        if (self.model.random_generator.exponential(other_bear_attack_strength) <
            self.model.random_generator.exponential(this_bear_attack_strength)):
            other.accumulated_xp += self.model.xp_for_bear + self.accumulated_xp / 2
            self.die()
            other.update()
        else:
            self.accumulated_xp += self.model.xp_for_bear + other.accumulated_xp / 2
            other.die()
            self.update()

    def hunt(self, sheep, assistant=None):
        ''' Calculate the probability of success dependent on the
        hunter's level and the assistant's level
        '''
        level = self.level
        if assistant:
            # Use the average value of level
            level = (self.level + assistant.level // 2)
        chance_to_hunt = self.model.hunt_success_chance * level
        if random.random() < chance_to_hunt:
            # Hunt successfull
            self.accumulated_xp += self.model.xp_for_sheep
            sheep.die()
        self.update()

    def give_birth(self, father):
        cub_cnt = self.model.random_generator.integers(self.lower_cub_limit,
                                                       self.upper_cub_limit)
        # Mother spends half her energy to birth cubs
        self.energy = self.energy / 2
        self.cubs = [ Bear(self.model.generate_id(), self.model, self.energy / cub_cnt,
                           random.choice([father.behavior, self.behavior]),
                           father, self)
                      for cub in range(cub_cnt) ]
        self.parental_care_countdown = \
            self.model.random_generator.integers(self.lower_parental_care_limit,
                                                 self.upper_parental_care_limit)
        for cub in self.cubs:
            self.model.schedule.add(cub)
            bond_with_cub(self, cub)

    def generate_encounters(self):
        ''' Generate encounters for a bear
        '''
        # Only fully mature bears can have enco
        assert(self.is_under_parental_care == False)

        if self.behavior == 'coward' and self.model.season != 'mating':
            # Cowards don't initiate encounters outside of the mating season
            return

        encounter_cnt = np.random.poisson(self.model.encounter_rate)
        for encounter_idx in range(encounter_cnt):
            bears = self.model.schedule.get_agents_by_breed(Bear)
            filtered_bears = [bear for bear in bears if bear != self
                              and bear.is_under_parental_care == False]
            if len(filtered_bears) > 0:
                other_bear = random.choice(filtered_bears)
                if (self.model.season == 'mating' and
                    other_bear.is_female != self.is_female):
                    did_make_cubs = False
                    if self.is_female:
                        did_make_cubs = attempt_to_mate(other_bear, self)
                    else:
                        did_make_cubs = attempt_to_mate(self, other_bear)
                    if did_make_cubs:
                        if self.is_female:
                            self.give_birth(other_bear)
                        else:
                            other_bear.give_birth(self)
                elif self.behavior == 'aggressive':
                    self.attack(other_bear)

    def step(self):
        #self.random_move()
        self.energy -= 1

        # If there are sheep present, eat one
        sheep = self.model.schedule.get_agents_by_breed(Sheep)
        if len(sheep) > 0:
            sheep_to_eat = random.choice(sheep)
            if self.is_under_parental_care:
                self.hunt(sheep_to_eat, self.mother)
            else:
                self.hunt(sheep_to_eat)
        if self.does_care_after_cubs and self.parental_care_countdown <= 0:
            # Chase cubs away
            for cub in self.cubs:
                chase_cub_away(self, cub)
        elif self.does_care_after_cubs:
            self.parental_care_countdown -= 1
        
        if not self.is_under_parental_care:
            self.generate_encounters()

        # Die of hunger
        if self.energy < 0:
            self.die()

    def die(self):
        if self.does_care_after_cubs:
            for cub in self.cubs:
                chase_cub_away(self, cub)
        self.model.schedule.remove(self)

