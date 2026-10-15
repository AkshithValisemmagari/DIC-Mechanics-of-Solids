"""Calibrated parallel pinhole stereo rig and synthetic front-face rendering.

Known camera calibration is available to reconstruction; the specimen deformation
is used only by the image generator and validation, never by matching.
"""
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates, gaussian_filter, binary_erosion
from speckle import generate_speckles


class StereoRig:
    def __init__(self,length,side,width=800):
        self.width=width;self.scale=(width-160)/length
        self.height=max(192,int(np.ceil(side*self.scale))+100)
        self.L=length;self.a=side/2;self.distance=4*length
        self.baseline=.8*self.distance;self.f=self.scale*(self.distance-self.a)
        self.cy=(self.height-1)/2
        self.cameras=[]
        for bx in [-self.baseline/2,self.baseline/2]:
            centre=np.array([length/2+bx,0,self.distance])
            cx=(width-1)/2+self.f*bx/(self.distance-self.a)
            # Image coordinates: columns +world x, rows -world y, depth -world z.
            R=np.diag([1.,-1.,-1.]);K=np.array([[self.f,0,cx],[0,self.f,self.cy],[0,0,1.]])
            P=K@np.column_stack((R,-R@centre))
            self.cameras.append(dict(centre=centre,cx=cx,P=P))

    def project(self,points,camera):
        points=np.asarray(points);cam=self.cameras[camera];q=self.distance-points[...,2]
        return np.stack((self.f*(points[...,0]-cam['centre'][0])/q+cam['cx'],self.cy-self.f*points[...,1]/q),axis=-1)

    def reference_xy(self,pixels):
        p=np.asarray(pixels)
        return np.column_stack(((p[:,0]-(self.width-1)/2)/self.scale+self.L/2,(self.cy-p[:,1])/self.scale))

    def triangulate(self,left,right):
        """Rectified pinhole triangulation. Row disagreement remains a QC residual."""
        left,right=np.asarray(left,float),np.asarray(right,float)
        disparity=(left[...,0]-self.cameras[0]['cx'])-(right[...,0]-self.cameras[1]['cx'])
        with np.errstate(divide='ignore',invalid='ignore'):
            depth=self.f*self.baseline/disparity
            xl=self.cameras[0]['centre'][0]+(left[...,0]-self.cameras[0]['cx'])*depth/self.f
            xr=self.cameras[1]['centre'][0]+(right[...,0]-self.cameras[1]['cx'])*depth/self.f
            yy=(self.cy-(left[...,1]+right[...,1])/2)*depth/self.f
        p=np.stack(((xl+xr)/2,yy,self.distance-depth),axis=-1)
        p=np.where((depth>0)[...,None],p,np.nan)
        return p

    def metadata(self):
        return dict(model='ideal rectified pinhole stereo; no lens distortion',width=self.width,height=self.height,
                    focal_length_px=self.f,baseline_m=self.baseline,reference_pixel_size_m=1/self.scale,
                    projection_matrices=[v['P'].tolist() for v in self.cameras],
                    centres_m=[v['centre'].tolist() for v in self.cameras],
                    principal_points_px=[[v['cx'],self.cy] for v in self.cameras],
                    calibration='Exact simulated calibration. No experimental calibration uncertainty is included.')


def render_face(model,rig,texture,camera,phase=1,rotation=None,translation=None):
    """Inverse project each camera pixel onto the warped material face.

    The allowed twist and aspect ratios give a single front-facing patch. Pixels
    without a converged, in-bounds, front-facing ray intersection are masked.
    """
    rr,cc=np.mgrid[:rig.height,:rig.width];cam=rig.cameras[camera]
    x=(cc-(rig.width-1)/2)/rig.scale+model.L/2;y=(rig.cy-rr)/rig.scale
    yy=np.linspace(-model.a,model.a,2049);ww,_,pz=model.section(yy,model.a)
    warp=CubicSpline(yy,ww);warp_y=CubicSpline(yy,model.a+pz)
    rot=np.eye(3) if rotation is None else np.asarray(rotation)
    shift=np.zeros(3) if translation is None else np.asarray(translation)
    rate=model.rate*phase
    def geometry(x,y):
        theta=rate*(x-model.rotation_reference);co,si=np.cos(theta),np.sin(theta)
        Y=y*co-model.a*si;Z=y*si+model.a*co
        yc=np.clip(y,-model.a,model.a)
        p=np.stack((x+rate*warp(yc),Y,Z),axis=-1)@rot.T+shift
        tx=np.stack((np.ones_like(x),-rate*Z,rate*Y),axis=-1)@rot.T
        ty=np.stack((rate*warp_y(yc),co,si),axis=-1)@rot.T
        return p,tx,ty
    for _ in range(24):
        p,tx,ty=geometry(x,y);q=rig.distance-p[...,2];X=p[...,0]-cam['centre'][0]
        col=rig.f*X/q+cam['cx'];row=rig.cy-rig.f*p[...,1]/q
        a=rig.f*(tx[...,0]*q+X*tx[...,2])/q**2
        b=rig.f*(ty[...,0]*q+X*ty[...,2])/q**2
        c=-rig.f*(tx[...,1]*q+p[...,1]*tx[...,2])/q**2
        d=-rig.f*(ty[...,1]*q+p[...,1]*ty[...,2])/q**2
        det=a*d-b*c;safe=np.abs(det)>1e-8
        dc=col-cc;dr=row-rr
        dx=np.divide(d*dc-b*dr,det,out=np.zeros_like(x),where=safe)
        dy=np.divide(-c*dc+a*dr,det,out=np.zeros_like(y),where=safe)
        x-=np.clip(dx,-model.L*.1,model.L*.1);y-=np.clip(dy,-model.side*.2,model.side*.2)
        if np.max(np.hypot(dc,dr))<1e-7:break
    p,tx,ty=geometry(x,y);projected=rig.project(p,camera)
    normal=np.cross(tx,ty);facing=np.sum(normal*(cam['centre']-p),axis=-1)>0
    valid=(x>=0)&(x<=model.L)&(np.abs(y)<=model.a)&facing&safe&(np.linalg.norm(projected-np.stack((cc,rr),axis=-1),axis=-1)<1e-4)
    cols=(x-model.L/2)*rig.scale+(rig.width-1)/2;rows=rig.cy-y*rig.scale
    im=map_coordinates(texture,[rows,cols],order=3,mode='constant',cval=.5)
    im[~valid]=.5
    return im,valid


def generate_images(model,rig,config,rotation=None,translation=None):
    image=config['image'];camera=config['camera'];shape=(rig.height,rig.width)
    texture=generate_speckles(shape,image['speckle_radius_px'],image['density'],image['seed'])
    rng=np.random.default_rng(camera['seed']);images={};masks={}
    for state,phase in [('reference',0),('deformed',1)]:
        for eye,index in [('left',0),('right',1)]:
            name=eye+'_'+state
            im,mask=render_face(model,rig,texture,index,phase,
                rotation if phase else None,translation if phase else None)
            blur=camera['blur_sigma']
            if blur:im=gaussian_filter(im,blur);mask=binary_erosion(mask,iterations=int(np.ceil(3*blur)))
            if phase:im*=camera['brightness_gain']
            im+=rng.normal(0,camera['noise_std'],shape)
            images[name]=np.rint(np.clip(im,0,1)*255)/255
            masks[name]=mask
    return images,masks
