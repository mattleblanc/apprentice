import apprentice
import numpy as np

# from numba import jit
# @jit(forceobj=True, parallel=True)
def gradientRecurrence(X, struct, jacfac, NNZ, sred):
    """
    X ... scaled point
    struct ... polynomial structure
    jacfac ... jacobian factor
    NNZ  ... list of np.where results
    sred ... reduced structure
    returns array suitable for multiplication with coefficient vector
    """
    dim = len(X)
    REC = np.zeros((dim, len(struct)))
    _RR = np.power(X, struct)
    nelem = len(sred[0])

    W=[_RR[nz] for nz in NNZ]


    for coord, (RR, nz) in enumerate(zip(W,NNZ)):
        RR[:, coord] = jacfac[coord] * sred[coord] *_RR[:nelem, coord]
        REC[coord][nz] = np.prod(RR, axis=1)


    return REC

# from numba import jit
# @jit(forceobj=True, parallel=True)
def gradientRecurrenceMulti(X, struct, jacfac, NNZ, sred):
    """
    X ... np array  of scaled points
    struct ... polynomial structure
    jacfac ... jacobian factor
    NNZ  ... list of np.where results
    sred ... reduced structure
    returns array suitable for multiplication with coefficient vector
    """

    nelem = len(sred[0])

    m_RR = np.power(X[:,np.newaxis], struct)
    WW = m_RR[:,NNZ].reshape(*X.shape, nelem, X.shape[1])

    RREC = np.zeros((*X.shape, len(struct)))

    for coord, nz in enumerate(NNZ):
        a = jacfac[coord] * sred[coord] * m_RR[:,:nelem,coord]
        RR = WW[:,coord]
        RR[:,:,coord] = a
        RREC[:,coord][:,nz] = np.prod(RR,axis=2).reshape((X.shape[0], 1, nelem))

    return RREC

# @jit(forceobj=True)#, parallel=True)
def prime(GREC, COEFF, dim, NNZ):
    ret = np.empty((len(COEFF), dim))
    for i in range(dim):
        ret[:,i] = np.sum(COEFF[:,NNZ[i]] * GREC[i, NNZ[i]], axis=2).flatten()
    return ret


class FunctionalApprox(object):
    def __init__(self, ndim, pcoeff=None, qcoeff=None, m=0, n=0):
        self.scaler_ = None
        self.dim_ = ndim
        self.orderp_ = m
        self.orderq_ = n
        self.currec_ = None

        if self.dim_ == 1: self.recurrence = apprentice.monomial.recurrence1D
        else:              self.recurrence = apprentice.monomial.recurrence

        self.setCoefficients(pcoeff, qcoeff)
        self.setStructure()

    @property
    def dim(self): return self.dim_

    def setCoefficients(self, pcoeff, qcoeff=None):
        """
        Obvious
        """
        self.pcoeff_ = pcoeff
        self.qcoeff_ = qcoeff

    def setStructure(self):
        """
        Monomial structures for evaluation of values and gradients
        """
        self.structure_      = np.array(apprentice.monomialStructure(self.dim_, max(self.orderp_, self.orderq_)), dtype=np.int32)
        self.nonzerostruct_  = [np.where(self.structure_[:, coord] != 0) for coord in range(self.dim_)]
        self.reducedstruct_  = np.array([self.structure_[nz][:,num] for num, nz in enumerate(self.nonzerostruct_)], dtype=np.int32)

    def setScaler(self, sdict):
        self.scaler_ = apprentice.Scaler(sdict)

    def setRecurrence(self, x):
        if self.scaler_ is not None:
            xs = self.scaler_.scale(x)
        else:
            xs = x
        self.currec_ = np.prod(np.power(xs, self.structure_[:, np.newaxis]), axis=2).T

    def val(self, x, sel=slice(None, None, None), set_recurrence=True):
        """
        Evaluation of the numerator and denominator polynomials at one or many points x.
        """

        if set_recurrence:
            self.setRecurrence(x)

        PV = self.currec_ * self.pcoeff_[sel][:, np.newaxis]
        vals = np.sum(PV, axis=2)

        if self.qcoeff_ is not None:
            QV = self.currec_ * self.qcoeff_[sel][:, np.newaxis]
            qvals = np.sum(QV, axis=2)
            vals/=qvals

        return vals

    def grad(self, x, sel=slice(None, None, None), set_recurrence=True):
        """
        If x is single point -> array of gradients for all bins
        If x is collection of points -> all sorts of gradients etc
        """
        if set_recurrence: self.setRecurrence(x)
        xs = self.scaler_.scale(x)
        GREC = gradientRecurrence(xs, self.structure_, self.scaler_.jacfac, self.nonzerostruct_, self.reducedstruct_)

        # NOTE this is expensive -- pybind11??
        # Pprime = np.sum(self._PC[sel].reshape((self._PC[sel].shape[0], 1, self._PC[sel].shape[1])) * GREC, axis=2)
        Pprime = prime(GREC, self.pcoeff_[sel], self.dim_, self.nonzerostruct_)

        # if self._hasRationals:
            # P = np.atleast_2d(np.sum(self._maxrec * self._PC[sel], axis=1))
            # Q = np.atleast_2d(np.sum(self._maxrec * self._QC[sel], axis=1))
            # Qprime = prime(GREC, self._QC[sel], self.dim, self._NNZ)
            # return np.array(Pprime/Q.transpose() - (P/Q/Q).transpose()*Qprime, dtype=np.float64)

        return np.array(Pprime, dtype=np.float64)
        # struct = np.array(self._struct_p, dtype=np.float)
        # X = self._scaler.scale(np.array(X))

        # if self.dim==1:
            # struct[1:]=self._scaler.jacfac[0]*struct[1:]*np.power(X, struct[1:]-1)
            # return np.dot(np.atleast_2d(struct),self._pcoeff)

        # from apprentice.tools import gradientRecursion
        # GREC = gradientRecursion(X, struct, self._scaler.jacfac)

        # return np.sum(GREC * self._pcoeff, axis=1)
        # pass

    def hess(X, sel=slice(None, None, None)):
        """
        If x is single point -> array of hessians for all bins
        If x is collection of points -> all sorts of hessians etc
        """
        pass
