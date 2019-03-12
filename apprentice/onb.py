import numpy as np

def maxOrder(N, dim):
    """
    Utility function to find highest order polynomial
    for dataset with N dim-dimensional points.
    Intended to be used when constructing max ONB
    """
    from scipy.special import comb
    omax = 0
    while comb(dim + omax+1, omax+1) + 1 <= N: # The '+1' stands for a order 0 polynomial's dof
        omax+=1
    return omax

class ONB(object):
    """
    Calculator for basis orthogonalisation.
    """

    def __init__(self, data):
        """
        data ... np.array or file name to restore from
        a, b ... scaling target
        """
        if type(data)==str:
            self.mkFromFile(data)
        elif type(data)==dict:
            self.mkFromDict(data)
        else:
            self._X = np.atleast_2d(data)
            self._dim = np.atleast_2d(data).shape[1]
            self._calc(maxOrder(*np.atleast_2d(data).shape))

    @property
    def dim(self):
        """
        Shorthand to get the dimensionality of the parameter space
        """
        return self._dim


    # def _reduce(self, M):
        # """
        # To be called once best orders are determined.
        # We drop all unneccessay rows and columns.
        # """
        # from scipy.special import comb
        # Mdof = int(comb(self.dim + M, M))
        # self._R = self._R[:Mdof, :Mdof]
        # self._Q = self._Q[:,0:Mdof]

    def _calc(self, M):
        """
        Stieltjes ONB procedure
        M ... highest order for polynomials --- this determines the matrix structure
        """

        K = np.atleast_2d(self._X).shape[0]

        from scipy.special import comb
        Mdof = int(comb(self.dim + M, M))

        Q = np.atleast_2d(np.zeros((K, Mdof)))    # ONB
        R = np.atleast_2d(np.zeros((Mdof, Mdof))) # Recurrence matrix--- stores projections, required to evaluate polynomialsx

        recInfoInd = np.zeros(Mdof, dtype=np.int)
        recInfoVar = np.zeros(Mdof, dtype=np.int)


        R[0][0]=np.sqrt(K)             # initial (constant vector)
        Q[:,0] = np.ones((K))/R[0][0]  # insert into matrix

        i = 1 # Start algorithm at second vector
        ind = np.zeros(self.dim+1, dtype=np.int) # Bookkeeping,initially just a bunch of zeros

        # Iterate of degrees
        for m in range(1,M+1):
            # Iterate over variable
            for n in range(self.dim):
                indnn = i
                # Stieltjes/Gram-Schmidt loop.
                #
                # TODO:  This is MGS.  Would CGS be better for
                # parallelization/efficiency?
                # print("m= {} n={} ||  {} -- {}".format(m,n,ind[n], ind[-1]+1))
                for j in range(ind[n], ind[-1]+1):
                    Q[:,i] = self._X[:,n] * Q[:,j]
                    recInfoInd[i] = j;
                    recInfoVar[i] = n;

                    # Orthogonalize. 
                    for k in range(i):
                        R[k][i] = np.dot(Q[:,k],Q[:,i])
                        Q[:,i]  = Q[:,i] - R[k][i]*Q[:,k]
                    R[i][i]=np.linalg.norm(Q[:,i])
                    Q[:,i] = Q[:,i]/R[i][i]

                    # Re-orthogonalize.
                    for k in range(i):
                        Q[:,i] = Q[:,i] - np.dot(Q[:,k], Q[:,i])*Q[:,k]
                    Q[:,i] = Q[:,i]/np.linalg.norm(Q[:,i])
                    i+=1
                ind[n] = indnn
            ind[-1]=i-1

        self._Q = Q
        self._R = R
        self._recInd = recInfoInd
        self._recVar = recInfoVar

    @property
    def R(self): return self._R

    @property
    def Q(self): return self._Q

    # def __call__(self, m):
        # """
        # Operator, the arg m is the maximal polynomial order.
        # This calls _calc and will set/update Q, R and the recInfo
        # """
        # self._calc(m)
        # return self.Q, self.R


    def _recurrence(self, X, dof):
        """
        Build the recurrence matrix for point X.
        X   ... point of interest
        dof ... degrees of freedom
        """
        import numpy as np
        Q = np.zeros(dof)
        # TODO: make this more efficient
        Q[0] = 1./self._R[0][0]
        for i in range(1, dof):
            Q[i]  = X[self._recVar[i]] * Q[self._recInd[i]]
            for j in range(i): # Note: this was the trouble maker when translating from matlab
                Q[i] -= Q[j]*self._R[j][i]
            Q[i] /= self._R[i][i]
        return Q

    @property
    def asDict(self):
        return {
                "Q" : self.Q.tolist(),
                "R" : self.R.tolist(),
                "recInd": self._recInd.tolist(),
                "recVar": self._recVar.tolist(),
                "dim" : self._dim
                }

    def save(self, fname):
        import json
        with open(fname, "w") as f:
            json.dump( self.asDict, f, indent=4)

    def mkFromFile(self, fname):
        import json
        with open(fname, "r") as f:
            self.mkFromDict( json.load(f) )

    def mkFromDict(self, ONBDict):
        self._Q = np.array(ONBDict["Q"])
        self._R = np.array(ONBDict["R"])
        self._recInd = np.array(ONBDict["recInd"])
        self._recVar = np.array(ONBDict["recVar"])
        self._dim = int(ONBDict["dim"])

    def __str__(self):
        s="Stieltjes ONB generator"
        return s



if __name__== "__main__":

    X=np.linspace(-1,1,40)
    from pyraider import raider3
    rs = raider3.RaiderSet(np.array([[x] for x in X]), tol=-1)



    aa= ONB(np.array([[x] for x in X]))
    aa._recurrence([X[0]], 6)

    bb = ONB(X)
    # from IPython import embed
    # embed()


    D=np.array([[1.,2.], [3.,4.], [5.,6.], [7.,8.], [9.,1], [4,7], [5,3] ])
    from apprentice import Scaler
    S = Scaler(D)
    O = ONB(S.scaledPoints)
    # Q, R = O(2)
    print(O._recurrence(S.scaledPoints[0],6))


    O.save("testSaveONB.json")
    O2 = ONB("testSaveONB.json")
    print(O2._recurrence(S.scaledPoints[0],6))
    import sys
    sys.exit(1)
    Q2, R2 = O2(2)
    assert(all([a==b for a,b in zip(Q.ravel(),Q2.ravel())]))

    O3=Stieltjes(D, max_size=True)
