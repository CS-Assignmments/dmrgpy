from ..algebra import algebra
from .. import multioperator
import scipy.sparse.linalg as slg
from ..algebra import kpm
import numpy as np
#from numba import jit


def get_dynamical_correlator(self,name=None,submode="KPM",**kwargs):
    """
    Compute the dynamical correlator
    """
    if name is None: raise
    if type(name[0])==multioperator.MultiOperator: # multioperator
      A = name[0].get_dagger() # dagger
      A = self.get_operator(A)
      B = self.get_operator(name[1])
    else:
      raise # this is no longer used
    self.get_gs() # compute ground state
    h = self.get_operator(self.hamiltonian) # Hamiltonian in matrix form
    if submode=="KPM":
      return dynamical_correlator_kpm(h,self.e0,self.wf0,A,B,**kwargs)
    elif submode=="ED":
      return dynamical_correlator_ED(h,A,B,**kwargs)
    elif submode=="INV":
      return dynamical_correlator_inv(h,self.wf0,self.e0,A,B,**kwargs)
    elif submode=="TD":
      from .. import timedependent
      return timedependent.dynamical_correlator(self,mode="ED",
              name=name,**kwargs)
    else: raise


def dynamical_correlator_kpm(h,e0,wf0,A,B,
        delta=1e-1,es=np.linspace(-1.,10,400)):
    vj = A@wf0 # first wavefunction
    vi = B@wf0 # second wavefunction
    m = -np.identity(h.shape[0])*e0+h # matrix to use
    emax = slg.eigsh(h,k=1,ncv=20,which="LA")[0] # upper energy
    scale = np.max([np.abs(e0),np.abs(emax)])*3.0
    n = 4*int(scale/delta) # number of polynomials
    (xs,ys) = kpm.dm_vivj_energy(m,vi,vj,scale=scale,
                                npol=n*4,ne=n*10,x=es)
    return xs,np.conjugate(ys) # return correlator




def dynamical_correlator_ED(h,a0,b0,delta=2e-2,
        es=np.linspace(-1.0,10.0,600)):
    """Compute a dynamical correlator"""
    emu,vs = algebra.eigh(h)
    U = np.array(vs) # matrix
    Uh = np.conjugate(np.transpose(U)) # Hermitian
    b0 = np.conjugate(b0.T)
    A = Uh@a0@U # get the matrix elements
    B = Uh@b0@U # get the matrix elements
    out = 0.0+es*0.0*1j # initialize
    out = dynamical_sum(emu,es+1j*delta,A,B,out) # perform the summation
    out -= dynamical_sum(emu,es-1j*delta,A,B,out) # perform the summation
    return (es,-out.imag/np.pi) # return correlator

#@jit(nopython=True)
def dynamical_sum(es,ws,A,B,out):
    """Return the sum giving the dynamical correlator"""
    out = out*0.0 # initialize
    es = es-np.min(es) # remove minimum
    n = len(es) # number of energies
    for iw in range(len(ws)): # loop over frequencies
        i = 0
        for j in range(n): # loop over energies
            tmp = A[i,j]*B[j,i]
            tmp *= 1./(ws[iw]+es[i] - es[j])
            out[iw] = out[iw] + tmp
    return out # return dynamical correlator


def dynamical_correlator_inv(h0,wf0,e0,A,B,es=np.linspace(-1,10,600),
        delta=1e-2,mode="cv"):
  """Calculate a correlation function SiSj in a frequency window"""
  ## default method
  iden = np.identity(h0.shape[0],dtype=np.complex) # identity
  out = []
  B = np.conjugate(B.T) # transpose
  for e in es: # loop over energies
      if mode=="full": # using exact inversion
        g1 = algebra.inv(iden*(e+e0+1j*delta)-h0)
        g2 = algebra.inv(iden*(e+e0-1j*delta)-h0)
        g = 1j*(g1-g2)/2.
        op = A@g@B # operator
        o = algebra.braket_wAw(wf0,op) # correlator
      elif mode=="cv": # correction vector algorithm
          o1 = solve_cv(h0,wf0,A,B,e+e0,delta=delta) # conjugate gradient
          o2 = solve_cv(h0,wf0,A,B,e+e0,delta=-delta) # conjugate gradient
          o = 1j*(o1 - o2)/2. # substract
      else: raise # not recognised
      out.append(o)
  return es,np.array(out) # return result



def solve_cv(h0,wf0,si,sj,w,delta=0.0):
     iden = np.identity(h0.shape[0],dtype=np.complex) # identity
     b = -delta*sj*np.matrix(wf0).T # create the b vector
     A = (h0 - w*iden)*(h0-w*iden) + iden*delta*delta # define A matrix
     b = np.array(b).reshape((b.shape[0],)) # array
     x,info = slg.cg(A,b,tol=1e-10) # solve the equation
     x = np.matrix(x).T # column vector
     x = 1j*x + (h0 - w*iden)*x/delta # full correction vector
     x = si*x # apply second operator
     o = (np.matrix(wf0).H.T*x).trace()[0,0] # compute the braket
     return o





