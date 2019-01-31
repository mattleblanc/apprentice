import numpy as np
from apprentice import monomial
from apprentice import tools
from scipy.optimize import minimize
from timeit import default_timer as timer


# from sklearn.base import BaseEstimator, RegressorMixin
# class RationalApproximationSIP(BaseEstimator, RegressorMixin):
class RationalApproximationSIP():
    def __init__(self, *args, **kwargs):
        """
        Multivariate rational approximation p(x)_m/q(x)_n

        args:
            fname   --- to read in previously calculated Pade approximation stored as the JSON file

            dict    --- to read in previously calculated Pade approximation stored as the dictionary object obtained after parsing the JSON file

            X       --- anchor points
            Y       --- function values

        kwargs:
            m               --- order of the numerator polynomial --- if omitted: auto 1 used
            n               --- order of the denominator polynomial --- if omitted: auto 1 used
            trainingscale   --- size of training data to use --- if omitted: auto 1x used
                                .5x is the half the numbner of coeffs in numerator and denominator,
                                1x is the number of coeffs in numerator and denominator,
                                2x is twice the number of coeffecients,
                                Cp is 100% of the data
            box             --- box (2D array of dim X [min,max]) within which to perform the approximation --- if omitted: auto dim X [-1, 1] used
            strategy        --- strategy to use --- if omitted: auto 0 used
                                0: min ||f*q(x)_m - p(x)_n||^2_2 sub. to q(x)_n >=1
                                1: min ||f*q(x)_m - p(x)_n||^2_2 sub. to q(x)_n >=1 and some p and/or q coeffecients set to 0
                                2: min ||f*q(x)_m - p(x)_n||^2_2 + lambda*||c_pq||_1 sub. to q(x)_n >=1
            roboptstrategy  --- strategy to optimize robust objective --- if omitted: auto 'ms' used
                                ss: single start algorithm using scipy.L-BFGS-B local optimizer
                                ms: multistart algorithm (with 10 restarts at random points from the box) using scipy.L-BFGS-B local optimizer
                                baron: pyomo with baron
                                solve: solve q(x) at random points in the box of X
                                ss_ms_so_ba: runs single start, multistart, baron and solve, and logs the different objective function values obtained
                                mlsl: multi-level single-linkage multistart algorithm from nlopt using nlopt.LD_LBFGS local optimizer
            penaltyparam    --- lambda to use for strategy 2 --- if omitted: auto 0.1 used
            penaltybin      --- penalty binary array for numberator and denomintor of the bits to keep active in strategy 1 and put in penalty term for activity 2
                                represented in a 2D array of shape(2,(m/n)+1) where for each numberator and denominator, the bits represent penalized coeffecient degrees and constant (1: not peanlized, 0 penalized)
                                required for strategy 1 and 2

        """
        import os
        if len(args) == 0:
            pass
        else:
            if type(args[0])==dict:
                self.mkFromDict(args[0])
            elif type(args[0]) == str:
                self.mkFromJSON(args[0])
            else:
                self._X   = np.array(args[0], dtype=np.float64)
                self._Y   = np.array(args[1], dtype=np.float64)
                self.mkFromData(kwargs=kwargs)

    @property
    def dim(self): return self._dim
    @property
    def M(self): return self._M
    @property
    def N(self): return self._N
    @property
    def m(self): return self._m
    @property
    def n(self): return self._n
    @property
    def trainingscale(self): return self._trainingscale
    @property
    def trainingsize(self): return self._trainingsize
    @property
    def box(self): return self._box
    @property
    def strategy(self): return self._strategy
    @property
    def roboptstrategy(self): return self._roboptstrategy
    @property
    def penaltyparam(self): return self._penaltyparam
    @property
    def ppenaltybin(self): return self._ppenaltybin
    @property
    def qpenaltybin(self): return self._qpenaltybin
    @property
    def pcoeff(self): return self._pcoeff
    @property
    def qcoeff(self): return self._qcoeff
    @property
    def iterationinfo(self): return self._iterationinfo
    @property
    def fittime(self): return self._fittime

    def mkFromJSON(self, fname):
        import json
        d = json.load(open(fname))
        self.mkFromDict(d)

    def mkFromDict(self, pdict):
        self._pcoeff        = np.array(pdict["pcoeff"]).tolist()
        self._qcoeff        = np.array(pdict["qcoeff"]).tolist()
        self._iterationinfo = pdict["iterationinfo"]
        self._dim           = pdict["dim"]
        self._m             = pdict["m"]
        self._n             = pdict["n"]
        self._M             = pdict["M"]
        self._N             = pdict["N"]
        self._fittime       = pdict["log"]["fittime"]
        self._strategy      = pdict["strategy"]
        self._roboptstrategy= pdict["roboptstrategy"]
        self._box           = np.array(pdict["box"],dtype=np.float64)
        self._trainingscale = pdict["trainingscale"]
        self._trainingsize  = pdict["trainingsize"]
        self._penaltyparam  = 0.0

        if(self.strategy ==1 or self.strategy==2):
            self._ppenaltybin = pdict['chosenppenalty']
            self._qpenaltybin = pdict['chosenqpenalty']

        if(self.strategy == 2):
            self._penaltyparam = pdict['lambda']

        self._struct_p      = monomial.monomialStructure(self.dim, self.m)
        self._struct_q      = monomial.monomialStructure(self.dim, self.n)
        # self.setStructures(pdict["m"], pdict["n"])

    def mkFromData(self, kwargs):
        """
        Calculate the Pade approximation
        """

        self._dim               = self._X[0].shape[0]

        self._m                 = int(kwargs["m"]) if kwargs.get("m") is not None else 1
        self._n                 = int(kwargs["n"]) if kwargs.get("n") is not None else 1
        self._M                 = tools.numCoeffsPoly(self.dim, self.m)
        self._N                 = tools.numCoeffsPoly(self.dim, self.n)
        self._strategy          = int(kwargs["strategy"]) if kwargs.get("strategy") is not None else 0
        self._roboptstrategy    = kwargs["roboptstrategy"] if kwargs.get("roboptstrategy") is not None else "ms"
        self._box               = np.empty(shape=(0,2))

        if(kwargs.get("box") is not None):
            for arr in kwargs.get("box"):
                newArr =np.array([[arr[0],arr[1]]],dtype=np.float64)
                self._box = np.concatenate((self._box,newArr),axis=0)
        else:
            for i in range(self.dim):
                newArr = np.array([[-1,1]],dtype=np.float64)
                self._box = np.concatenate((self._box,newArr),axis=0)

        self._trainingscale = kwargs["trainingscale"] if kwargs.get("trainingscale") is not None else "1x"
        if(self.trainingscale == ".5x" or self.trainingscale == "0.5x"):
            self.trainingscale = ".5x"
            self._trainingsize = int(0.5*(self.M+self.N))
        elif(self.trainingscale == "1x"):
            self._trainingsize = self.M+self.N
        elif(self.trainingscale == "2x"):
            self._trainingsize = 2*(self.M+self.N)
        elif(self.trainingscale == "Cp"):
            self._trainingsize = len(self._X)

        self._penaltyparam  = kwargs["penaltyparam"] if kwargs.get("penaltyparam") is not None else 0.0

        if(kwargs.get("ppenaltybin") is not None):
            self._ppenaltybin = kwargs["ppenaltybin"]
        elif(self.strategy ==1 or self.strategy==2):
            raise Exception("Binary Penalty for numerator required for strategy 1 and 2")

        if(kwargs.get("qpenaltybin") is not None):
            self._qpenaltybin = kwargs["qpenaltybin"]
        elif(self.strategy ==1 or self.strategy==2):
            raise Exception("Binary Penalty for denomintor equired for strategy 1 and 2")


        self._struct_p      = monomial.monomialStructure(self.dim, self.m)
        self._struct_q      = monomial.monomialStructure(self.dim, self.n)

        self._ipo            = np.empty((self.trainingsize,2),"object")
        for i in range(self.trainingsize):
            self._ipo[i][0] = monomial.recurrence(self._X[i,:],self._struct_p)
            self._ipo[i][1]= monomial.recurrence(self._X[i,:],self._struct_q)
        start = timer()
        self.fit()
        end = timer()
        self._fittime = end-start

    def fit(self):
        # Strategies:
        # 0: LSQ with SIP and without penalty
        # 1: LSQ with SIP and some coeffs set to 0 (using constraints)
        # 2: LSQ with SIP, penaltyParam > 0 and all or some coeffs in L1 term


        cons = np.empty(self.trainingsize, "object")
        for trainingIndex in range(self.trainingsize):
            q_ipo = self._ipo[trainingIndex][1]
            cons[trainingIndex] = {'type': 'ineq', 'fun':self.robustSample, 'args':(q_ipo,)}

        p_penaltyIndex = []
        q_penaltyIndex = []
        if(self.strategy ==1 or self.strategy == 2):
            p_penaltyIndex, q_penaltyIndex = self.createPenaltyIndexArr()
        coeff0 = []
        if(self.strategy == 0):
            coeffs0 = np.zeros((self.M+self.N))
        elif(self.strategy == 1):
            coeffs0 = np.zeros((self.M+self.N))
            for index in p_penaltyIndex:
                cons = np.append(cons,{'type': 'eq', 'fun':self.coeffSetTo0, 'args':(index, "p")})
            for index in q_penaltyIndex:
                cons = np.append(cons,{'type': 'eq', 'fun':self.coeffSetTo0, 'args':(index, "q")})
        elif(self.strategy == 2):
            coeffs0 = np.zeros(2*(self.M+self.N))
            for index in p_penaltyIndex:
                cons = np.append(cons,{'type': 'ineq', 'fun':self.abs1, 'args':(index, "p")})
                cons = np.append(cons,{'type': 'ineq', 'fun':self.abs2, 'args':(index, "p")})
            for index in q_penaltyIndex:
                cons = np.append(cons,{'type': 'ineq', 'fun':self.abs1, 'args':(index, "q")})
                cons = np.append(cons,{'type': 'ineq', 'fun':self.abs2, 'args':(index, "q")})
        else:
            raise Exception("fit() strategy %i not implemented"%self.strategy)

        maxIterations = 100 # hardcode for now. Param later?
        maxRestarts = 10    # hardcode for now. Param later?
        threshold = 0.02
        self._iterationinfo = []
        for iter in range(1,maxIterations+1):
            data = {}
            data['iterationNo'] = iter
            ret = {}
            start = timer()
            if(self.strategy == 2):
                ret = minimize(self.leastSqObjWithPenalty, coeffs0, args = (p_penaltyIndex,q_penaltyIndex),method = 'SLSQP', constraints=cons, options={'maxiter': 1000,'ftol': 1e-4, 'disp': False})
            else:
                ret = minimize(self.leastSqObj, coeffs0 ,method = 'SLSQP', constraints=cons, options={'maxiter': 1000,'ftol': 1e-4, 'disp': False})
            end = timer()
            optstatus = {'message':ret.get('message'),'status':ret.get('status'),'noOfIterations':ret.get('nit'),'time':end-start}

            coeffs = ret.get('x')
            # print(ret)
            # print(np.c_[coeffs[self.M+self.N:self.M+self.N+self.M],coeffs[0:self.M], coeffs[self.M+self.N:self.M+self.N+self.M]-coeffs[0:self.M] ])
            # print(np.c_[coeffs[self.M+self.N+self.M:self.M+self.N+self.M+self.N],coeffs[self.M:self.M+self.N]])
            leastSq = ret.get('fun')
            data['log'] = optstatus
            data['leastSqObj'] = leastSq
            data['pcoeff'] = coeffs[0:self.M].tolist()
            data['qcoeff'] = coeffs[self.M:self.M+self.N].tolist()

            if(self.strategy == 2):
                lsqsplit = {}
                l1term = self.computel1Term(coeffs,p_penaltyIndex,q_penaltyIndex)
                lsqsplit['l1term'] = l1term
                lsqsplit['l2term'] = leastSq - self.penaltyparam * l1term
                data['leastSqSplit'] = lsqsplit

            # data['restartInfo'] = []
            robO = 0
            x = []
            if(self._roboptstrategy == 'ss'):
                maxRestarts = 1
                x, robO, restartInfo = self.multipleRestartRobO(coeffs,maxRestarts,threshold)
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':restartInfo}
            elif(self._roboptstrategy == 'ms'):
                maxRestarts = 10
                x, robO, restartInfo = self.multipleRestartRobO(coeffs,maxRestarts,threshold)
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':restartInfo}
            elif(self._roboptstrategy == 'mlsl'):
                x, robO, restartInfo = self.mlslRobO(coeffs,threshold)
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':restartInfo}
            elif(self._roboptstrategy == 'baron'):
                x, robO, restartInfo = self.baronPyomoRobO(coeffs,threshold)
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':restartInfo}
            elif(self._roboptstrategy == 'solve'):
                x, robO, info = self.solveRobO(coeff=coeffs,threshold=threshold)
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':info}
            elif(self._roboptstrategy == 'ss_ms_so_ba'):
                # ss
                maxRestarts = 1
                ssx, ssrobO, ssrestartInfo = self.multipleRestartRobO(coeffs,maxRestarts,threshold)

                # ms
                maxRestarts = 10
                msx, msrobO, msrestartInfo = self.multipleRestartRobO(coeffs,maxRestarts,threshold)

                # ba
                start = timer()
                bax, barobO, barestartInfo = self.baronPyomoRobO(coeffs,threshold)
                end = timer()

                # so
                onesolve = 2.74464035034e-05
                maxEvals = int((end-start)/onesolve)
                sox1, sorobO1, soinfo1 = self.solveRobO(coeff=coeffs,threshold=threshold, maxEvals=maxEvals)
                sox2, sorobO2, soinfo2 = self.solveRobO(coeff=coeffs,threshold=threshold, maxEvals=2*maxEvals)
                sox3, sorobO3, soinfo3 = self.solveRobO(coeff=coeffs,threshold=threshold, maxEvals=3*maxEvals)
                sox4, sorobO4, soinfo4 = self.solveRobO(coeff=coeffs,threshold=threshold, maxEvals=4*maxEvals)

                robOarr = np.array([ssrobO,msrobO,barobO,sorobO1,sorobO2,sorobO3,sorobO4])
                xdict = {0:ssx,1:msx,2:bax,3:sox1,4:sox2,5:sox3,6:sox4}
                robO = np.min(robOarr)
                x = xdict[np.argmin(robOarr)]

                diffd = {}
                diffd['ss'] = ssrobO
                diffd["ms"] = msrobO
                diffd['ba'] = barobO
                diffd['so1x'] = sorobO1
                diffd['so2x'] = sorobO2
                diffd['so3x'] = sorobO3
                diffd['so4x'] = sorobO4
                restartInfo = {'ssInfo':ssrestartInfo,'msInfo':msrestartInfo,'baInfo':barestartInfo,'so1xInfo':soinfo1,'so2xInfo':soinfo2,'so3xInfo':soinfo3,'so4xInfo':soinfo4}
                data['robOptInfo'] = {'robustArg':x.tolist(),'robustObj':robO,'info':restartInfo,'diff':diffd}
            else: raise Exception("rob opt strategy unknown")



            self._iterationinfo.append(data)
            if(robO >= threshold):
                break
            q_ipo_new = monomial.recurrence(x,self._struct_q)
            cons = np.append(cons,{'type': 'ineq', 'fun':self.robustSample, 'args':(q_ipo_new,)})

        if(len(self._iterationinfo) == maxIterations and self._iterationinfo[maxIterations-1]['robOptInfo']["robustObj"]<threshold):
            import json
            j = json.dumps(self._iterationinfo,indent=4, sort_keys=True)
            raise Exception(j+"\nCould not find a robust objective")
        self._pcoeff = self._iterationinfo[len(self._iterationinfo)-1]["pcoeff"]
        self._qcoeff = self._iterationinfo[len(self._iterationinfo)-1]["qcoeff"]

    def solveRobO(self, coeff, threshold=0.2,maxEvals=50000):
        start = timer()
        info = []
        minx = []
        minq = np.inf
        actualEvals = maxEvals
        for r in range(maxEvals):
            x=[]
            if(r == 0):
                x = np.array([(self.box[i][0]+self.box[i][1])/2 for i in range(self.dim)], dtype=np.float64)
            else:
                x = np.zeros(self.dim, dtype=np.float64)
                for d in range(self.dim):
                    x[d] = np.random.rand()*(self.box[d][1]-self.box[d][0])+self.box[d][0]
            q_ipo = monomial.recurrence(x,self._struct_q)
            q = np.sum([coeff[i]*q_ipo[i-self.M] for i in range(self.M,self.M+self.N)])
            if(minq > q):
                minq = q
                minx = x
            if(q < 3*threshold):
                rinfo = {'robustArg':x.tolist(),'robustObj':q}
                info.append(rinfo)
            if(q < threshold):
                actualEvals = r+1
                break
        end = timer()
        info.append({'log':{'maxEvals':maxEvals,'actualEvals':actualEvals,'time':end-start}})
        return minx, minq, info


    def variableBound(self, model, i):
        b = (self._box[i][0], self._box[i][1])
        return b

    def baronPyomoRobO(self, coeffs, threshold=0.2):
        from pyomo import environ
        info = np.zeros(shape=(len(self._struct_q),self._dim+1),dtype=np.float64)
        for l in range(len(self._struct_q)):
            for d in range(self._dim):
                info[l][d] = self._struct_q[l][d]
            info[l][self._dim] = coeffs[l+self._M]
        model = environ.ConcreteModel()
        model.dimrange = range(self._dim)
        model.coeffinfo = info
        model.x = environ.Var(model.dimrange, bounds=self.variableBound)
        model.robO = environ.Objective(rule=self.robObjPyomo, sense=1)
        opt = environ.SolverFactory('baron')

        """
        Control where the log file is written by passing “logfile=<name>”
        to the solve method.

        If you want to print solver log to console, add tee=True to solve method

        If you want the solution and problem files to be logged,
        you can set keepfiles=True for that file to not be deleted.

        Also, if you set keepfiles to True, you can find the location of Solver log file,
        Solver problem files, and Solver solution file printed on console (usually
        located in /var/folders/)
        """
        pyomodebug = 0
        if(pyomodebug == 0):
            ret = opt.solve(model)
        elif(pyomodebug == 1):
            import uuid
            uniquefn = str(uuid.uuid4())
            logfn = "/tmp/%s.log"%(uniquefn)
            print("Log file name: %s"%(logfn))
            ret = opt.solve(model,tee=True,logfile=logfn)
            model.pprint()
            ret.write()

        optstatus = {'message':str(ret.solver.termination_condition),'status':str(ret.solver.status),'time':ret.solver.time,'error_rc':ret.solver.error_rc}

        robO = model.robO()
        x = np.array([model.x[i].value for i in range(self._dim)])
        info = [{'robustArg':x.tolist(),'robustObj':robO,'log':optstatus}]

        return x, robO, info


    """
    MLSL with LBFGS does not converge. Untested. Not fixed. DO NOT USE!!!
    """
    def mlslRobO(self,coeffs, threshold=0.2):
        import nlopt
        localopt = nlopt.opt(nlopt.LD_LBFGS, self._dim)
        localopt.set_lower_bounds(self._box[:,0])
        localopt.set_upper_bounds(self._box[:,1])
        localopt.set_min_objective(lambda x,grad: self.robustObjWithGrad(x,grad,coeffs))
        localopt.set_xtol_rel(1e-4)

        mlslopt = nlopt.opt(nlopt.G_MLSL_LDS, self._dim)
        mlslopt.set_lower_bounds(self._box[:,0])
        mlslopt.set_upper_bounds(self._box[:,1])
        mlslopt.set_min_objective(lambda x,grad: self.robustObjWithGrad(x,grad,coeffs))
        mlslopt.set_local_optimizer(localopt)
        mlslopt.set_stopval(1e-20)
        mlslopt.set_maxtime(500.0)

        x0 = np.array([(self.box[i][0]+self.box[i][1])/2 for i in range(self.dim)], dtype=np.float64)
        x = mlslopt.optimize(x0)
        robO = mlslopt.last_optimum_value()
        info = [{'robustArg':x.tolist(),'robustObj':robO}]

        # print(info)
        # exit(1)

        return x, robO, info

    def multipleRestartRobO(self, coeffs, maxRestarts = 10, threshold=0.2):
        minx = []
        restartInfo = []
        minrobO = np.inf
        for r in range(maxRestarts):
            x0 = []
            if(r == 0):
                x0 = np.array([(self.box[i][0]+self.box[i][1])/2 for i in range(self.dim)], dtype=np.float64)
            else:
                x0 = np.zeros(self.dim, dtype=np.float64)
                for d in range(self.dim):
                    x0[d] = np.random.rand()*(self.box[d][1]-self.box[d][0])+self.box[d][0]
            start = timer()
            ret = minimize(self.robustObj, x0, bounds=self.box, args = (coeffs,),method = 'L-BFGS-B', options={'maxiter': 1000,'ftol': 1e-4, 'disp': False})
            end = timer()
            optstatus = {'message':ret.get('message'),'status':ret.get('status'),'noOfIterations':ret.get('nit'),'time':end-start}
            x = ret.get('x')
            robO = ret.get('fun')
            if(minrobO > robO):
                minrobO = robO
                minx = x
            rinfo = {'robustArg':x.tolist(),'robustObj':robO, 'log':optstatus}
            restartInfo.append(rinfo)
            if(robO < threshold):
                break
        return minx, minrobO, restartInfo

    def leastSqObj(self,coeff):
        sum = 0
        for index in range(self.trainingsize):
            p_ipo = self._ipo[index][0]
            q_ipo = self._ipo[index][1]

            P = np.sum([coeff[i]*p_ipo[i] for i in range(self.M)])
            Q = np.sum([coeff[i]*q_ipo[i-self.M] for i in range(self.M,self.M+self.N)])

            sum += (self._Y[index] * Q - P)**2
        return sum

    def computel1Term(self,coeff,p_penaltyIndexs=np.array([]), q_penaltyIndexs=np.array([])):
        l1Term = 0
        for index in p_penaltyIndexs:
            term = coeff[self.M+self.N+index]
            if(abs(term) > 10**-5):
                l1Term += term
        for index in q_penaltyIndexs:
            term = coeff[self.M+self.N+self.M+index]
            if(abs(term) > 10**-5):
                l1Term += term
        return l1Term

    def leastSqObjWithPenalty(self,coeff,p_penaltyIndexs=np.array([]), q_penaltyIndexs=np.array([])):
        sum = self.leastSqObj(coeff)
        l1Term = self.penaltyparam * self.computel1Term(coeff, p_penaltyIndexs, q_penaltyIndexs)
        return sum+l1Term

    def abs1(self,coeff, index, pOrq="q"):
        ret = -1
        if(pOrq == "p"):
            ret = coeff[self.M+self.N+index] - coeff[index]
        elif(pOrq == "q"):
            ret = coeff[self.M+self.N+self.M+index] - coeff[self.M+index]
        return ret

    def abs2(self,coeff, index, pOrq="q"):
        ret = -1
        if(pOrq == "p"):
            ret = coeff[self.M+self.N+index] + coeff[index]
        elif(pOrq == "q"):
            ret = coeff[self.M+self.N+self.M+index] + coeff[self.M+index]
        return ret

    def coeffSetTo0(self, coeff, index, pOrq="q"):
        ret = -1
        if(pOrq == "p"):
            ret = coeff[index]
        elif(pOrq == "q"):
            ret = coeff[self.M+index]
        return ret

    def robustSample(self,coeff, q_ipo):
        return np.sum([coeff[i]*q_ipo[i-self.M] for i in range(self.M,self.M+self.N)])-1

    def robObjPyomo(self, model):
        dim = len(model.dimrange)
        res = 0
        for mon in model.coeffinfo:
            term = 1
            for d in model.dimrange:
                term *= model.x[d] ** mon[d]
            res += mon[dim] * term
        return res

    def robustObjWithGrad(self, x, grad, coeff):
        if grad.size > 0:
            g = tools.getPolyGradient(coeff=coeff[self.M:self.M+self.N],X=x, dim=self._dim,n=self._n)
            for i in range(grad.size): grad[i] = g[i]

        q_ipo = monomial.recurrence(x,self._struct_q)

        res = np.sum([coeff[i]*q_ipo[i-self.M] for i in range(self.M,self.M+self.N)])
        return res

    def robustObj(self,x,coeff):
        q_ipo = monomial.recurrence(x,self._struct_q)
        return np.sum([coeff[i]*q_ipo[i-self.M] for i in range(self.M,self.M+self.N)])

    def createPenaltyIndexArr(self):
        p_penaltyBinArr = self.ppenaltybin
        q_penaltyBinArr = self.qpenaltybin

        p_penaltyIndex = np.array([], dtype=np.int64)
        for index in range(self.m+1):
            if(p_penaltyBinArr[index] == 0):
                if(index == 0):
                    p_penaltyIndex = np.append(p_penaltyIndex, 0)
                else:
                    A = tools.numCoeffsPoly(self.dim, index-1)
                    B = tools.numCoeffsPoly(self.dim, index)
                    for i in range(A, B):
                        p_penaltyIndex = np.append(p_penaltyIndex, i)

        q_penaltyIndex = np.array([],dtype=np.int64)
        for index in range(self.n+1):
            if(q_penaltyBinArr[index] == 0):
                if(q_penaltyBinArr[index] == 0):
                    if(index == 0):
                        q_penaltyIndex = np.append(q_penaltyIndex, 0)
                    else:
                        A = tools.numCoeffsPoly(self.dim, index-1)
                        B = tools.numCoeffsPoly(self.dim, index)
                        for i in range(A, B):
                            q_penaltyIndex = np.append(q_penaltyIndex, i)

        return p_penaltyIndex, q_penaltyIndex

    def numer(self, X):
        """
        Evaluation of the denom poly at X.
        """
        ipo = np.empty(len(X),"object")
        for i in range(len(X)):
            ipo[i] = monomial.recurrence(X[i,0:self.dim],self._struct_p)
            ipo[i] = ipo[i].dot(self._pcoeff)
        return ipo

    def denom(self, X):
        """
        Evaluation of the numer poly at X.
        """
        ipo = np.empty(len(X),"object")
        for i in range(len(X)):
            ipo[i] = monomial.recurrence(X[i,0:self.dim],self._struct_q)
            ipo[i] = ipo[i].dot(self._qcoeff)
        return ipo

    def predict(self, X):
        """
        Return the prediction of the RationalApproximation at X.
        """
        return self.numer(X)/self.denom(X)

    def __call__(self, X):
        """
        Operator version of predict.
        """
        return self.predict(X)

    @property
    def asDict(self):
        """
        Store all info in dict as basic python objects suitable for JSON
        """
        d={}
        d['pcoeff']                 = self._pcoeff
        d['qcoeff']                 = self._qcoeff
        d['iterationinfo']    = self._iterationinfo
        d['dim']              = self._dim
        d['m'] = self._m
        d['n'] = self._n
        d['M'] = self._M
        d['N'] = self._N
        d["log"] = {"fittime":self._fittime}
        d['strategy'] = self._strategy
        d['roboptstrategy'] = self._roboptstrategy
        d['box'] = self._box.tolist()
        d['trainingscale'] = self._trainingscale
        d['trainingsize'] = self._trainingsize

        if(self.strategy ==1 or self.strategy==2):
            d['chosenppenalty'] = self._ppenaltybin
            d['chosenqpenalty'] = self._qpenaltybin


        if(self.strategy==2):
            d['lambda'] = self._penaltyparam
        return d

    @property
    def asJSON(self):
        """
        Store all info in dict as basic python objects suitable for JSON
        """
        d = self.asDict
        import json
        return json.dumps(d,indent=4, sort_keys=True)

    def save(self, fname, indent=4, sort_keys=True):
        import json
        with open(fname, "w") as f:
            json.dump(self.asDict, f,indent=indent, sort_keys=sort_keys)

if __name__=="__main__":
    import sys
    infilePath11 = "../benchmarkdata/f11_noise_0.1.txt"
    infilePath1 = "../benchmarkdata/f1_noise_0.1.txt"
    X, Y = tools.readData(infilePath11)
    r = RationalApproximationSIP(X,Y,
                                m=2,
                                n=3,
                                trainingscale="1x",
                                box=np.array([[-1,1]]),
                                # box=np.array([[-1,1],[-1,1]]),
                                strategy=2,
                                penaltyparam=10**-1,
                                ppenaltybin=[1,0,0],
                                qpenaltybin=[1,0,0,0]
    )
    # r.save("/Users/mkrishnamoorthy/Desktop/pythonRASIP.json")

    r2 = RationalApproximationSIP(r.asDict)
    print(r2.asJSON)
    print(r2.pcoeff, r2.qcoeff,r2.box,r2.ppenaltybin,r2.qpenaltybin, r2.dim)
    print(r2(X[0:4,:])) #calls predict

    # r1 = RationalApproximationSIP("/Users/mkrishnamoorthy/Desktop/pythonRASIP.json")
    # print(r1.asJSON)








# END
