"""Small orthographic CAD rasterizer with depth buffering for headless PNGs."""
import math
import numpy as np
from numba import njit
from PIL import Image
from matplotlib.colors import to_rgb

@njit(cache=True)
def paint(tri,colors,img,depth):
    h,w=depth.shape
    for k in range(len(tri)):
        v=tri[k]
        xmin=max(0,int(np.floor(v[:,0].min())));xmax=min(w-1,int(np.ceil(v[:,0].max())))
        ymin=max(0,int(np.floor(v[:,1].min())));ymax=min(h-1,int(np.ceil(v[:,1].max())))
        den=(v[1,1]-v[2,1])*(v[0,0]-v[2,0])+(v[2,0]-v[1,0])*(v[0,1]-v[2,1])
        if abs(den)<1e-12:continue
        for y in range(ymin,ymax+1):
            for x in range(xmin,xmax+1):
                a=((v[1,1]-v[2,1])*(x+.5-v[2,0])+(v[2,0]-v[1,0])*(y+.5-v[2,1]))/den
                b=((v[2,1]-v[0,1])*(x+.5-v[2,0])+(v[0,0]-v[2,0])*(y+.5-v[2,1]))/den
                c=1-a-b
                if a<0 or b<0 or c<0:continue
                z=a*v[0,2]+b*v[1,2]+c*v[2,2]
                if z>depth[y,x]:
                    depth[y,x]=z
                    for j in range(3):img[y,x,j]=colors[k,j]

def render(pieces,width=1100,height=1000,elev=25,azim=120):
    e=math.radians(elev);a=math.radians(azim)
    w=np.array([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)])
    u=np.array([-math.sin(a),math.cos(a),0]);v=np.cross(w,u)
    rot=np.stack([u,-v,w])
    light=w+.5*v-.25*u;light/=np.linalg.norm(light)
    tris=[];cols=[]
    for (p,f),color in pieces:
        t=p[f];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-15)
        shade=.48+.47*np.maximum(n@light,0)
        cols.append(np.clip(np.array(to_rgb(color))[None,:]*shade[:,None]*255,0,255).astype(np.uint8))
        tris.append(t@rot.T)
    t=np.concatenate(tris);colors=np.concatenate(cols)
    lo=t[:,:,:2].min((0,1));hi=t[:,:,:2].max((0,1));center=(lo+hi)/2
    scale=min((width-24)/(hi[0]-lo[0]),(height-24)/(hi[1]-lo[1]))
    t[:,:,:2]=(t[:,:,:2]-center)*scale+np.array([width/2,height/2])
    img=np.empty((height,width,3),dtype=np.uint8);img[:]=np.array([246,248,249],dtype=np.uint8)
    depth=np.full((height,width),-np.inf)
    paint(t,colors,img,depth)
    return img
