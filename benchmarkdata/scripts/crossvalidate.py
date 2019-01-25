import numpy as np
from apprentice import RationalApproximationSIP
from sklearn.model_selection import KFold
from apprentice import tools, readData

def runCrossValidation(infile,box=np.array([[-1,1],[-1,1]]),outfile="out.json",debug=0):
	trainingScale = "Cp"

	X, Y = tools.readData(infile)

	# Some param overrides for debug
	larr = np.array([10**i for i in range(3,-13,-1)])
	# larr = np.array([10**i for i in range(0,-5,-1)])

	k=10
	# k=2

	outJSON = {}
	for pdeg in range(2,5):
	# for pdeg in range(3,5):
		ppenaltybin = np.zeros(pdeg+1)
		for qdeg in range(2,5):
		# for qdeg in range(3,5):
			qpenaltybin = np.zeros(qdeg+1)
			avgerror = np.zeros(len(larr))
			avgerror_k = np.zeros(len(larr))
			for index in range(len(larr)):
				l = larr[index]
				kfold = KFold(k)
				error_l = 0
				for train, test in kfold.split(X):
					rappsip = RationalApproximationSIP(
												X[train],
												Y[train],
				                                m=pdeg,
				                                n=qdeg,
				                                trainingscale=trainingScale,
				                                box=box,
				                                strategy=2,
				                                penaltyparam=l,
				                                ppenaltybin=ppenaltybin.tolist(),
				                                qpenaltybin=qpenaltybin.tolist()
				    )
					error_l_k = np.sum([(rappsip(X[test])-Y[test])**2])
					error_l += error_l_k
				avgerror[index] = error_l / len(X)
				avgerror_k[index] = error_l / len(X[test])
			stderror = np.std(avgerror_k)/np.sqrt(k)
			minIndex = np.argmin(avgerror)
			minv = avgerror[minIndex]
			minl = larr[minIndex]

			currIndex = minIndex
			while currIndex >= 0:
				if(minv + stderror == avgerror[currIndex]):
					break
				elif(minv + stderror > avgerror[currIndex]):
					currIndex -= 1
				else:
					currIndex += 1
					break
			if(currIndex == -1):
				currIndex = 0
			currl = larr[currIndex]

			# print(minIndex)
			# print(currIndex)
			#
			# print(avgerror)
			# print(avgerror_k)
			# print(stderror)
			#
			# print(minl)
			# print(currl)

			rappsip_min = RationalApproximationSIP(
										X,
										Y,
										m=pdeg,
										n=qdeg,
										trainingscale=trainingScale,
										box=box,
										strategy=2,
										penaltyparam=minl,
										ppenaltybin=ppenaltybin.tolist(),
										qpenaltybin=qpenaltybin.tolist()
			)
			rappsip_minpse = rappsip_min
			if(currl != minl):
				rappsip_minpse = RationalApproximationSIP(
											X,
											Y,
											m=pdeg,
											n=qdeg,
											trainingscale=trainingScale,
											box=box,
											strategy=2,
											penaltyparam=currl,
											ppenaltybin=ppenaltybin.tolist(),
											qpenaltybin=qpenaltybin.tolist()
			)
			rappsip = {"min":rappsip_min.asDict, "min plus SE":rappsip_minpse.asDict, "avgerror":avgerror.tolist(),
						"avgerror_k":avgerror_k.tolist(), "stderror":stderror,"minIndex":minIndex,"minl":minl,
						"minv":minv, "mpseIndex":currIndex, "mpsel":currl}

			outJSON["p%s_q%s"%(str(pdeg),str(qdeg))] = rappsip

			if(debug == 1):
				import json
				with open("/tmp/cv_latest.json", "w") as f:
					json.dump(outJSON, f,indent=4, sort_keys=True)
			# exit(1)

	import json
	with open(outfile, "w") as f:
		json.dump(outJSON, f,indent=4, sort_keys=True)

def runRappsipBaseStrategy(infile,runs, box=np.array([[-1,1],[-1,1]]),trainingScale="1x", roboptstrategy="ms",outfile="out.json",debug=0):

	X, Y = tools.readData(infile)
	outJSON = {}
	for r in runs:
		pdeg=r[0]
		qdeg=r[1]
		rappsip = RationalApproximationSIP(
										X,
										Y,
										m=pdeg,
										n=qdeg,
										trainingscale=trainingScale,
										roboptstrategy=roboptstrategy,
										box=box,
										strategy=0
		)
		outJSON["p%s_q%s"%(str(pdeg),str(qdeg))] = rappsip.asDict
		if(debug == 1):
			import json
			with open("/tmp/s0_latest.json", "w") as f:
				json.dump(outJSON, f,indent=4, sort_keys=True)

	import json
	with open(outfile, "w") as f:
		json.dump(outJSON, f,indent=4, sort_keys=True)

def runRappsipStrategy2(infile,runs, larr,l1strat="ho_p_q",box=np.array([[-1,1],[-1,1]]),trainingScale="0.5x",outfile="out.json",debug=0):

# l1strat="ho_p_q"
# l1strat="all_p_q"


	X, Y = tools.readData(infile)
	outJSON = {}

	# runs = [[2,2],[3,?3],[4,4],[5,5],[6,6]]
	for r in runs:
		for l in larr:
			pdeg=r[0]
			qdeg=r[1]
			if(l1strat == "ho_p_q"):
				ppenaltybin = np.ones(pdeg+1)
				ppenaltybin[pdeg] = 0

				qpenaltybin = np.ones(qdeg+1)
				qpenaltybin[qdeg] = 0
			elif(l1strat == "all_p_q"):
				ppenaltybin = np.zeros(pdeg+1)
				qpenaltybin = np.zeros(qdeg+1)


			rappsip = RationalApproximationSIP(
											X,
											Y,
											m=pdeg,
											n=qdeg,
											trainingscale=trainingScale,
											roboptstrategy="baron",
											box=box,
											strategy=2,
											penaltyparam=l,
				                            ppenaltybin=ppenaltybin.tolist(),
				                            qpenaltybin=qpenaltybin.tolist()

			)
			outJSON["p%s_q%s_%.E"%(str(pdeg),str(qdeg),l)] = rappsip.asDict
			if(debug == 1):
				import json
				with open("/tmp/s2_latest.json", "w") as f:
					json.dump(outJSON, f,indent=4, sort_keys=True)

	import json
	with open(outfile, "w") as f:
		json.dump(outJSON, f,indent=4, sort_keys=True)


def tableS0(jsonfile, testfile, runs):
	import json
	if jsonfile:
		with open(jsonfile, 'r') as fn:
			datastore = json.load(fn)

	X_test, Y_test = readData(testfile)
	karr = np.array([])
	aic = np.array([])
	bic = np.array([])
	X_l2 = np.array([])
	Z_testerr = np.array([])
	mn = np.array([])

	for r in runs:
		pdeg=r[0]
		qdeg=r[1]
		key = "p%s_q%s"%(str(pdeg),str(qdeg))
		iterationInfo = datastore[key]["iterationinfo"]
		lastii = iterationInfo[len(iterationInfo)-1]
		trainerr = lastii["leastSqObj"]
		X_l2 = np.append(X_l2,trainerr)

		rappsip = RationalApproximationSIP(datastore[key])
		Y_pred = rappsip(X_test)
		testerror = np.sum((Y_pred-Y_test)**2)
		Z_testerr = np.append(Z_testerr,testerror)

		k = 2
		pcoeff = datastore[key]["pcoeff"]
		qcoeff = datastore[key]["qcoeff"]
		maxp = abs(max(pcoeff, key=abs))
		maxq = abs(max(qcoeff, key=abs))
		# print(np.c_[pcoeff])
		# print(np.c_[qcoeff])
		# print(maxp,maxq)
		for pc in pcoeff:
			if(pc > 10**-2*maxp):
				k += 1
		for qc in qcoeff:
			if(qc > 10**-2*maxq):
				k += 1
		karr = np.append(karr,k)
		n = len(X_test)
		# AIC = 2k - 2log(L)
		# BIC = klog(n) - 2log(L)
		# -2log(L) becomes nlog(variance) = nlog(SSE/n) = nlog(testerror/n)
		a = 2*k + n*np.log(testerror/n)
		b = k*np.log(n) + n*np.log(testerror/n)

		aic = np.append(aic,a)
		bic = np.append(bic,b)
		mn = np.append(mn,rappsip.M+rappsip.N)

	sortedmnindex = np.argsort(mn)
	print("#\tpq\tl2 error\ttest err\tM+N\tnnz\taic\t\tbic")
	for i in sortedmnindex:
		r = runs[i]
		pdeg=r[0]
		qdeg=r[1]
		print("%d\tp%dq%d\t%f\t%f\t%d\t%d\t%f\t%f"%(i+1,pdeg,qdeg,X_l2[i],Z_testerr[i],mn[i],karr[i],aic[i],bic[i]))

	print("\nMIN\t\t%d\t\t%d\t\t%d\t%d\t\t%d\t\t%d\n"%(np.argmin(X_l2)+1,np.argmin(Z_testerr)+1,np.argmin(mn)+1,np.argmin(karr)+1,np.argmin(aic)+1,np.argmin(bic)+1))


def plotmntesterr(jsonfilearr, jsonfiledescrarr, testfile, runs, fno,folder):
	# LT, RT, LB, RB
	maxpq = np.amax(runs,axis=0)
	outfile1 = folder+"/"+fno+".299445.png"
	outfile2 = folder+"/"+fno+"_index.299445.png"

	X_test, Y_test = readData(testfile)
	testerractuals = {}
	testerrindex = {}
	for i in range(len(jsonfilearr)):
		jsonfile = jsonfilearr[i]
		import json
		if jsonfile:
			with open(jsonfile, 'r') as fn:
				datastore = json.load(fn)
		testerrarr = np.zeros(shape=(maxpq[0],maxpq[1]),dtype=np.float64)
		for r in runs:
			pdeg=r[0]
			qdeg=r[1]
			key = "p%s_q%s"%(str(pdeg),str(qdeg))
			print(key)
			# iterationInfo = datastore[key]["iterationinfo"]
			# lastii = iterationInfo[len(iterationInfo)-1]

			rappsip = RationalApproximationSIP(datastore[key])
			Y_pred = rappsip(X_test)
			testerror = np.average((Y_pred-Y_test)**2)
			testerrarr[pdeg-1][qdeg-1] = testerror


		testerractuals[i] = testerrarr
		sortedindexarr = np.argsort(-testerrarr,axis=None)[::-1].argsort()
		sortedindexarr = np.reshape(sortedindexarr,(maxpq[0],maxpq[1]))
		testerrindex[i] = sortedindexarr

		print(testerrarr)
		print(sortedindexarr)
		print(np.argmin(testerrarr), np.min(testerrarr), np.max(testerrarr))

	import matplotlib as mpl
	import matplotlib.pyplot as plt
	mpl.rc('text', usetex = True)
	mpl.rc('font', family = 'serif', size=12)
	mpl.style.use("ggplot")
	cmapname   = 'viridis'
	# X,Y = np.meshgrid(range(1,maxpq[0]+1), range(1,maxpq[1]+1))
	X,Y = np.meshgrid(range(1,maxpq[1]+1), range(1,maxpq[0]+1))
	f, axarr = plt.subplots(2,2, sharex=True, sharey=True, figsize=(15,15))
	f.suptitle(fno + " -- log(test error)", fontsize = 28)
	markersize = 1000
	vmin = -6
	vmax = -1

	for i in range(2):
		for j in range(2):
			testerrarr = testerractuals[i*2+j]
			sc = axarr[i][j].scatter(X,Y, marker = 's', s=markersize, c = np.ma.log10(testerrarr), cmap = cmapname, vmin=vmin, vmax=vmax, alpha = 1)
			axarr[i][j].set_title(jsonfiledescrarr[i*2+j], fontsize = 28)

	for ax in axarr.flat:
		ax.set(xlim=(0,maxpq[1]+1),ylim=(0,maxpq[0]+1))
		ax.tick_params(axis = 'both', which = 'major', labelsize = 18)
		ax.tick_params(axis = 'both', which = 'minor', labelsize = 18)
		ax.set_xlabel('$n$', fontsize = 22)
		ax.set_ylabel('$m$', fontsize = 22)
	for ax in axarr.flat:
		ax.label_outer()
	b=f.colorbar(sc,ax=axarr.ravel().tolist(), shrink=0.95)

    # b.set_label("Error = $log_{10}\\left(\\frac{\\left|\\left|f - \\frac{p^m}{q^n}\\right|\\right|_%i}{%i}\\right)$"%(norm,testSize), fontsize = 28)

	plt.savefig(outfile1)

	import matplotlib as mpl
	import matplotlib.pyplot as plt
	mpl.rc('text', usetex = True)
	mpl.rc('font', family = 'serif', size=12)
	mpl.style.use("ggplot")
	cmapname   = 'viridis'
	X,Y = np.meshgrid(range(1,maxpq[1]+1), range(1,maxpq[0]+1))
	f, axarr = plt.subplots(2,2, sharex=True, sharey=True, figsize=(15,15))
	f.suptitle(fno + " -- ordered enumeration of test error", fontsize = 28)
	markersize = 1000
	vmin = 0
	vmax = maxpq[0] * maxpq[1]

	for i in range(2):
		for j in range(2):
			sortedindexarr = testerrindex[i*2+j]
			sc = axarr[i][j].scatter(X,Y, marker = 's', s=markersize, c = sortedindexarr, cmap = cmapname, vmin=vmin, vmax=vmax, alpha = 1)
			axarr[i][j].set_title(jsonfiledescrarr[i*2+j], fontsize = 28)

	for ax in axarr.flat:
		ax.set(xlim=(0,maxpq[1]+1),ylim=(0,maxpq[0]+1))
		ax.tick_params(axis = 'both', which = 'major', labelsize = 18)
		ax.tick_params(axis = 'both', which = 'minor', labelsize = 18)
		ax.set_xlabel('$n$', fontsize = 22)
		ax.set_ylabel('$m$', fontsize = 22)
	for ax in axarr.flat:
		ax.label_outer()
	b=f.colorbar(sc,ax=axarr.ravel().tolist(), shrink=0.95)

    # b.set_label("Error = $log_{10}\\left(\\frac{\\left|\\left|f - \\frac{p^m}{q^n}\\right|\\right|_%i}{%i}\\right)$"%(norm,testSize), fontsize = 28)

	plt.savefig(outfile2)





def tableS2(jsonfile, testfile, runs, larr):
	import json
	# Lcurve
	if jsonfile:
		with open(jsonfile, 'r') as fn:
			datastore = json.load(fn)

	X_test, Y_test = readData(testfile)

	# import matplotlib as mpl
	# import matplotlib.pyplot as plt
	# mpl.rc('text', usetex = True)
	# mpl.rc('font', family = 'serif', size=12)
	# mpl.style.use("ggplot")
	# cmapname   = 'viridis'
	#
	# f, axarr = plt.subplots(4,4, figsize=(15,15))
	# markersize = 1000
	# vmin = -4
	# vmax = 2.5

	mintesterrArr = np.array([])
	minaic = np.array([])
	minbic = np.array([])
	minparam = np.array([])
	minnnz = np.array([])
	minmn = np.array([])


	for r in runs:
		pdeg=r[0]
		qdeg=r[1]
		Y_l1 = np.array([])
		X_l2 = np.array([])
		Z_testerr = np.array([])
		karr = np.array([])
		aic = np.array([])
		bic = np.array([])
		mn = np.array([])
		param = np.array([])
		for l in larr:
			key = "p%s_q%s_%.E"%(str(pdeg),str(qdeg),l)
			iterationInfo = datastore[key]["iterationinfo"]
			lastii = iterationInfo[len(iterationInfo)-1]
			regerr = lastii["leastSqSplit"]["l1term"]
			trainerr = lastii["leastSqSplit"]["l2term"]
			X_l2 = np.append(X_l2,trainerr)
			Y_l1 = np.append(Y_l1,regerr)

			rappsip = RationalApproximationSIP(datastore[key])
			Y_pred = rappsip(X_test)
			testerror = np.sum((Y_pred-Y_test)**2)
			Z_testerr = np.append(Z_testerr,testerror)
			k = 2
			pcoeff = datastore[key]["pcoeff"]
			qcoeff = datastore[key]["qcoeff"]
			maxp = abs(max(pcoeff, key=abs))
			maxq = abs(max(qcoeff, key=abs))
			# print(np.c_[pcoeff])
			# print(np.c_[qcoeff])
			# print(maxp,maxq)
			for pc in pcoeff:
				if(pc > 10**-2*maxp):
					k += 1
			for qc in qcoeff:
				if(qc > 10**-2*maxq):
					k += 1


			karr = np.append(karr,k)
			n = len(X_test)
			# AIC = 2k - 2log(L)
			# BIC = klog(n) - 2log(L)
			# -2log(L) becomes nlog(variance) = nlog(SSE/n) = nlog(testerror/n)
			a = 2*k + n*np.log(testerror/n)
			b = k*np.log(n) + n*np.log(testerror/n)

			aic = np.append(aic,a)
			bic = np.append(bic,b)

			param = np.append(param,l)
			mn = np.append(mn,rappsip.M+rappsip.N)

		print("p = "+str(pdeg)+"; q = "+str(qdeg))
		print("#\tl2 error\tl1 error\ttest err\tnnz\taic\t\tbic")
		for i in range(len(larr)):
			print("%d\t%f\t%f\t%f\t%d\t%f\t%f"%(i+1,X_l2[i],Y_l1[i],Z_testerr[i],karr[i], aic[i],bic[i]))
		print("\nMIN\t%d\t\t%d\t\t%d\t\t%d\t\t%d\t\t%d\n"%(np.argmin(X_l2)+1,np.argmin(Y_l1)+1,np.argmin(Z_testerr)+1,np.argmin(karr)+1,np.argmin(aic)+1,np.argmin(bic)+1))




		# axarr[pdeg-2][qdeg-2].plot(X_l2, Y_l1, '-rD')
		# axarr[pdeg-2][qdeg-2].set_title("p = "+str(pdeg)+"; q = "+str(qdeg))

		# if min arg of aic, bic and test err match, then take that and put int min arrays
		minindexarr = [np.argmin(Z_testerr),np.argmin(aic),np.argmin(bic)]
		if all(x == minindexarr[0] for x in minindexarr):
			mintesterrArr = np.append(mintesterrArr,np.min(Z_testerr))
			minaic = np.append(minaic,np.min(aic))
			minbic = np.append(minbic,np.min(bic))
			minparam = np.append(minparam,param[minindexarr[0]])
			minnnz  = np.append(minnnz,karr[minindexarr[0]])
			minmn = np.append(minmn,mn[minindexarr[0]])
		# 2 elements match
		elif len(set(arr)) == 2:
			# find the 2 mathcing elements and take values from all arrays at that index
			if minindexarr[0]==minindexarr[1] or minindexarr[0]==minindexarr[2]:
				mintesterrArr = np.append(mintesterrArr,Z_testerr[minindexarr[0]])
				minaic = np.append(minaic,aic[minindexarr[0]])
				minbic = np.append(minbic,bic[minindexarr[0]])
				minparam = np.append(minparam,param[minindexarr[0]])
				minnnz  = np.append(minnnz,karr[minindexarr[0]])
				minmn = np.append(minmn,mn[minindexarr[0]])
			elif minindexarr[1]==minindexarr[2]:
				mintesterrArr = np.append(mintesterrArr,Z_testerr[minindexarr[1]])
				minaic = np.append(minaic,aic[minindexarr[1]])
				minbic = np.append(minbic,bic[minindexarr[1]])
				minparam = np.append(minparam,param[minindexarr[1]])
				minnnz  = np.append(minnnz,karr[minindexarr[1]])
				minmn = np.append(minmn,mn[minindexarr[1]])
		# no elements match. Highly unlikely that we will be here
		else:
			#take the case where test arr is minimum
			mintesterrArr = np.append(mintesterrArr,Z_testerr[minindexarr[0]])
			minaic = np.append(minaic,aic[minindexarr[0]])
			minbic = np.append(minbic,bic[minindexarr[0]])
			minparam = np.append(minparam,param[minindexarr[0]])
			minnnz  = np.append(minnnz,karr[minindexarr[0]])
			minmn = np.append(minmn,mn[minindexarr[0]])


	print("#\tpq\ttesterr\t\tM+N\tNNZ\taic\t\tbic\t\tlambda")
	for i in range(len(runs)):
		pdeg = runs[i][0]
		qdeg = runs[i][1]
		print("%d\tp%dq%d\t%f\t%d\t%d\t%f\t%f\t%.2E"%(i+1,pdeg,qdeg,mintesterrArr[i],minmn[i],minnnz[i],minaic[i],minbic[i],minparam[i]))

	print("\n")

	sortedmnindex = np.argsort(minmn)
	print("#\tpq\ttesterr\t\tM+N\tNNZ\taic\t\tbic\t\tlambda")
	for i in sortedmnindex:
		pdeg = runs[i][0]
		qdeg = runs[i][1]
		print("%d\tp%dq%d\t%f\t%d\t%d\t%f\t%f\t%.2E"%(i+1,pdeg,qdeg,mintesterrArr[i],minmn[i],minnnz[i],minaic[i],minbic[i],minparam[i]))

	print("\nMIN\t\t%d\t\t%d\t%d\t%d\t\t%d\n"%(np.argmin(mintesterrArr)+1,np.argmin(minmn)+1,np.argmin(minnnz)+1,np.argmin(minaic)+1,np.argmin(minbic)+1))


	# for ax in axarr.flat:
	# 	# ax.set(xlim=(-6,4))
	# 	if(ax.is_first_col()):
	# 		ax.set_ylabel("L1 error", fontsize = 15)
	# 	if(ax.is_last_row()):
	# 		ax.set_xlabel("L2 error", fontsize = 15)
	# # plt.show()



	# P 0,1,2,3,5


def prettyPrint(cvjsonfile,jsonfile, testfile):
	import json
	# if cvjsonfile:
	# 	with open(cvjsonfile, 'r') as fn:
	# 		datastore = json.load(fn)
	#
	#
	# keylist = datastore.keys()
	# keylist.sort()
	# s=""
	# s = "pq deg\tcparam\tparam\tl2term\t\tl1term\n\n"
	# for key in keylist:
	#
	# 	iterationInfo = datastore[key]['min']["iterationinfo"]
	# 	lsqsplit = iterationInfo[len(iterationInfo)-1]["leastSqSplit"]
	# 	s += "%s\tmin\t%.0E\t%f\t%f\n"%(key,datastore[key]['minl'],lsqsplit['l2term'],lsqsplit['l1term'])
	#
	# 	iterationInfo = datastore[key]['min plus SE']["iterationinfo"]
	# 	lsqsplit = iterationInfo[len(iterationInfo)-1]["leastSqSplit"]
	# 	s += "%s\tmpse\t%.0E\t%f\t%f\n"%(key,datastore[key]['mpsel'],lsqsplit['l2term'],lsqsplit['l1term'])
	# 	s+="\naverage error\n"
	#
	#
	# 	avgerror =  datastore[key]['avgerror']
	# 	larr = np.array([10**i for i in range(3,-13,-1)])
	# 	# for i in larr:
	# 	# 	s += "%.1E\t"%(i)
	# 	s+="\n"
	# 	for i in avgerror:
	# 		s += "%.4E\t"%(i)
	# 	s+="\n\n"
	#



	X_test, Y_test = readData(testfile)



	# static for f8 and upto p4 and q4

	# s+= "p coeffs obtained for lambda with minimum avg CV error\n"
	# s+="origfn\t"
	# for key in keylist:
	# 	s+="%s\t\t"%(key)
	# s+="\n"
	# # P 0,1,2,3,5
	# pcoeffO = [-1,-1,1,1,0,1]
	# for i in range(15):
	# 	if(i <= 3 or i == 5):
	# 		s+= "%d\t"%(pcoeffO[i])
	# 	else:
	# 		s+="\t"
	# 	for key in keylist:
	# 		pcoeff = datastore[key]['min']["pcoeff"]
	# 		if(i<len(pcoeff)):
	# 			s+="%f\t"%(pcoeff[i])
	# 		else: s+="\t\t"
	# 	s+="\n"
	#
	# s+= "q coeffs obtained for lambda with minimum avg CV error\n"
	# s+="origfn\t"
	# for key in keylist:
	# 	s+="%s\t\t"%(key)
	# s+="\n"
	# qcoeffO = [1.21,-1.1,-1.1,0,1,0]
	# # Q 0,1,2,3,5
	# for i in range(15):
	# 	if(i <= 2 or i == 4):
	# 		s+= "%.2f\t"%(qcoeffO[i])
	# 	else:
	# 		s+="\t"
	# 	for key in keylist:
	# 		qcoeff = datastore[key]['min']["qcoeff"]
	# 		if(i < len(qcoeff)):
	# 			s+="%f\t"%(qcoeff[i])
	# 		else: s+="\t\t"
	# 	s+="\n"
	# s+="\n"
	#

	# f8
	# pcoeffO = [-1,-1,1,1,0,1,0,0,0,0,0,0,0,0,0,0]
	# qcoeffO = [1.21,-1.1,-1.1,0,1,0,0,0,0,0,0,0,0,0,0,0]

	# f12
	pcoeffO = [-1,-1,1,1,0,1,0,0,0,0,0,0,0,0,0,0]
	qcoeffO = [4,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0]


	# for key in keylist:
	# 	s+="\t%s\t"%(key)
	# s+="\n"
	#
	# testerrarr = np.array([])
	# s+= "testErr\t"
	# for key in keylist:
	# 	rappsip = RationalApproximationSIP(datastore[key]['min'])
	# 	Y_pred = rappsip(X_test)
	# 	# print(np.c_[Y_pred,Y_test,abs(Y_pred-Y_test)])
	# 	error = np.average(abs(Y_pred-Y_test))
	# 	testerrarr = np.append(testerrarr,error)
	# 	s += "%.8f\t"%(error)
	# s+="\n"
	# trainerrarr = np.array([])
	# s+= "l2term\t"
	# for key in keylist:
	# 	iterationInfo = datastore[key]['min']["iterationinfo"]
	# 	lsqsplit = iterationInfo[len(iterationInfo)-1]["leastSqSplit"]
	# 	trainerrarr = np.append(trainerrarr,lsqsplit['l2term'])
	# 	s += "%f\t"%(lsqsplit['l2term'])
	# s+="\n"
	# s+= "l1term\t"
	# for key in keylist:
	# 	iterationInfo = datastore[key]['min']["iterationinfo"]
	# 	lsqsplit = iterationInfo[len(iterationInfo)-1]["leastSqSplit"]
	# 	s += "%f\t"%(lsqsplit['l1term'])
	# s+="\n"
	# s+= "param\t"
	# for key in keylist:
	# 	s += "%.E\t\t"%(datastore[key]['minl'])
	# s+="\n\n"
	#
	# s+="Min testing error was at %s with value %f.\n"%(keylist[np.argmin(testerrarr)],np.min(testerrarr))
	# s+="Min training error was at %s with value %f.\n"%(keylist[np.argmin(trainerrarr)],np.min(trainerrarr))
	#
	# print(s)

	if jsonfile:
		with open(jsonfile, 'r') as fn:
			datastore = json.load(fn)


	keylist = datastore.keys()
	keylist.sort()

	s=""

	s+= "p coeffs obtained \n"
	s+="origfn\t"
	for key in keylist:
		s+="%s\t\t"%(key)
	s+="\n"
	# P 0,1,2,3,5

	for i in range(28):
		if(i>=len(pcoeffO) or pcoeffO[i] == 0):
			s+= "\t"
		else:
			s+= "%d\t"%(pcoeffO[i])
		for key in keylist:
			pcoeff = datastore[key]["pcoeff"]
			if(i<len(pcoeff)):
				s+="%f\t"%(pcoeff[i])
			else: s+="\t\t"
		s+="\n"

	s+= "q coeffs obtained \n"
	s+="origfn\t"
	for key in keylist:
		s+="%s\t\t"%(key)
	s+="\n"

	# Q 0,1,2,3,5
	for i in range(28):
		if(i>=len(qcoeffO) or qcoeffO[i] == 0):
			s+= "\t"
		else:
			s+= "%.2f\t"%(qcoeffO[i])
		for key in keylist:
			qcoeff = datastore[key]["qcoeff"]
			if(i < len(qcoeff)):
				s+="%f\t"%(qcoeff[i])
			else: s+="\t\t"
		s+="\n"
	s+="\n"

	for key in keylist:
		s+="\t%s\t"%(key)
	s+="\n"

	testerrarr = np.array([])
	s+= "testErr\t"
	for key in keylist:
		# print(datastore[key])
		rappsip = RationalApproximationSIP(datastore[key])
		Y_pred = rappsip(X_test)
		# print(np.c_[Y_pred,Y_test,abs(Y_pred-Y_test)])
		# print(np.c_[Y_pred,Y_test])
		error = np.average(abs(Y_pred-Y_test))
		testerrarr = np.append(testerrarr,error)
		s += "%.8f\t"%(error)
	s+="\n"
	trainerrarr = np.array([])
	s+= "l2term\t"
	for key in keylist:
		iterationInfo = datastore[key]["iterationinfo"]
		lastii = iterationInfo[len(iterationInfo)-1]
		trainerr = 0
		if lastii.get("leastSqSplit") is not None:
			trainerr = lastii["leastSqSplit"]["l2term"]
		else:
			trainerr = lastii["leastSqObj"]
		trainerrarr = np.append(trainerrarr,trainerr)
		s += "%f\t"%(trainerr)
	s+="\n"

	regerrarr = np.array([])
	s+= "l1term\t"
	for key in keylist:
		iterationInfo = datastore[key]["iterationinfo"]
		lastii = iterationInfo[len(iterationInfo)-1]
		if lastii.get("leastSqSplit") is not None:
			regerr = lastii["leastSqSplit"]["l1term"]
			regerrarr = np.append(regerrarr,regerr)
			s += "%f\t"%(regerr)
		else:
			s += "\t"
	s+="\n\n"


	s+="Min testing error was at %s with value %f.\n"%(keylist[np.argmin(testerrarr)],np.min(testerrarr))
	s+="Min training error was at %s with value %f.\n"%(keylist[np.argmin(trainerrarr)],np.min(trainerrarr))
	if(len(regerrarr)>0):
		s+="Min Regularization error was at %s with value %f.\n"%(keylist[np.argmin(regerrarr)],np.min(regerrarr))

	print(s)


infilePath = "../f8_noisepct10-3.txt"

cvoutfile = "test/f8_noisepct10-3_cv_out.299445.json"
s0outfile = "test/f8_noisepct10-3_s0_out.299445.json"
testfile8 = "../f8_test.txt"

box = np.array([[-1,1],[-1,1]])
debug = 1
infilePathNN = "../f8.txt"
s0outfileNN = "test/f8_s0_out.299445.json"

infilePath10_10_1 = "../f10_noisepct10-1.txt"
infilePath10_10_3 = "../f10_noisepct10-3.txt"
s0outfile10 = "test/f10_noisepct10-1_s0_out.299445.json"
s0outfile10_1x_10_1 = "test/f10_noisepct10-1_s0_out_1x.299445.json"
s0outfile10_2x_10_1 = "test/f10_noisepct10-1_s0_out_2x.299445.json"
s0outfile10_1x_10_3 = "test/f10_noisepct10-3_s0_out_1x.299445.json"
s0outfile10_2x_10_3 = "test/f10_noisepct10-3_s0_out_2x.299445.json"
testfile10 = "../f10_test.txt"

infilePath12_10_1 = "../f12_noisepct10-1.txt"
infilePath12_10_3 = "../f12_noisepct10-3.txt"
s0outfile12 = "test/f12_noisepct10-1_s0_out.299445.json"
s0outfile12_1x_10_1 = "test/f12_noisepct10-1_s0_out_1x.299445.json"
s0outfile12_2x_10_1 = "test/f12_noisepct10-1_s0_out_2x.299445.json"
s0outfile12_1x_10_3 = "test/f12_noisepct10-3_s0_out_1x.299445.json"
s0outfile12_2x_10_3 = "test/f12_noisepct10-3_s0_out_2x.299445.json"
testfile12 = "../f12_test.txt"

infilePath13_10_1 = "../f13_noisepct10-1.txt"
infilePath13_10_3 = "../f13_noisepct10-3.txt"
s0outfile13 = "test/f13_noisepct10-1_s0_out.299445.json"
s0outfile13_1x_10_1 = "test/f13_noisepct10-1_s0_out_1x.299445.json"
s0outfile13_2x_10_1 = "test/f13_noisepct10-1_s0_out_2x.299445.json"
s0outfile13_1x_10_3 = "test/f13_noisepct10-3_s0_out_1x.299445.json"
s0outfile13_2x_10_3 = "test/f13_noisepct10-3_s0_out_2x.299445.json"
testfile13 = "../f13_test.txt"

infilePath14_10_1 = "../f14_noisepct10-1.txt"
infilePath14_10_3 = "../f14_noisepct10-3.txt"
s0outfile14 = "test/f14_noisepct10-1_s0_out.299445.json"
s0outfile14_1x_10_1 = "test/f14_noisepct10-1_s0_out_1x.299445.json"
s0outfile14_2x_10_1 = "test/f14_noisepct10-1_s0_out_2x.299445.json"
s0outfile14_1x_10_3 = "test/f14_noisepct10-3_s0_out_1x.299445.json"
s0outfile14_2x_10_3 = "test/f14_noisepct10-3_s0_out_2x.299445.json"
testfile14 = "../f14_test.txt"

infilePath15_10_1 = "../f15_noisepct10-1.txt"
infilePath15_10_3 = "../f15_noisepct10-3.txt"
s0outfile15 = "test/f15_noisepct10-1_s0_out.299445.json"
s0outfile15_1x_10_1 = "test/f15_noisepct10-1_s0_out_1x.299445.json"
s0outfile15_2x_10_1 = "test/f15_noisepct10-1_s0_out_2x.299445.json"
s0outfile15_1x_10_3 = "test/f15_noisepct10-3_s0_out_1x.299445.json"
s0outfile15_2x_10_3 = "test/f15_noisepct10-3_s0_out_2x.299445.json"
testfile15 = "../f15_test.txt"

infilePath16_10_1 = "../f16_noisepct10-1.txt"
infilePath16_10_3 = "../f16_noisepct10-3.txt"
s0outfile16 = "test/f16_noisepct10-1_s0_out.299445.json"
s0outfile16_1x_10_1 = "test/f16_noisepct10-1_s0_out_1x.299445.json"
s0outfile16_2x_10_1 = "test/f16_noisepct10-1_s0_out_2x.299445.json"
s0outfile16_1x_10_3 = "test/f16_noisepct10-3_s0_out_1x.299445.json"
s0outfile16_2x_10_3 = "test/f16_noisepct10-3_s0_out_2x.299445.json"
testfile16 = "../f16_test.txt"

infilePath17_10_1 = "../f17_noisepct10-1.txt"
infilePath17_10_3 = "../f17_noisepct10-3.txt"
s0outfile17 = "test/f17_noisepct10-1_s0_out.299445.json"
s0outfile17_1x_10_1 = "test/f17_noisepct10-1_s0_out_1x.299445.json"
s0outfile17_2x_10_1 = "test/f17_noisepct10-1_s0_out_2x.299445.json"
s0outfile17_1x_10_3 = "test/f17_noisepct10-3_s0_out_1x.299445.json"
s0outfile17_2x_10_3 = "test/f17_noisepct10-3_s0_out_2x.299445.json"
testfile17 = "../f17_test.txt"

infilePath18_10_1 = "../f18_noisepct10-1.txt"
infilePath18_10_3 = "../f18_noisepct10-3.txt"
s0outfile18 = "test/f18_noisepct10-1_s0_out.299445.json"
s0outfile18_1x_10_1 = "test/f18_noisepct10-1_s0_out_1x.299445.json"
s0outfile18_2x_10_1 = "test/f18_noisepct10-1_s0_out_2x.299445.json"
s0outfile18_1x_10_3 = "test/f18_noisepct10-3_s0_out_1x.299445.json"
s0outfile18_2x_10_3 = "test/f18_noisepct10-3_s0_out_2x.299445.json"
testfile18 = "../f18_test.txt"

infilePath19_10_1 = "../f19_noisepct10-1.txt"
infilePath19_10_3 = "../f19_noisepct10-3.txt"
s0outfile19 = "test/f19_noisepct10-1_s0_out.299445.json"
s0outfile19_1x_10_1 = "test/f19_noisepct10-1_s0_out_1x.299445.json"
s0outfile19_2x_10_1 = "test/f19_noisepct10-1_s0_out_2x.299445.json"
s0outfile19_1x_10_3 = "test/f19_noisepct10-3_s0_out_1x.299445.json"
s0outfile19_2x_10_3 = "test/f19_noisepct10-3_s0_out_2x.299445.json"
testfile19 = "../f19_test.txt"

# runs = [[2,2],[3,3],[4,4],[5,5]]
runs2D = []
for i in range(1,7):
	for j in range(1,7):
		runs2D.append([i,j])

runs3D = []
for i in range(1,7):
	for j in range(1,7):
		constantpluslinear = 4
		if(tools.numCoeffsPoly(3, j)-constantpluslinear<=50):
			runs3D.append([i,j])

runs4D = []
for i in range(1,7):
	for j in range(1,7):
		constantpluslinear = 5
		if(tools.numCoeffsPoly(4, j)-constantpluslinear<=50):
			runs4D.append([i,j])

box17 = np.array([[80,100],[5, 10],[90, 93]])
box18 = np.array([[-0.95,0.95],[-0.95,0.95],[-0.95,0.95],[-0.95,0.95]])
box19 = np.array([[-1,1],[-1,1],[-1,1],[-1,1]])

larr = np.array([10**i for i in range(2,-8,-1)])

roboptstrategy = "ss_ms_ba"

# runs = [[6,3],[7,3],[7,4],[7,5],[7,6],[7,7]]
# larr = np.array([10**i for i in np.linspace(3,-8,23)])


# runCrossValidation(infilePath,box,cvoutfile,debug)

# runRappsipBaseStrategy(infilePath12,runs2D, box,"1x",s0outfile12,debug)
# tableS0(s0outfile12,testfile12,runs2D)
#
# runRappsipBaseStrategy(infilePath13,runs2D, box,"1x",s0outfile13,debug)
# tableS0(s0outfile13,testfile13,runs2D)
#
# runRappsipBaseStrategy(infilePath14,runs2D, box,"1x",s0outfile14,debug)
# tableS0(s0outfile14,testfile14,runs2D)
#
#
# runRappsipBaseStrategy(infilePath15,runs2D, box,"1x",s0outfile15,debug)
# tableS0(s0outfile15,testfile15,runs2D)
#
# runRappsipBaseStrategy(infilePath16,runs2D, box,"1x",s0outfile16,debug)
# tableS0(s0outfile16,testfile16,runs2D)

# runRappsipStrategy2(infilePath12, runs2D, larr,"all_p_q", box,".5x",s2outfile12,debug)
# runRappsipStrategy2(infilePath13, runs2D, larr,"all_p_q", box,"0.5x",s2outfile13,debug)
# runRappsipStrategy2(infilePath12, runs2D, larr,"ho_p_q", box,"1x",s2outfile12,debug)
# tableS0(s2outfile12,testfile12,runs2D,larr)
# runRappsipStrategy2(infilePath13, runs2D, larr,"ho_p_q", box,"1x",s2outfile13,debug)
# tableS0(s2outfile13,testfile13,runs2D,larr)
# runRappsipStrategy2(infilePath14, runs2D, larr,"ho_p_q", box,"1x",s2outfile14,debug)
# runRappsipStrategy2(infilePath13, runs2D, larr,"all_p_q", box,"0.5x",s2outfile13,debug)
# tableS0(s2outfile13,testfile13,runs2D,larr)

# prettyPrint(cvoutfile,s2outfile12,testfile12)

# runRappsipBaseStrategy(infilePath12_10_1, runs2D, box, "1x", roboptstrategy, s0outfile12_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath12_10_1, runs2D, box, "2x", roboptstrategy, s0outfile12_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath12_10_3, runs2D, box, "1x", roboptstrategy, s0outfile12_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath12_10_3, runs2D, box, "2x", roboptstrategy, s0outfile12_2x_10_3,debug=1)
# plotmntesterr([s0outfile12_1x_10_1,s0outfile12_2x_10_1,s0outfile12_1x_10_3,s0outfile12_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile12, runs2D, "f12","test")
#
# runRappsipBaseStrategy(infilePath13_10_1, runs2D, box, "1x", roboptstrategy, s0outfile13_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath13_10_1, runs2D, box, "2x", roboptstrategy, s0outfile13_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath13_10_3, runs2D, box, "1x", roboptstrategy, s0outfile13_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath13_10_3, runs2D, box, "2x", roboptstrategy, s0outfile13_2x_10_3,debug=1)
# plotmntesterr([s0outfile13_1x_10_1,s0outfile13_2x_10_1,s0outfile13_1x_10_3,s0outfile13_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile13, runs2D, "f13","test")
#
# runRappsipBaseStrategy(infilePath14_10_1, runs2D, box, "1x", roboptstrategy, s0outfile14_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath14_10_1, runs2D, box, "2x", roboptstrategy, s0outfile14_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath14_10_3, runs2D, box, "1x", roboptstrategy, s0outfile14_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath14_10_3, runs2D, box, "2x", roboptstrategy, s0outfile14_2x_10_3,debug=1)
# plotmntesterr([s0outfile14_1x_10_1,s0outfile14_2x_10_1,s0outfile14_1x_10_3,s0outfile14_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile14, runs2D, "f14","test")
#
# runRappsipBaseStrategy(infilePath15_10_1, runs2D, box, "1x", roboptstrategy, s0outfile15_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath15_10_1, runs2D, box, "2x", roboptstrategy, s0outfile15_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath15_10_3, runs2D, box, "1x", roboptstrategy, s0outfile15_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath15_10_3, runs2D, box, "2x", roboptstrategy, s0outfile15_2x_10_3,debug=1)
# plotmntesterr([s0outfile15_1x_10_1,s0outfile15_2x_10_1,s0outfile15_1x_10_3,s0outfile15_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile15, runs2D, "f15","test")
#
# runRappsipBaseStrategy(infilePath16_10_1, runs2D, box, "1x", roboptstrategy, s0outfile16_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath16_10_1, runs2D, box, "2x", roboptstrategy, s0outfile16_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath16_10_3, runs2D, box, "1x", roboptstrategy, s0outfile16_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath16_10_3, runs2D, box, "2x", roboptstrategy, s0outfile16_2x_10_3,debug=1)
# plotmntesterr([s0outfile16_1x_10_1,s0outfile16_2x_10_1,s0outfile16_1x_10_3,s0outfile16_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile16, runs2D, "f16","test")

# runRappsipBaseStrategy(infilePath17_10_1, runs3D, box17, "1x", roboptstrategy, s0outfile17_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath17_10_1, runs3D, box17, "2x", roboptstrategy, s0outfile17_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath17_10_3, runs3D, box17, "1x", roboptstrategy, s0outfile17_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath17_10_3, runs3D, box17, "2x", roboptstrategy, s0outfile17_2x_10_3,debug=1)
# plotmntesterr([s0outfile17_1x_10_1,s0outfile17_2x_10_1,s0outfile17_1x_10_3,s0outfile17_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile17, runs3D, "f17","test")


# runRappsipBaseStrategy(infilePath18_10_1, runs4D, box18, "1x", roboptstrategy, s0outfile18_1x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath18_10_1, runs4D, box18, "2x", roboptstrategy, s0outfile18_2x_10_1,debug=1)
# runRappsipBaseStrategy(infilePath18_10_3, runs4D, box18, "1x", roboptstrategy, s0outfile18_1x_10_3,debug=1)
# runRappsipBaseStrategy(infilePath18_10_3, runs4D, box18, "2x", roboptstrategy, s0outfile18_2x_10_3,debug=1)
# plotmntesterr([s0outfile18_1x_10_1,s0outfile18_2x_10_1,s0outfile18_1x_10_3,s0outfile18_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile18, runs4D, "f18","test")


# runRappsipBaseStrategy(infilePath10_10_1, runs4D, box19, "1x", roboptstrategy, s0outfile10_1x_10_1,debug=1)

runRappsipBaseStrategy(infilePath19_10_1, runs4D, box19, "1x", roboptstrategy, s0outfile19_1x_10_1,debug=1)
runRappsipBaseStrategy(infilePath19_10_1, runs4D, box19, "2x", roboptstrategy, s0outfile19_2x_10_1,debug=1)
runRappsipBaseStrategy(infilePath19_10_3, runs4D, box19, "1x", roboptstrategy, s0outfile19_1x_10_3,debug=1)
runRappsipBaseStrategy(infilePath19_10_3, runs4D, box19, "2x", roboptstrategy, s0outfile19_2x_10_3,debug=1)
plotmntesterr([s0outfile19_1x_10_1,s0outfile19_2x_10_1,s0outfile19_1x_10_3,s0outfile19_2x_10_3], ["e=10-1, 1x","e=10-1, 2x","e=10-3, 1x","e=10-3, 2x"], testfile19, runs4D, "f19","test")
#end
