# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Environments/10_EnvSocialDilemma.ipynb.

# %% auto 0
__all__ = ['SocialDilemma']

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 5
import numpy as np
from fastcore.utils import *
from fastcore.test import *

from .Base import ebase

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 6
class SocialDilemma(ebase):
    """
    Symmetric 2-agent 2-action Social Dilemma Matrix Game.
    """ 

    def __init__(self,
                 R:float,  # reward of mutual cooperation
                 T:float,  # temptation of unilateral defection 
                 S:float,  # sucker's payoff of unilateral cooperation
                 P:float): # punsihment of mutual defection
        self.N = 2
        self.M = 2
        self.Z = 1

        self.Re = R
        self.Te = T
        self.Su = S    
        self.Pu = P

        self.state = 0 # inital state
        super().__init__()

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 7
@patch
def TransitionTensor(self:SocialDilemma):
    """Get the Transition Tensor."""
    Tsas = np.ones((self.Z, self.M, self.M, self.Z))             
    return Tsas

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 8
@patch
def RewardTensor(self:SocialDilemma):
    """Get the Reward Tensor R[i,s,a1,...,aN,s']."""

    R = np.zeros((2, self.Z, 2, 2, self.Z))

    R[0, 0, :, :, 0] = [[self.Re , self.Su],
                        [self.Te , self.Pu]]
    R[1, 0, :, :, 0] = [[self.Re , self.Te],
                        [self.Su , self.Pu]]

    return R

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 9
@patch
def actions(self:SocialDilemma):
    """The action sets"""
    return [['c', 'd'] for _ in range(self.N)]

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 10
@patch
def states(self:SocialDilemma):
    """The states set"""
    return ['.'] 

# %% ../../nbs/Environments/10_EnvSocialDilemma.ipynb 11
@patch
def id(self:SocialDilemma):
    """
    Returns id string of environment
    """
    # Default
    id = f"{self.__class__.__name__}_"+\
        f"{self.Te}_{self.Re}_{self.Pu}_{self.Su}"
    return id

