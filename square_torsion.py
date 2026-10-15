"""Free-warping Saint-Venant square torsion; metres, pascals and radians.

The series satisfies traction-free lateral faces. Ends are applied resultants,
not rigid clamps. Finite cross-section rotation is used for camera geometry;
analytical stresses remain the small-strain Saint-Venant stresses.
"""
import numpy as np


class SquareTorsion:
    def __init__(self,length,side,E,nu,torque,terms=80):
        self.L,self.side,self.a=length,side,side/2
        self.rotation_reference=length/2
        self.G=E/(2*(1+nu));self.T=torque;self.terms=terms
        n=np.arange(1,2*terms,2,dtype=float)
        self.J=side**4/3*(1-192/np.pi**5*np.sum(np.tanh(n*np.pi/2)/n**5))
        self.rate=torque/(self.G*self.J)

    def section(self,y,z):
        """Warping function w (m²) and Prandtl derivatives phi_y, phi_z (m).
        phi solves Laplacian(phi)=-2, phi=0 on the square boundary.
        u_x=rate*w; tau_xy=G*rate*phi_z; tau_xz=-G*rate*phi_y.
        Stable hyperbolic ratios avoid overflow at high series orders.
        """
        y,z=np.broadcast_arrays(np.asarray(y,float),np.asarray(z,float))
        a=self.a; w=-y*z;py=np.zeros_like(y);pz=-2*z
        for j in range(self.terms):
            n=2*j+1;k=n*np.pi/(2*a);sign=(-1)**j
            ep=np.exp(k*(y-a));em=np.exp(-k*(y+a));den=1+np.exp(-2*k*a)
            ch=(ep+em)/den;sh=(ep-em)/den
            w=w+32*a*a/np.pi**3*sign/n**3*np.sin(k*z)*sh
            py=py-16*a/np.pi**2*sign/n**2*np.cos(k*z)*sh
            pz=pz+16*a/np.pi**2*sign/n**2*np.sin(k*z)*ch
        # Enforce the known zero traction on exact boundary coordinates.
        # A truncated Fourier derivative otherwise leaves a small corner tail.
        pz=np.where(np.abs(y)>=a*(1-1e-12),0.,pz)
        py=np.where(np.abs(z)>=a*(1-1e-12),0.,py)
        return w,py,pz

    def stress(self,y,z):
        _,py,pz=self.section(y,z)
        return self.G*self.rate*pz,-self.G*self.rate*py

    def position(self,x,y,z,phase=1):
        x,y,z=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float),np.asarray(z,float))
        w,_,_=self.section(y,z);rate=self.rate*phase;theta=rate*(x-self.rotation_reference)
        return np.stack((x+rate*w,y*np.cos(theta)-z*np.sin(theta),y*np.sin(theta)+z*np.cos(theta)),axis=-1)

    def face(self,x,y,phase=1):
        """Front-face position and exact tangent vectors of the camera geometry."""
        x,y=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float));z=self.a
        w,_,pz=self.section(y,z);rate=self.rate*phase;theta=rate*(x-self.rotation_reference)
        c,s=np.cos(theta),np.sin(theta);Y=y*c-z*s;Z=y*s+z*c
        p=np.stack((x+rate*w,Y,Z),axis=-1)
        tx=np.stack((np.ones_like(x),-rate*Z,rate*Y),axis=-1)
        ty=np.stack((rate*(z+pz),c,s),axis=-1)
        return p,tx,ty

    def face_strain(self,x,y):
        _,tx,ty=self.face(x,y)
        return np.stack(((np.sum(tx*tx,axis=-1)-1)/2,(np.sum(ty*ty,axis=-1)-1)/2,np.sum(tx*ty,axis=-1)),axis=-1)

    def summary(self):
        y,z=np.meshgrid(np.linspace(-self.a,self.a,81),np.linspace(-self.a,self.a,81))
        t1,t2=self.stress(y,z);tau=np.hypot(t1,t2)
        x=np.linspace(0,self.L,101)
        return dict(torsion_constant_m4=self.J,shear_modulus_pa=self.G,twist_rate_rad_per_m=self.rate,
                    end_twist_rad=self.rate*self.L,total_twist_rad=self.rate*self.L,
                    rotation_reference_m=self.rotation_reference,left_end_rotation_rad=-self.rate*self.L/2,
                    right_end_rotation_rad=self.rate*self.L/2,max_shear_pa=float(tau.max()),
                    max_von_mises_pa=float(np.sqrt(3)*tau.max()),x_m=x.tolist(),twist_deg=np.degrees(self.rate*(x-self.rotation_reference)).tolist(),
                    section_y_m=y[0].tolist(),section_z_m=z[:,0].tolist(),section_shear_mpa=(tau/1e6).tolist())

    def solid(self):
        """Independent face meshes for shaded display, with exact vertex stresses."""
        vertices=[];faces=[];nx,ns=48,16
        # Map face grids and orient each face outward.
        for fixed,sign in [('z',1),('z',-1),('y',1),('y',-1),('x',1),('x',-1)]:
            if fixed=='x':
                u,v=np.meshgrid(np.linspace(-self.a,self.a,ns+1),np.linspace(-self.a,self.a,ns+1));x=np.full_like(u,self.L if sign==1 else 0);y=u;z=v
                reverse=sign<0
            else:
                u,v=np.meshgrid(np.linspace(0,self.L,nx+1),np.linspace(-self.a,self.a,ns+1));x=u
                if fixed=='z':y=v;z=np.full_like(u,sign*self.a);reverse=sign<0
                else:y=np.full_like(u,sign*self.a);z=v;reverse=sign>0
            orig=np.stack((x,y,z),axis=-1);disp=self.position(x,y,z)-orig
            t1,t2=self.stress(y,z);tau=np.hypot(t1,t2)/1e6
            offset=len(vertices);vertices.extend(np.concatenate((orig,disp,tau[...,None],(np.sqrt(3)*tau)[...,None]),axis=-1).reshape(-1,8).tolist())
            ny,ncol=x.shape
            for j in range(ny-1):
                for i in range(ncol-1):
                    k=offset+j*ncol+i;ids=[k,k+1,k+ncol+1,k+ncol]
                    faces.append(ids[::-1] if reverse else ids)
        return dict(vertices=vertices,faces=faces)


def build_square_config(data,E_gpa,nu,L,number,defaults,material_name):
    side=number(data,'side_mm',2,200)/1000;T=number(data,'torque_nm',-1e6,1e6)
    if not 3<=L/side<=10:raise ValueError('For the stereo view use a length between 3 and 10 times the square side.')
    if not isinstance(data.get('compare_noise',False),bool):raise ValueError('compare_noise must be true or false.')
    if data.get('compare_noise',False):raise ValueError('Stereo torsion supports selected camera noise; paired noise comparison is for the flat experiments.')
    model=SquareTorsion(L,side,E_gpa*1e9,nu,T)
    if abs(model.rate*L)>.15:raise ValueError('End twist exceeds 0.15 rad. Reduce torque for reliable visibility and small-strain mechanics.')
    if model.summary()['max_shear_pa']/model.G>.02:raise ValueError('Maximum shear strain exceeds 2%. Reduce torque.')
    subset=number(data,'subset_size',17,41,True);step=number(data,'step',8,32,True)
    if subset%2==0:raise ValueError('Subset size must be odd.')
    radius=number(data,'fit_radius_px',20,100)
    if radius<2.1*step:raise ValueError('Strain fit radius must be at least 2.1 times grid spacing.')
    seed=number(data,'seed',0,2147483647,True)
    return dict(benchmark='square_torsion',stereo=True,length_m=L,side_m=side,torque_nm=T,rotation_reference_m=L/2,
        material=dict(youngs_modulus_pa=E_gpa*1e9,poisson_ratio=nu),
        image=dict(speckle_radius_px=number(data,'speckle_radius_px',1,5),density=number(data,'density',.15,.65),seed=seed),
        camera=dict(noise_std=number(data,'noise_std',0,.15),blur_sigma=number(data,'blur_sigma',0,2.5),brightness_gain=number(data,'brightness_gain',.5,1.4),seed=seed+1),
        dic=dict(subset_size=subset,step=step,search_radius=number(data,'search_radius',4,36,True)),
        strain=dict(fit_radius_px=radius),user_inputs={**defaults,**data,'E_gpa':E_gpa,'nu':nu},
        load_description=dict(material_name=material_name,torque_nm=T),
        warnings=['Square-section Saint-Venant torsion with free axial warping. The middle section has zero rotation; both ends rotate oppositely. Local rigid-clamp/end effects are excluded.',
                  'Stereo DIC measures the common visible front face only, using ideal calibrated pinhole cameras.',
                  'Surface Green–Lagrange strain includes rotation correctly. Interior stress colours are analytical; no measured interior stress is inferred.',
                  'Camera geometry uses finite section rotation and Saint-Venant warping; analytical stress is the small-strain elastic solution. Magnification affects only the 3D display.'])
