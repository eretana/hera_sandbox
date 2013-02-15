#! /usr/bin/env python
import aipy as a, numpy as n, capo as C, pylab as p
import sys, optparse, os
from matplotlib import rc
rc('text',usetex=True)
rc('font', size=22)

class DataQuery:
    def __init__(self,fig,bls):
        self.x = 0
        self.y = 0
        self.cid = fig.canvas.mpl_connect('button_press_event',self)
    def __call__(self,event):
       try:
           self.y = event.ydata- 1
           line = n.floor(self.y)
           bl = bls[line]
           print a.miriad.bl2ij(bl)
       except(TypeError): pass

o = optparse.OptionParser()
o.add_option('--umax', type='float', default=n.Inf,
    help='Only show baselines shorter than this value')   
o.add_option('--umin', type='float', default=0.,
    help='Only show baselines longer than this value')   
a.scripting.add_standard_options(o,cal=True)
opts,args = o.parse_args(sys.argv[1:])

fq = .1525
aa = a.cal.get_aa(opts.cal, n.array([fq]))

magdict, wgtdict = {},{}
mags,bls,conj = [],[],[]
for npzfile in args:
    print 'Reading...', npzfile
    dat = n.load(npzfile)
    kpl = dat['kpl']
    keys = dat.files[:]
    keys.remove('kpl')

    for bl in keys:
        if bl[0] == 'w': continue
        wbl = 'w'+str(bl)
        i,j = a.miriad.bl2ij(bl)
        if i == 40 or j == 40: continue
        if i == 55 or j == 55: continue
        crd = aa.get_baseline(i,j)*fq
        mag = n.sqrt(crd[0]**2 + crd[1]**2)
        magdict[mag] = magdict.get(mag,0) + dat[bl]
        wgtdict[mag] = wgtdict.get(mag,0) + dat[wbl]
        mags.append(mag)
        bls.append(bl)
        if crd[0] < 0.:
            conj.append(1)
        else:
            conj.append(0)

mags,bls = n.unique(n.array(mags)),n.unique(n.array(bls))
inds = n.argsort(mags)
mags,bls,conj = n.take(mags,inds), n.take(bls,inds), n.take(conj,inds)
valid = n.where(mags > opts.umin, 1, 0) * n.where(mags < opts.umax, 1, 0)
mags,bls,conj = mags.compress(valid), bls.compress(valid), conj.compress(valid)

blmags = []
for bl in bls:
    i,j = a.miriad.bl2ij(bl)
    crd = aa.get_baseline(i,j)*fq
    mag = n.sqrt(crd[0]**2 + crd[1]**2)
    blmags.append(mag)

hi, bins = .14, 750
step = hi/bins
kprs = n.arange(0,hi,step)
half = len(kpl)/2

wfall = n.zeros((len(kprs),half))
wgtfall = n.zeros((len(kprs),half))
hors,phors = n.zeros_like(kprs),n.zeros_like(kprs)
for ind,mag in enumerate(mags):
    spec = magdict[mag] / wgtdict[mag]
    #conjugate [doesnt work]
    if conj[ind] == 1: 
         spec = spec[::-1]
    inds = n.argsort(kpl)
    spec = n.take(spec,inds)
    kpr = C.pspec.dk_du(C.pspec.f2z(fq))*mag
    kpr = n.round(kpr/(step))*(step)
    #calculate the horizon
    hor = C.pspec.dk_deta(C.pspec.f2z(fq))*(mag/fq)
    phor = C.pspec.dk_deta(C.pspec.f2z(fq))*((mag/fq)+50)
    line = n.where(kprs == kpr)[0]
    hors[line] = hor
    phors[line] = phor
    #fold over kpl = 0
    spec = (spec[0:half]+spec[half:][::-1])/2 
    wfall[line,:] += spec
    wgtfall[line,:] += n.ones_like(spec)
    #if line == 0: p.semilogy(kpl[inds],spec);p.show()

wfall[wgtfall>0] /= wgtfall[wgtfall>0]
kpl.sort()

fig = p.figure()
axis = fig.add_subplot(111)

wfall = wfall.T
#multiply by 2 for beam cludge
p.imshow(n.log10(2*n.abs(wfall)),aspect='auto',interpolation='nearest',extent=(0,kprs[-1],0,n.max(kpl)),vmin=11,vmax=15)
p.colorbar()

p.plot(kprs,hors,'.',lw=2,color='white')
p.plot(kprs,phors,'.',lw=2,color='orange')

query = DataQuery(fig,bls)

p.title(r'$P(k)\ [{\rm mK}^2 (h^{-1}{\rm Mpc})^{3}]$')
p.ylabel(r'$k_{\parallel}\ [h{\rm Mpc}^{-1}]$')
p.xlabel(r'$k_{\perp}\ [h{\rm Mpc}^{-1}]$')
p.ylim(0,.6)
p.show()
