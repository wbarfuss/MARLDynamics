# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Agents/99_ABase.ipynb.

# %% auto 0
__all__ = ['abase']

# %% ../../nbs/Agents/99_ABase.ipynb 4
import numpy as np
import itertools as it
from functools import partial

import jax
from jax import jit
import jax.numpy as jnp

from typing import Iterable
from fastcore.utils import *

from ..Utils.Helpers import *

# %% ../../nbs/Agents/99_ABase.ipynb 6
class abase(object):
    """
    Base class for deterministic strategy-average independent (multi-agent)
    temporal-difference reinforcement learning.
    """
    
    def __init__(self, 
                 TransitionTensor: np.ndarray, # transition model of the environment
                 RewardTensor: np.ndarray,  # reward model of the environment
                 DiscountFactors: Iterable[float],  # the agents' discount factors
                 use_prefactor=False,  # use the 1-DiscountFactor prefactor
                 opteinsum=True):  # optimize einsum functions
                
        R = jnp.array(RewardTensor)
        T = jnp.array(TransitionTensor)
    
        # number of agents
        N = R.shape[0]  
        assert len(T.shape[1:-1]) == N, "Inconsistent number of agents"
        assert len(R.shape[2:-1]) == N, "Inconsistent number of agents"
        
        # number of actions for each agent        
        M = T.shape[1] 
        assert np.allclose(T.shape[1:-1], M), 'Inconsisten number of actions'
        assert np.allclose(R.shape[2:-1], M), 'Inconsisten number of actions'
        
        # number of states
        Z = T.shape[0] 
        assert T.shape[-1] == Z, 'Inconsisten number of states'
        assert R.shape[-1] == Z, 'Inconsisten number of states'
        assert R.shape[1] == Z, 'Inconsisten number of states'
        
        self.R, self.T, self.N, self.M, self.Z, self.Q = R, T, N, M, Z, Z
        
        # discount factors
        self.gamma = make_variable_vector(DiscountFactors, N)

        # use (1-DiscountFactor) prefactor to have values on scale of rewards
        self.pre = 1 - self.gamma if use_prefactor else jnp.ones(N)        
        self.use_prefactor = use_prefactor

        # 'load' the other agents actions summation tensor for speed
        self.Omega = self._OtherAgentsActionsSummationTensor()
        self.has_last_statdist = False
        self._last_statedist = jnp.ones(Z) / Z
        
        # use optimized einsum method
        self.opti = opteinsum  

    @partial(jit, static_argnums=0)    
    def Tss(self, 
            Xisa:jnp.ndarray  # Joint strategy
           ) -> jnp.ndarray: # Average transition matrix
        """Compute average transition model `Tss`, given joint strategy `Xisa`"""
        # i = 0  # agent i (not needed)
        s = 1  # state s
        sprim = 2  # next state s'
        b2d = list(range(3, 3+self.N))  # all actions

        X4einsum = list(it.chain(*zip(Xisa, [[s, b2d[a]] for a in range(self.N)])))
        args = X4einsum + [self.T, [s]+b2d+[sprim], [s, sprim]]
        return jnp.einsum(*args, optimize=self.opti)
    
    @partial(jit, static_argnums=0)    
    def Tisas(self,
              Xisa:jnp.ndarray  # Joint strategy
             ) -> jnp.ndarray:  #  Average transition Tisas
        """Compute average transition model `Tisas`, given joint strategy `Xisa`"""      
        i = 0  # agent i
        a = 1  # its action a
        s = 2  # the current state
        s_ = 3  # the next state
        j2k = list(range(4, 4+self.N-1))  # other agents
        b2d = list(range(4+self.N-1, 4+self.N-1 + self.N))  # all actions
        e2f = list(range(3+2*self.N, 3+2*self.N + self.N-1))  # all other acts

        sumsis = [[j2k[l], s, e2f[l]] for l in range(self.N-1)]  # sum inds
        otherX = list(it.chain(*zip((self.N-1)*[Xisa], sumsis)))

        args = [self.Omega, [i]+j2k+[a]+b2d+e2f] + otherX\
            + [self.T, [s]+b2d+[s_], [i, s, a, s_]]
        return jnp.einsum(*args, optimize=self.opti)

    @partial(jit, static_argnums=0)    
    def Ris(self,
            Xisa:jnp.ndarray, # Joint strategy
            Risa:jnp.ndarray=None # Optional reward for speed-up
           ) -> jnp.ndarray: # Average reward
        """Compute average reward `Ris`, given joint strategy `Xisa`""" 
        if Risa is None:  # for speed up
            # Variables      
            i = 0; s = 1; sprim = 2; b2d = list(range(3, 3+self.N))
        
            X4einsum = list(it.chain(*zip(Xisa,
                                    [[s, b2d[a]] for a in range(self.N)])))

            args = X4einsum + [self.T, [s]+b2d+[sprim],
                               self.R, [i, s]+b2d+[sprim], [i, s]]
            return jnp.einsum(*args, optimize=self.opti)
        
        else:  # Compute Ris from Risa 
            i=0; s=1; a=2
            args = [Xisa, [i, s, a], Risa, [i, s, a], [i, s]]
            return jnp.einsum(*args, optimize=self.opti)
       
    @partial(jit, static_argnums=0)    
    def Risa(self,
             Xisa:jnp.ndarray # Joint strategy
            ) -> jnp.ndarray:  # Average reward
        """Compute average reward `Risa`, given joint strategy `Xisa`"""
        i = 0; a = 1; s = 2; s_ = 3  # Variables
        j2k = list(range(4, 4+self.N-1))  # other agents
        b2d = list(range(4+self.N-1, 4+self.N-1 + self.N))  # all actions
        e2f = list(range(3+2*self.N, 3+2*self.N + self.N-1))  # all other acts
 
        sumsis = [[j2k[l], s, e2f[l]] for l in range(self.N-1)]  # sum inds
        otherX = list(it.chain(*zip((self.N-1)*[Xisa], sumsis)))

        args = [self.Omega, [i]+j2k+[a]+b2d+e2f] + otherX\
            + [self.T, [s]+b2d+[s_], self.R, [i, s]+b2d+[s_],
               [i, s, a]]
        return jnp.einsum(*args, optimize=self.opti)       
       
    @partial(jit, static_argnums=0)            
    def Vis(self,
            Xisa:jnp.ndarray, # Joint strategy
            Ris:jnp.ndarray=None, # Optional reward for speed-up
            Tss:jnp.ndarray=None, # Optional transition for speed-up
            Risa:jnp.ndarray=None  # Optional reward for speed-up
           ) -> jnp.ndarray:  # Average state values
        """Compute average state values `Vis`, given joint strategy `Xisa`"""
        # For speed up
        Ris = self.Ris(Xisa, Risa=Risa) if Ris is None else Ris
        Tss = self.Tss(Xisa) if Tss is None else Tss
        
        i = 0  # agent i
        s = 1  # state s
        sp = 2  # next state s'

        n = np.newaxis
        Miss = np.eye(self.Z)[n,:,:] - self.gamma[:, n, n] * Tss[n,:,:]
        
        invMiss = jnp.linalg.inv(Miss)
               
        return self.pre[:,n] * jnp.einsum(invMiss, [i, s, sp], Ris, [i, sp],
                                          [i, s], optimize=self.opti)

    @partial(jit, static_argnums=0)        
    def Qisa(self,
             Xisa:jnp.ndarray, # Joint strategy
             Risa:jnp.ndarray=None, #  Optional reward for speed-up
             Vis:jnp.ndarray=None, # Optional values for speed-up
             Tisas:jnp.ndarray=None, # Optional transition for speed-up
            ) -> jnp.ndarray:  # Average state-action values
        """Compute average state-action values Qisa, given joint strategy `Xisa`"""
        # For speed up
        Risa = self.Risa(Xisa) if Risa is None else Risa
        Vis = self.Vis(Xisa, Risa=Risa) if Vis is None else Vis
        Tisas = self.Tisas(Xisa) if Tisas is None else Tisas

        nextQisa = jnp.einsum(Tisas, [0,1,2,3], Vis, [0,3], [0,1,2],
                              optimize=self.opti)

        n = np.newaxis
        return self.pre[:,n,n] * Risa + self.gamma[:,n,n]*nextQisa
    
    
    # === Helper ===
    @partial(jit, static_argnums=0)  
    def _jaxPs(self,
               Xisa,  # Joint strategy
               pS0):  # Last stationary state distribution 
        """
        Compute stationary distribution `Ps`, given joint strategy `Xisa`
        using JAX.
        """
        Tss = self.Tss(Xisa)
        _pS = compute_stationarydistribution(Tss)
        nrS = jnp.where(_pS.mean(0)!=-10, 1, 0).sum()

        @jit
        def single_dist(pS):
            return jnp.max(jnp.where(_pS.mean(0)!=-10,
                                     jnp.arange(_pS.shape[0]), -1))
        @jit
        def multi_dist(pS):
            ix = jnp.argmin(jnp.linalg.norm(_pS.T - pS0, axis=-1))
            return ix
            
        ix = jax.lax.cond(nrS == 1, single_dist, multi_dist, _pS)

        pS = _pS[:, ix]
        return pS
        

# %% ../../nbs/Agents/99_ABase.ipynb 15
@patch
def Ps(self:abase,
       Xisa:jnp.ndarray # Joint strategy
       ) -> jnp.ndarray: # Stationary state distribution
    """Compute stationary state distribution `Ps`, given joint strategy `Xisa`."""
    
    # To make it work with JAX just-in-time compilation
    if self.has_last_statdist: # Check whether we found a previous Ps
        # If so, use jited computation
        Ps =  self._jaxPs(Xisa, self._last_statedist)
    else:
        # If not, use the slower numpy implementation once
        Ps = jnp.array(self._numpyPs(Xisa))
        self.has_last_statdist = True

    self._last_statedist = statedist
    return Ps


@patch
def _numpyPS(self:abase, Xisa):
    """
    Compute stationary distribution `Ps`, given joint strategy `Xisa`
    just using numpy and without using JAX.
    """
    Tss = self.Tss(Xisa)
    _pS = np.array(compute_stationarydistribution(Tss))

    # clean _pS from unwanted entries 
    _pS = _pS[:, pS.mean(0)!=-10]
    if len(pS[0]) == 0:  # this happens when the tollerance can distinquish 
        assert False, 'No _statdist return - must not happen'
    elif len(pS[0]) > 1:  # Should not happen, in an ideal world
            # sidenote: This means an ideal world is ergodic ;)
            print("More than 1 state-eigenvector found")

            if hasattr(self, '_last_statedist'):  # if last exists
                # take one that is closesd to last
                # Sidenote: should also not happen, because for this case
                # we are using the jitted implementation `_jaxPS`.
                pS0 = self._last_statedist
                choice = np.argmin(np.linalg.norm(_pS.T - pS0, axis=-1))
                print('taking closest to last')
            else: # if no last_Ps exists
                # take a random one.
                print(pS.round(2))
                nr = len(pS[0])
                choice = np.random.randint(nr)
                print("taking random one: ", choice)
               
    _pS = _pS[:, choice] 
    return pS.flatten() # clean

# %% ../../nbs/Agents/99_ABase.ipynb 17
@patch
def Ri(self:abase,
       Xisa:jnp.ndarray # Joint strategy `Xisa`
      ) -> jnp.ndarray: # Average reward `Ri`
    """Compute average reward `Ri`, given joint strategy `Xisa`.""" 
    i, s = 0, 1
    return jnp.einsum(self.statedist(X), [s], self.Ris(X), [i, s], [i])

# %% ../../nbs/Agents/99_ABase.ipynb 18
@patch
def trajectory(self:abase,
               Xinit:jnp.ndarray,  # Initial condition
               Tmax:int=100, # the maximum number of iteration steps
               tolerance:float=None, # to determine if a fix point is reached 
               verbose=False,  # Say something during computation?
               **kwargs) -> tuple: # (`trajectory`, `fixpointreached`)
    """
    Compute a joint learning trajectory.
    """
    traj = []
    t = 0
    X = Xinit.copy()
    fixpreached = False

    while not fixpreached and t < Tmax:
        print(f"\r [computing trajectory] step {t}", end='') if verbose else None 
        traj.append(X)

        X_, TDe = self.step(X)
        if np.any(np.isnan(X_)):
            fixpreached = True
            break

        if tolerance is not None:
            fixpreached = np.linalg.norm(X_ - X) < tolerance

        X = X_
        t += 1

    print(f" [trajectory computed]") if verbose else None

    return np.array(traj), fixpreached

# %% ../../nbs/Agents/99_ABase.ipynb 20
@patch
def _OtherAgentsActionsSummationTensor(self:abase):
    """
    To sum over the other agents and their respective actions using `einsum`.
    """
    dim = np.concatenate(([self.N],  # agent i
                          [self.N for _ in range(self.N-1)],  # other agnt
                          [self.M],  # agent a of agent i
                          [self.M for _ in range(self.N)],  # all acts
                          [self.M for _ in range(self.N-1)]))  # other a's
    Omega = np.zeros(dim.astype(int), int)

    for index, _ in np.ndenumerate(Omega):
        I = index[0]
        notI = index[1:self.N]
        A = index[self.N]
        allA = index[self.N+1:2*self.N+1]
        notA = index[2*self.N+1:]

        if len(np.unique(np.concatenate(([I], notI)))) is self.N:
            # all agents indices are different

            if A == allA[I]:
                # action of agent i equals some other action
                cd = allA[:I] + allA[I+1:]  # other actionss
                areequal = [cd[k] == notA[k] for k in range(self.N-1)]
                if np.all(areequal):
                    Omega[index] = 1

    return jnp.array(Omega)
