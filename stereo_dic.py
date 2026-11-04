"""Image-only stereo correspondence, calibrated triangulation and surface strain.

No material properties, applied torque, deformation model or truth displacements
are accepted by this module. Camera calibration and support masks are known.
"""
from collections import Counter
import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import least_squares
from scipy.ndimage import binary_erosion,map_coordinates
from scipy.signal import correlate
from scipy.spatial import cKDTree


from image_preprocessing import prepare_images
from dic_support import supported_subset_centres


class ImageMatcher:
    def __init__(self,image,mask,subset):
        self.image=np.asarray(image,float);self.mask=binary_erosion(mask,iterations=3)
        self.integer_support=supported_subset_centres(self.mask,subset)
        self.spline=RectBivariateSpline(np.arange(image.shape[0]),np.arange(image.shape[1]),image)
        self.h=subset//2;y,x=np.mgrid[-self.h:self.h+1,-self.h:self.h+1];self.dx=x.ravel();self.dy=y.ravel()

    def supported(self,r,c):
        H,W=self.image.shape
        return (np.min(r)>=2 and np.max(r)<=H-3 and np.min(c)>=2 and np.max(c)<=W-3 and
                np.all(map_coordinates(self.mask.astype(float),[r,c],order=1,mode='constant',cval=0)>.999))

    def match(self,target,centre,radius,guess=None,epipolar=False):
        centre=np.asarray(centre,float);guess=centre if guess is None else np.asarray(guess,float)
        sr=centre[1]+self.dy;sc=centre[0]+self.dx
        if not self.supported(sr,sc):return None,'source_support'
        ref=self.spline.ev(sr,sc);ref-=ref.mean();norm=np.linalg.norm(ref)
        if norm/np.sqrt(ref.size)<.015:return None,'low_texture'
        ref/=norm;h=self.h;H,W=target.image.shape
        gx,gy=np.rint(guess).astype(int);ry=1 if epipolar else radius
        x0=max(h+2,gx-radius);x1=min(W-h-3,gx+radius)
        y0=max(h+2,gy-ry);y1=min(H-h-3,gy+ry)
        if x1<x0 or y1<y0:return None,'search_support'
        search=target.image[y0-h:y1+h+1,x0-h:x1+h+1];kernel=np.ones((2*h+1,2*h+1))
        sums=correlate(search,kernel,mode='valid',method='fft');sq=correlate(search*search,kernel,mode='valid',method='fft')
        numerator=correlate(search,ref.reshape(kernel.shape),mode='valid',method='fft')
        denom=np.sqrt(np.maximum(sq-sums*sums/ref.size,1e-14));scores=numerator/denom
        valid_windows=target.integer_support[y0:y1+1,x0:x1+1]
        if not valid_windows.any():return None,'target_support'
        scores=np.where(valid_windows,scores,-np.inf)
        row,col=np.unravel_index(np.argmax(scores),scores.shape)
        seed=np.array([x0+col-centre[0],y0+row-centre[1],0,0,0,0],float)
        offset=guess-centre;lower=np.r_[offset-radius-1,[-.35]*4];upper=np.r_[offset+radius+1,[.35]*4]
        cache={}
        def evaluate(p):
            if 'p' in cache and np.array_equal(p,cache['p']):return cache['res'],cache['jac']
            c=sc+p[0]+p[2]*self.dx+p[3]*self.dy;r=sr+p[1]+p[4]*self.dx+p[5]*self.dy
            values=target.spline.ev(r,c);g=values-values.mean();n=max(np.linalg.norm(g),1e-12)
            ir=target.spline.ev(r,c,dx=1,dy=0);ic=target.spline.ev(r,c,dx=0,dy=1)
            J=np.column_stack((ic,ir,ic*self.dx,ic*self.dy,ir*self.dx,ir*self.dy));J-=J.mean(axis=0)
            J=(J-g[:,None]*(g@J)[None,:]/n**2)/n
            residual=g/n-ref;cache.update(p=p.copy(),res=residual,jac=J)
            return residual,J
        fit=least_squares(lambda p:evaluate(p)[0],seed,jac=lambda p:evaluate(p)[1],bounds=(lower,upper),x_scale='jac',max_nfev=60,ftol=1e-7,xtol=1e-7,gtol=1e-8)
        p=fit.x;zncc=1-float(fit.fun@fit.fun)/2
        if not fit.success:return None,'optimizer'
        if zncc<.85:return None,'low_correlation'
        if np.any(p-lower<.01*(upper-lower)) or np.any(upper-p<.01*(upper-lower)):return None,'parameter_bound'
        c=sc+p[0]+p[2]*self.dx+p[3]*self.dy;r=sr+p[1]+p[4]*self.dx+p[5]*self.dy
        if not target.supported(r,c):return None,'target_support'
        return dict(point=centre+p[:2],zncc=zncc,parameters=p),None


def surface_strain(reference,deformed,centres,valid,radius):
    """Local quadratic 3D surfaces -> Green–Lagrange strains in ref tangent axes.

    Coordinates for fitting are measured reference-image locations. Both 3D
    surfaces are fitted. A local metric/tangent transformation makes the result
    invariant to rigid rotation, including for imperfect reconstructed depth.
    """
    out=np.full((len(centres),3),np.nan);ids=np.flatnonzero(valid)
    if len(ids)<9:return out
    tree=cKDTree(centres[ids])
    for index,i in enumerate(ids):
        near=ids[tree.query_ball_point(centres[i],radius)]
        if len(near)<9:continue
        d=(centres[near]-centres[i])/radius;u,v=d.T
        A=np.column_stack((np.ones(len(near)),u,v,u*u,u*v,v*v));w=np.exp(-np.sum(d*d,axis=1))
        Aw=A*w[:,None]
        if np.linalg.matrix_rank(Aw)<6 or np.linalg.cond(Aw)>1e4:continue
        B=np.column_stack((reference[near]-reference[i],deformed[near]-deformed[i]))
        coefficients=np.linalg.lstsq(Aw,B*w[:,None],rcond=None)[0]
        # parameter axes: +columns, -rows, approximately +x,+y on reference face.
        R=np.column_stack((coefficients[1,:3],-coefficients[2,:3]))
        D=np.column_stack((coefficients[1,3:],-coefficients[2,3:]))
        ru=np.linalg.norm(R[:,0]);rv=R[:,1]-R[:,0]*np.dot(R[:,0],R[:,1])/max(ru*ru,1e-30)
        rvnorm=np.linalg.norm(rv)
        if min(ru,rvnorm)<1e-10:continue
        Q=np.column_stack((R[:,0]/ru,rv/rvnorm));transform=Q.T@R
        if np.linalg.cond(transform)>1e3:continue
        F=D@np.linalg.inv(transform);E=(F.T@F-np.eye(2))/2
        out[i]=E[0,0],E[1,1],2*E[0,1]
    return out


def reconstruct(images,masks,rig,settings,strain_radius,progress=None):
    keys=['left_reference','right_reference','left_deformed','right_deformed']
    raw_images,raw_masks=images,masks
    images,masks,preprocessing=prepare_images(images,masks,settings.get('denoise_sigma',0))
    matchers=[ImageMatcher(images[k],masks[k],settings['subset_size']) for k in keys]
    a,b,c,d=matchers;H,W=images[keys[0]].shape;h=settings['subset_size']//2;step=settings['step'];radius=settings['search_radius']
    # Keep the original candidate grid for fair Off/Mild coverage comparisons.
    candidate=a if not preprocessing['kernel_radius_px'] else ImageMatcher(raw_images[keys[0]],raw_masks[keys[0]],settings['subset_size'])
    rows,cols=np.nonzero(candidate.mask)
    def axis(lo,hi):
        lo+=h+1;hi-=h+1
        count=max(0,int((hi-lo)//step)+1)
        # Integer reference centres avoid an unnecessary second interpolation of
        # the source image while retaining a centred, full-support grid.
        return np.floor((lo+hi-(count-1)*step)/2)+np.arange(count)*step
    grid=np.array([(x,y) for y in axis(rows.min(),rows.max()) for x in axis(cols.min(),cols.max())],float)
    # Candidate centres require reference subset support; invalid background isn't
    # counted as a failed stereo attempt. All subsequent failure reasons are kept.
    centres=np.array([p for p in grid if candidate.supported(p[1]+candidate.dy,p[0]+candidate.dx)])
    if not len(centres):raise ValueError('No complete reference subsets fit the face. Reduce subset size or increase square side.')
    n=len(centres);reference=np.full((n,3),np.nan);deformed=reference.copy();coordinates=np.full((n,4,2),np.nan)
    valid=np.zeros(n,bool);quality=np.full((n,4),np.nan);statuses=[]
    thresholds=dict(cycle_px=.3,epipolar_px=.25,reprojection_px=.2,neighbour_px=.5)
    for i,point in enumerate(centres):
        coordinates[i,0]=point
        if progress and i%20==0:progress(f'Stereo matching: {i} / {n} reference subsets…')
        r0,why=a.match(b,point,radius,epipolar=True)
        if why:statuses.append('reference_'+why);continue
        l1,why=a.match(c,point,radius)
        if why:statuses.append('temporal_'+why);continue
        # Independently match both routes to the right-deformed observation.
        r1,why=a.match(d,point,radius)
        if why:statuses.append('right_'+why);continue
        cross,why=c.match(d,l1['point'],radius,guess=r1['point'],epipolar=True)
        if why:statuses.append('cross_'+why);continue
        back,why=c.match(a,l1['point'],radius,guess=point)
        if why:statuses.append('reverse_'+why);continue
        right_time,why=b.match(d,r0['point'],radius,guess=r1['point'])
        if why:statuses.append('right_temporal_'+why);continue
        cycle=max(np.linalg.norm(back['point']-point),np.linalg.norm(cross['point']-r1['point']),np.linalg.norm(right_time['point']-r1['point']))
        epi=max(abs(point[1]-r0['point'][1]),abs(l1['point'][1]-r1['point'][1]))
        p0=rig.triangulate(point,r0['point']);p1=rig.triangulate(l1['point'],r1['point'])
        coordinates[i]=point,r0['point'],l1['point'],r1['point'];reference[i]=p0;deformed[i]=p1
        reproj=max(np.linalg.norm(rig.project(p0,0)-point),np.linalg.norm(rig.project(p0,1)-r0['point']),np.linalg.norm(rig.project(p1,0)-l1['point']),np.linalg.norm(rig.project(p1,1)-r1['point']))
        quality[i]=min(v['zncc'] for v in (r0,l1,r1,cross,back,right_time)),cycle,epi,reproj
        if not np.all(np.isfinite([p0,p1])):statuses.append('triangulation');continue
        if cycle>thresholds['cycle_px']:statuses.append('cycle');continue
        if epi>thresholds['epipolar_px']:statuses.append('epipolar');continue
        if reproj>thresholds['reprojection_px']:statuses.append('reprojection');continue
        valid[i]=True;statuses.append('accepted')
    # Flag isolated inconsistencies with a local affine prediction of measured
    # image movement. This uses no imposed torsion shape or analytical truth.
    ids=np.flatnonzero(valid);flagged=[]
    if len(ids)>=10:
        tree=cKDTree(centres[ids]);motion=coordinates[:,2:,:]-coordinates[:,0,None,:]
        for i in ids:
            _,nn=tree.query(centres[i],k=min(13,len(ids)));near=ids[np.atleast_1d(nn)];near=near[near!=i]
            A=np.column_stack((np.ones(len(near)),(centres[near]-centres[i])/step))
            if np.linalg.matrix_rank(A)<3:continue
            B=motion[near].reshape(len(near),4);coef=np.linalg.lstsq(A,B,rcond=None)[0]
            residual=B-A@coef;scale=1.4826*np.median(abs(residual-np.median(residual,axis=0)),axis=0)
            if np.any(abs(motion[i].ravel()-coef[0])>np.maximum(thresholds['neighbour_px'],6*scale)):flagged.append(i)
        for i in flagged:valid[i]=False;statuses[i]='neighbour_inconsistent'
    strains=surface_strain(reference,deformed,centres,valid,strain_radius)
    displacement=deformed-reference;displacement[~valid]=np.nan;strains[~valid]=np.nan
    return dict(centres_px=centres,reference_m=reference,deformed_m=deformed,displacement_m=displacement,
                strain=strains,valid=valid,coordinates_px=coordinates,quality=quality,status=statuses,
                status_counts=dict(Counter(statuses)),thresholds=thresholds,
                preprocessing=preprocessing,matching_images=images)
